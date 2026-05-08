import dotenv from 'dotenv';
dotenv.config();
import { HuaweiCloudService } from '../src/services/HuaweiCloudService.js';
import { HuaweiSigner } from '../src/services/HuaweiSigner.js';
import axios from 'axios';

async function main() {
  const ak = process.env.HUAWEI_ACCESS_KEY?.trim()!;
  const sk = process.env.HUAWEI_SECRET_KEY?.trim()!;
  HuaweiCloudService.setCredentials(ak, sk);

  // Get projects
  const iamUrl = 'https://iam.myhuaweicloud.com/v3/projects';
  const iamHeaders = HuaweiSigner.sign(ak, sk, { method: 'GET', url: iamUrl, headers: { 'Accept': 'application/json' } });
  const iamRes = await axios.get(iamUrl, { headers: iamHeaders });
  const projects = iamRes.data.projects.filter((p: any) => p.name !== 'MOS' && p.name !== 'global');

  // Validate regions (quick check - just try one API call per region with short timeout)
  const validRegions: {region_id: string, project_id: string}[] = [];
  for (const p of projects) {
    try {
      await Promise.race([
        HuaweiCloudService.request({
          service: 'ecs', region_id: p.name, project_id: p.id,
          method: 'GET', path: '/v1/{project_id}/cloudservers/detail',
          queryParams: { limit: '1' }
        }),
        new Promise((_, rej) => setTimeout(() => rej(new Error('timeout')), 3000))
      ]);
      validRegions.push({ region_id: p.name, project_id: p.id });
    } catch { /* skip */ }
  }

  console.log(`Valid regions: ${validRegions.length}`);

  // Parallel search
  const start = Date.now();
  const results = await Promise.all(
    validRegions.map(async (r) => {
      try {
        const data = await HuaweiCloudService.request({
          service: 'ecs', region_id: r.region_id, project_id: r.project_id,
          method: 'GET', path: '/v1/{project_id}/cloudservers/detail',
        });
        return (data?.servers || []).map((s: any) => ({
          name: s.name, status: s.status, region: r.region_id
        }));
      } catch { return []; }
    })
  );
  const elapsed = Date.now() - start;
  const servers = results.flat();
  console.log(`Parallel search: ${elapsed}ms, ${servers.length} servers`);
  for (const s of servers) console.log(`  - ${s.name} (${s.status}) @ ${s.region}`);

  // Sequential search for comparison
  const start2 = Date.now();
  const seqResults: any[] = [];
  for (const r of validRegions) {
    try {
      const data = await HuaweiCloudService.request({
        service: 'ecs', region_id: r.region_id, project_id: r.project_id,
        method: 'GET', path: '/v1/{project_id}/cloudservers/detail',
      });
      seqResults.push(...(data?.servers || []).map((s: any) => ({
        name: s.name, status: s.status, region: r.region_id
      })));
    } catch { /* skip */ }
  }
  const elapsed2 = Date.now() - start2;
  console.log(`Sequential search: ${elapsed2}ms, ${seqResults.length} servers`);
  console.log(`Speedup: ${(elapsed2/elapsed).toFixed(1)}x`);
}

main().catch(console.error);
