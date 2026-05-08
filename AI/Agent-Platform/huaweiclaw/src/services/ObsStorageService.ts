import axios from 'axios';
import crypto from 'crypto';
import { HuaweiSigner } from './HuaweiSigner.js';

export class ObsStorageService {
  private static get ak() { return (process.env.HUAWEI_ACCESS_KEY || '').trim(); }
  private static get sk() { return (process.env.HUAWEI_SECRET_KEY || '').trim(); }
  private static get bucket() { return (process.env.OBS_BUCKET || '').trim(); }
  private static get region() { return (process.env.OBS_REGION || 'la-south-2').trim(); }

  private static get baseUrl() {
    return `https://${this.bucket}.obs.${this.region}.myhuaweicloud.com`;
  }

  static isConfigured(): boolean {
    return !!(this.ak && this.sk && this.bucket);
  }

  /**
   * Upload a buffer to OBS and return a pre-signed URL for access.
   */
  static async upload(key: string, data: Buffer, contentType: string = 'application/octet-stream'): Promise<string> {
    if (!this.isConfigured()) throw new Error('OBS not configured. Set OBS_BUCKET in .env.');

    const url = `${this.baseUrl}/${key}`;
    const headers = HuaweiSigner.sign(this.ak, this.sk, {
      method: 'PUT',
      url,
      headers: { 'Content-Type': contentType },
      body: data.toString('binary'),
      service: 'obs'
    });

    await axios.put(url, data, { headers: { ...headers, 'Content-Type': contentType }, timeout: 30_000 });
    console.log(`[OBS] Uploaded ${key} (${Math.round(data.length / 1024)}KB)`);

    return this.presignedUrl(key);
  }

  /**
   * Generate a pre-signed URL for temporary access to a private object.
   * Default expiry: 1 hour.
   */
  static presignedUrl(key: string, expiresSeconds: number = 3600): string {
    if (!this.isConfigured()) throw new Error('OBS not configured.');

    const url = `${this.baseUrl}/${key}`;
    const expires = Math.floor(Date.now() / 1000) + expiresSeconds;

    // S3-compatible pre-signed URL (OBS supports this)
    const stringToSign = `GET\n\n\n${expires}\n/${this.bucket}/${key}`;
    const signature = crypto.createHmac('sha1', this.sk).update(stringToSign).digest('base64');

    return `${url}?AWSAccessKeyId=${encodeURIComponent(this.ak)}&Expires=${expires}&Signature=${encodeURIComponent(signature)}`;
  }

  /**
   * Download an object from OBS (via pre-signed URL).
   */
  static async download(key: string): Promise<Buffer> {
    const url = this.presignedUrl(key);
    const res = await axios.get(url, { responseType: 'arraybuffer', timeout: 30_000 });
    return Buffer.from(res.data);
  }
}
