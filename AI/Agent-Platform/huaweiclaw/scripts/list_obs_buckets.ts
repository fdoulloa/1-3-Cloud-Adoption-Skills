import dotenv from 'dotenv';
dotenv.config();
import { HuaweiCloudService } from '../src/services/HuaweiCloudService.js';
import { HuaweiSigner } from '../src/services/HuaweiSigner.js';

async function main() {
  const ak = process.env.HUAWEI_ACCESS_KEY?.trim();
  const sk = process.env.HUAWEI_SECRET_KEY?.trim();

  HuaweiCloudService.setCredentials(ak, sk);

  // Get project IDs
  const iamUrl = 'https://iam.myhuaweicloud.com/v3/projects';
  const iamHeaders = HuaweiSigner.sign(ak, sk, { method: 'GET', url: iamUrl, headers: { 'Accept': 'application/json' } });
  const iamRes = await fetch(iamUrl, { headers: iamHeaders });
  const iamData = await iamRes.json();
  
  const project = iamData.projects?.find((p: any) => p.name === 'ap-southeast-1');
  console.log('Project for ap-southeast-1:', project ? { id: project.id, name: project.name } : 'NOT FOUND');

  const hkProject = iamData.projects?.find((p: any) => p.name === 'ap-east-1');
  console.log('Project for ap-east-1:', hkProject ? { id: hkProject.id, name: hkProject.name } : 'NOT FOUND');

  // List OBS buckets in ap-southeast-1
  try {
    const result = await HuaweiCloudService.request({
      service: 'obs',
      region_id: 'ap-southeast-1',
      project_id: project?.id,
      method: 'GET',
      path: '/',
    });
    console.log('OBS Buckets (ap-southeast-1):', JSON.stringify(result, null, 2));
  } catch (e: any) {
    console.error('Error ap-southeast-1:', e.message);
    if (e.response) console.error('Status:', e.response.status, 'Data:', JSON.stringify(e.response.data));
  }

  // Also try ap-east-1 (Hong Kong)
  if (hkProject) {
    try {
      const result = await HuaweiCloudService.request({
        service: 'obs',
        region_id: 'ap-east-1',
        project_id: hkProject.id,
        method: 'GET',
        path: '/',
      });
      console.log('OBS Buckets (ap-east-1):', JSON.stringify(result, null, 2));
    } catch (e: any) {
      console.error('Error ap-east-1:', e.message);
      if (e.response) console.error('Status:', e.response.status, 'Data:', JSON.stringify(e.response.data));
    }
  }
}

main().catch(console.error);
