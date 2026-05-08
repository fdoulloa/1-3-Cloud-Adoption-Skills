import axios from 'axios';
import { HuaweiSigner } from './HuaweiSigner.js';
import dotenv from 'dotenv';

dotenv.config();

export interface HuaweiRequestOptions {
  service: 'ecs' | 'vpc' | 'evs' | 'rds' | 'iam' | 'obs';
  region_id?: string;
  project_id?: string;
  bucket_name?: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE';
  path: string;
  body?: any;
  queryParams?: Record<string, string>;
}

export class HuaweiCloudService {
  private static dynamicAk: string = '';
  private static dynamicSk: string = '';

  private static get ak() { 
    return (this.dynamicAk || process.env.HUAWEI_ACCESS_KEY || '').trim(); 
  }
  private static get sk() { 
    return (this.dynamicSk || process.env.HUAWEI_SECRET_KEY || '').trim(); 
  }

  static setCredentials(ak: string, sk: string) {
    this.dynamicAk = ak;
    this.dynamicSk = sk;
    console.log(`[HuaweiCloudService] Credentials updated dynamically (AK: ${ak.substring(0,4)}...)`);
  }

  private static getBaseUrl(service: string, region_id?: string, bucket_name?: string): string {
    if (service === 'iam') return 'https://iam.myhuaweicloud.com';
    if (!region_id) throw new Error(`Region ID required for service ${service}`);
    
    // Virtual-hosted style for OBS
    if (service === 'obs' && bucket_name) {
      return `https://${bucket_name}.obs.${region_id}.myhuaweicloud.com`;
    }

    // Most regional services follow this pattern
    return `https://${service}.${region_id}.myhuaweicloud.com`;
  }

  static async request(options: HuaweiRequestOptions) {
    const { service, region_id, project_id, bucket_name, method, path, body, queryParams } = options;
    
    if (!this.ak || !this.sk) {
      console.error('[HuaweiCloudService] CRITICAL: AK or SK is missing. Cannot sign request.');
      throw new Error('Huawei Cloud credentials (AK/SK) are not configured. Check your .env file.');
    }

    const baseUrl = this.getBaseUrl(service, region_id || '', bucket_name);
    let url = `${baseUrl}${path.replace('{project_id}', project_id || '')}`;
    
    if (queryParams) {
      const searchParams = new URLSearchParams(queryParams);
      url += `?${searchParams.toString()}`;
    }

    // Huawei POST APIs strongly prefer an empty object {} rather than literal empty string to validate JSON payload auth safely.
    const requestBody = (method === 'POST' || method === 'PUT') && !body ? {} : body;
    // SDK signer requires exactly the string layout Axios will transmit.
    const jsonBody = requestBody ? JSON.stringify(requestBody) : '';
    
    // Huawei Cloud Gateway STRICTLY REQUIRES Content-Type: application/json on all API calls (even GETs)
    const initialHeaders: Record<string, string> = {
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };

    console.log(`[HuaweiCloudService] Signing ${method} ${service.toUpperCase()} request for region ${region_id}...`);
    const headers = HuaweiSigner.sign(this.ak, this.sk, {
      method,
      url,
      service,
      headers: initialHeaders,
      body: jsonBody
    });

    try {
      const timeout = parseInt(process.env.TIMEOUT_MS || '60000');
      const response = await axios({
        method,
        url,
        headers,
        data: requestBody,
        timeout
      });
      return response.data;
    } catch (error: any) {
      const data = error.response?.data;
      let message = error.message;

      if (data && data.code) {
        const errorMaps: Record<string, string> = {
          'Ecs.0121': 'El servidor ya se encuentra en el estado deseado (o en transición). Operación omitida.',
          'Ecs.0104': 'El servidor no fue encontrado. Verifica el ID o la Región.',
          'Ecs.0120': 'El servidor no puede realizar esta acción en su estado actual.',
          'Ecs.0107': 'No tienes permisos suficientes para esta operación.',
          'Vpc.0001': 'Error en la configuración de red VPC.',
        };
        message = errorMaps[data.code] || data.message || message;
      }

      console.error(`Huawei Cloud API Error [${service} ${method} ${path}]:`, data || error.message);
      throw new Error(`Huawei Cloud [${service}] Error: ${message}`);
    }
  }

  // Helper for common action pattern (ECS specific mainly)
  static async action(region_id: string, project_id: string, actionName: string, data: any) {
    return this.request({
      service: 'ecs',
      region_id,
      project_id,
      method: 'POST',
      path: '/v1/{project_id}/cloudservers/action',
      body: { [actionName]: data }
    });
  }
}
