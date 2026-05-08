import dotenv from 'dotenv';
dotenv.config();
import { McpProcessService } from '../src/services/McpProcessService.js';

async function main() {
  console.log('Testing MCP OBS server - ListBuckets...');
  
  try {
    const result = await McpProcessService.executeTool({
      command: 'mcp-server-obs',
      args: ['-t', 'stdio'],
      tool: 'ListBuckets',
      toolArgs: {
        region: 'ap-southeast-1',
      },
      timeout: 30_000,
    });
    console.log('Result type:', typeof result);
    console.log('Result:', typeof result === 'string' ? result.substring(0, 2000) : JSON.stringify(result, null, 2)?.substring(0, 2000));
  } catch (e: any) {
    console.error('Error:', e.message);
    console.error('Stack:', e.stack?.substring(0, 500));
  }
}

main().catch(console.error);
