import { McpProcessService } from '../src/services/McpProcessService.js';
import dotenv from 'dotenv';
dotenv.config();

async function main() {
  const sources = process.env.ZATURN_SOURCES ? process.env.ZATURN_SOURCES.split(',') : [];
  try {
    console.log("SOURCES:", sources);
    const res = await McpProcessService.executeTool({
      command: 'uvx',
      args: ['--from', 'zaturn', 'zaturn_mcp', ...sources],
      tool: 'run_query',
      toolArgs: { source_id: 'test-mysql', query: "SELECT 1" }
    });
    console.log("Success:", JSON.stringify(res, null, 2));
  } catch(e) {
    console.error("Error:", e);
  }
}
main();
