import { McpProcessService } from './McpProcessService.js';
import Database from 'better-sqlite3';
import fs from 'fs';
import path from 'path';
import { Tool, ToolParameter } from '../core/Agent.js';
import dotenv from 'dotenv';

dotenv.config();

const SERVICES = ['ecs', 'vpc', 'iam', 'evs', 'obs', 'rds'] as const;
type HwcService = typeof SERVICES[number];

interface CachedTool {
  service: HwcService;
  name: string;
  description: string;
  inputSchema: any;
}

interface McpServerState {
  command: string;
  args: string[];
  ready: boolean;
}

export class HuaweiCloudMcpManager {
  private db: Database.Database;
  private servers: Map<HwcService, McpServerState> = new Map();
  private initialized = false;

  constructor() {
    this.db = new Database(':memory:');
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS mcp_tools (
        service  TEXT NOT NULL,
        name     TEXT NOT NULL PRIMARY KEY,
        description TEXT NOT NULL,
        input_schema TEXT NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_service ON mcp_tools(service);
    `);
  }

  async initialize(getProject: (region: string) => any): Promise<Tool[]> {
    if (this.initialized) return this.loadToolsFromCache(getProject);

    const ak = (process.env.HUAWEI_ACCESS_KEY || '').trim();
    const sk = (process.env.HUAWEI_SECRET_KEY || '').trim();

    const insertStmt = this.db.prepare(
      'INSERT OR REPLACE INTO mcp_tools (service, name, description, input_schema) VALUES (?, ?, ?, ?)'
    );
    const insertAll = this.db.transaction((tools: CachedTool[]) => {
      for (const t of tools) insertStmt.run(t.service, t.name, t.description, JSON.stringify(t.inputSchema));
    });

    const allCachedTools: CachedTool[] = [];

    for (const service of SERVICES) {
      const command = `mcp-server-${service}`;
      const args: string[] = ['-t', 'stdio'];

      this.servers.set(service, { command, args, ready: false });

      try {
        console.log(`[MCP-Manager] Discovering tools from ${command}...`);
      } catch {
        // no-op
      }

      // Discover tools from the OpenAPI spec JSON file
      const tools = this.discoverToolsFromSpec(service);
      if (tools.length > 0) {
        insertAll(tools);
        allCachedTools.push(...tools);
        this.servers.get(service)!.ready = true;
        console.log(`[MCP-Manager] Cached ${tools.length} tools for ${service}`);
      } else {
        console.warn(`[MCP-Manager] No tools discovered for ${service}`);
      }
    }

    this.initialized = true;
    console.log(`[MCP-Manager] Total cached: ${allCachedTools.length} tools across ${SERVICES.length} services`);
    return this.loadToolsFromCache(getProject);
  }

  private discoverToolsFromSpec(service: HwcService): CachedTool[] {
    // Try the official MCP server config path first
    const mcpPaths = [
      path.join('/tmp/huaweicloud-mcp-server', 'huaweicloud_services_server', `mcp_server_${service}`, 'src', `mcp_server_${service}`, 'config', `${service}.json`),
      path.join(process.cwd(), 'src', 'mcp', 'definitions', `${service}.json`),
    ];

    let specPath: string | null = null;
    for (const p of mcpPaths) {
      if (fs.existsSync(p)) { specPath = p; break; }
    }
    if (!specPath) return [];

    const spec = JSON.parse(fs.readFileSync(specPath, 'utf-8'));
    const tools: CachedTool[] = [];

    const resolveRef = (schema: any, root: any): any => {
      if (!schema || !schema.$ref) return schema;
      const parts = schema.$ref.replace('#/', '').split('/');
      let current = root;
      for (const seg of parts) { current = current?.[seg]; if (!current) break; }
      return resolveRef(current, root);
    };

    const paths = spec.paths || {};
    for (const [pathStr, pathItem] of Object.entries(paths as any)) {
      for (const [method, operation] of Object.entries(pathItem as any)) {
        if (!['get', 'post', 'put', 'delete', 'patch'].includes(method.toLowerCase())) continue;
        const op = operation as any;
        const name = op.operationId || `${method}_${pathStr.replace(/[^a-zA-Z0-9]/g, '_')}`;
        const description = op.summary || op.description || `${method.toUpperCase()} ${pathStr}`;

        const inputSchema: any = { type: 'object', properties: {} as Record<string, any>, required: [] as string[] };

        // Path-level parameters
        const pathParams: any[] = (pathItem as any).parameters || [];
        const opParams: any[] = op.parameters || [];
        const allParams = [...pathParams, ...opParams];

        for (const param of allParams) {
          const resolved = resolveRef(param, spec);
          if (['X-Auth-Token'].includes(resolved.name)) continue;
          const schema = resolveRef(resolved.schema, spec) || { type: 'string' };
          inputSchema.properties[resolved.name] = {
            ...schema,
            in: resolved.in,
            description: resolved.description || schema.description || '',
          };
          if (resolved.required || resolved.in === 'path') {
            inputSchema.required.push(resolved.name);
          }
        }

        // Request body
        if (op.requestBody) {
          const content = op.requestBody.content?.['application/json'];
          const bodySchema = resolveRef(content?.schema, spec);
          if (bodySchema?.type === 'object' && bodySchema.properties) {
            for (const [propName, propSchema] of Object.entries(bodySchema.properties)) {
              const resolved = resolveRef(propSchema, spec);
              inputSchema.properties[propName] = { ...resolved, description: resolved?.description || '' };
            }
            if (Array.isArray(bodySchema.required)) {
              inputSchema.required.push(...bodySchema.required);
            }
          }
        }

        // Add region_id as optional parameter (we inject it at call time)
        if (!inputSchema.properties.region_id) {
          inputSchema.properties.region_id = { type: 'string', description: 'Region ID (e.g. ap-southeast-1)', in: 'query' };
        }

        tools.push({ service, name, description, inputSchema });
      }
    }

    return tools;
  }

  loadToolsFromCache(getProject: (region: string) => any): Tool[] {
    const rows = this.db.prepare('SELECT * FROM mcp_tools').all() as CachedTool[];
    return rows.map(row => this.cachedToolToAgentTool(row, getProject));
  }

  private cachedToolToAgentTool(cached: CachedTool, getProject: (region: string) => any): Tool {
    const schema = typeof cached.input_schema === 'string' ? JSON.parse(cached.input_schema) : cached.input_schema;
    const parameters: Record<string, ToolParameter> = {};

    for (const [name, prop] of Object.entries(schema.properties || {})) {
      const p = prop as any;
      if (['project_id', 'domain_id', 'X-Auth-Token'].includes(name)) continue;
      parameters[name] = {
        type: p.type || 'string',
        description: p.description || '',
        required: (name === 'region_id') ? false : schema.required?.includes(name) || false,
      };
    }

    return {
      name: cached.name,
      description: cached.description,
      parameters,
      execute: async (args: any) => {
        return this.executeTool(cached.service, cached.name, args, getProject);
      },
    };
  }

  async executeTool(service: HwcService, toolName: string, args: any, getProject: (region: string) => any): Promise<any> {
    const region = args.region_id || 'ap-southeast-1';
    const project = getProject(region);

    // Get the tool's input schema to know how to route params
    const row = this.db.prepare('SELECT input_schema FROM mcp_tools WHERE name = ?').get(toolName) as any;
    if (!row) throw new Error(`Tool ${toolName} not found in cache`);

    const schema = JSON.parse(row.input_schema);

    // Build the MCP tool arguments, injecting project_id and region
    const mcpArgs: any = { ...args };
    if (schema.properties.project_id) mcpArgs.project_id = project.project_id;
    if (schema.properties.region_id) mcpArgs.region_id = region;
    // Remove undefined/null values
    for (const key of Object.keys(mcpArgs)) {
      if (mcpArgs[key] === undefined || mcpArgs[key] === null) delete mcpArgs[key];
    }

    const server = this.servers.get(service);
    if (!server) throw new Error(`No MCP server registered for service ${service}`);

    try {
      const result = await McpProcessService.executeTool({
        command: server.command,
        args: server.args,
        tool: toolName,
        toolArgs: mcpArgs,
        timeout: 60_000,
      });

      // Parse JSON result if it's a string
      if (typeof result === 'string') {
        try { return JSON.parse(result); } catch { return result; }
      }
      return result;
    } catch (error: any) {
      console.error(`[MCP-Manager] MCP call failed for ${toolName}: ${error.message}`);
      throw error;
    }
  }

  getToolCount(): number {
    return (this.db.prepare('SELECT COUNT(*) as c FROM mcp_tools').get() as any).c;
  }

  getServer(service: string): McpServerState | undefined {
    return this.servers.get(service as HwcService);
  }

  getToolsByService(): Record<string, number> {
    const rows = this.db.prepare('SELECT service, COUNT(*) as count FROM mcp_tools GROUP BY service').all() as any[];
    const result: Record<string, number> = {};
    for (const r of rows) result[r.service] = r.count;
    return result;
  }

  close() {
    this.db.close();
  }
}
