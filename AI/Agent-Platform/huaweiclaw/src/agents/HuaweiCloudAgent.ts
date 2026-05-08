import { Agent, Tool } from '../core/Agent.js';
import { LLMService } from '../services/LLMService.js';
import axios from 'axios';
import dotenv from 'dotenv';
import { Audit } from '../core/Audit.js';
import { HuaweiSigner } from '../services/HuaweiSigner.js';
import { HuaweiCloudService } from '../services/HuaweiCloudService.js';
import { HuaweiCloudMcpManager } from '../services/HuaweiCloudMcpManager.js';
import { McpProcessService } from '../services/McpProcessService.js';

dotenv.config();

export interface RegionCache {
  region_id: string;
  project_id: string;
  project_name: string;
  display_names: string[];
}

const TOOL_ALIASES: Record<string, string> = {
  'start_rds_instance': 'StartupInstance',
  'stop_rds_instance': 'StopInstance',
  'restart_rds_instance': 'RestartInstance',
  'reboot_rds_instance': 'RestartInstance',
  'start_ecs': 'BatchStartServers',
  'stop_ecs': 'BatchStopServers',
  'reboot_ecs': 'BatchRebootServers',
  'start_server': 'BatchStartServers',
  'stop_server': 'BatchStopServers',
  'create_server': 'CreatePostPaidServers',
  'CreateCloudServers': 'CreatePostPaidServers',
  'create_rds': 'CreateInstance',
  'create_database': 'CreateInstance'
};

export class HuaweiCloudAgent extends Agent {
  private cache: RegionCache[] = [];
  private toolCatalog: string = '';
  private mcpManager: HuaweiCloudMcpManager = new HuaweiCloudMcpManager();

  constructor() {
    super(
      'huaweicloud-agent',
      'Huawei Cloud Expert',
      'huaweicloud',
      process.env.HUAWEI_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3',
      'Expert in Huawei Cloud infrastructure management (ECS, VPC, OBS, RDS, IAM, EVS) across multiple regions.'
    );
  }

  private async initializeTools() {
    console.log('Loading Huawei Cloud MCP tools...');

    this.tools = await this.mcpManager.initialize((region) => this.getProject(region));

    // Generate tool catalog (Summarized list of names and core purpose)
    const coreTools = this.tools.filter(t => 
      ['StartupInstance', 'StopInstance', 'RestartInstance', 'BatchStartServers', 'BatchStopServers', 'BatchRebootServers', 'ListServersDetails', 'ListInstances'].includes(t.name) ||
      t.name.toLowerCase().includes('search') ||
      t.name.toLowerCase().includes('list')
    );
    
    this.toolCatalog = coreTools.map(t => `- ${t.name}: ${t.description}`).join('\n');
    if (this.toolCatalog.length > 20_000) {
      this.toolCatalog = this.toolCatalog.substring(0, 20_000) + "\n... [Catalog truncated for brevity]";
    }

    console.log(`Loaded ${this.tools.length} tools. Generated catalog with ${coreTools.length} core tools (Catalog size: ${this.toolCatalog.length} chars).`);

    // Wrap tools with audit logging and resolution logic
    this.tools = this.tools.map(tool => ({
      ...tool,
      execute: async (args: any) => {
        // Alias mapping check is done at the Orchestrator level or before calling tool.execute
        // But we add a safety check here too if needed.

        // 1. AUTO-RESOLUTION: If region_id is missing, try to infer it
        if (!args.region_id) {
          args.region_id = this.inferRegion();
          console.log(`Auto-resolved missing region_id to: ${args.region_id}`);
        }

        // 1a. AUTO-INJECT: project_id from cache (required by MCP server for token scoping)
        if (!args.project_id && args.region_id) {
          try {
            const project = this.getProject(args.region_id);
            args.project_id = project.project_id;
          } catch {}
        }

        // 1a2. NORMALIZE: MCP server uses 'region' not 'region_id'
        if (args.region_id && !args.region) {
          args.region = args.region_id;
        }

        // 1b. RDS mutation tools: normalize 'id' → 'instance_id' (LLM often sends 'id' but the path template uses {instance_id})
        const rdsMutationTools = ['StartupInstance', 'StopInstance', 'RestartInstance', 'DeleteInstance', 'UpdateInstance'];
        if (rdsMutationTools.includes(tool.name)) {
          if (!args.instance_id && args.id) {
            args.instance_id = args.id;
            delete args.id;
            console.log(`Normalized RDS arg: id → instance_id = ${args.instance_id}`);
          }
          if (!args.instance_id) {
            throw new Error(`Falta instance_id para ${tool.name}. Proporciona el nombre o UUID de la instancia RDS (ej: "rds-ocr" o su ID).`);
          }
        }

        // 2. ECS-Specific: Auto-resolution for common ECS tools that use server IDs
        if (['BatchStopServers', 'BatchStartServers', 'BatchRebootServers', 'DeleteServers', 'CreatePostPaidServers'].includes(tool.name)) {
          await this.resolveEcsParams(args, tool.name);
        }

        // 2b. RDS-Specific: Auto-resolution for RDS tool IDs
        if (args.instance_id && !this.isRdsUuid(args.instance_id)) {
          console.log(`Resolving RDS string "${args.instance_id}" to UUID...`);
          const resolvedId = await this.resolveRdsName(args.region_id, args.instance_id);
          if (resolvedId) {
            console.log(`Resolved RDS name "${args.instance_id}" to ${resolvedId}`);
            args.instance_id = resolvedId;
          } else {
             console.warn(`Could not resolve RDS instance name "${args.instance_id}", sending as-is.`);
          }
        }

        // 3. Job Status Normalization: RDS uses 'id' while ECS uses 'job_id' for async task tracking.
        if (tool.name === 'ListJobInfo' && args.job_id && !args.id) {
          args.id = args.job_id;
          delete args.job_id;
        } else if (tool.name === 'ShowJob' && args.id && !args.job_id) {
          args.job_id = args.id;
          delete args.id;
        }

        Audit.logToolCall(this.id, tool.name, args);
        return await tool.execute(args);
      }
    }));

    console.log(`Loaded ${this.tools.length} tools for Huawei Cloud.`);
    const serviceStats = this.mcpManager.getToolsByService();
    console.log(`[MCP-Manager] Tools per service:`, JSON.stringify(serviceStats));

    // Add specialized Global Search tools (via MCP)
    this.tools.push({
      name: 'global_search_servers',
      description: 'Search for all ECS servers across all available regions in the account.',
      parameters: {},
      execute: async () => {
        if (this.cache.length === 0) {
          return { error: 'No regions available. The Huawei Cloud cache failed to initialize — check your AK/SK credentials and IAM permissions.' };
        }
        const regionResults = await Promise.all(
          this.cache.map(async (region) => {
            try {
              const data = await HuaweiCloudService.request({
                service: 'ecs',
                region_id: region.region_id,
                project_id: region.project_id,
                method: 'GET',
                path: '/v1/{project_id}/cloudservers/detail',
              });
              const servers = data?.servers || [];
              return servers.map((s: any) => ({
                name: s.name,
                id: s.id,
                status: s.status,
                region: region.region_id,
                private_ips: Object.values(s.addresses || {}).flat().map((a: any) => a.addr)
              }));
            } catch (e: any) {
              console.warn(`global_search_servers: failed in region ${region.region_id}: ${e.message}`);
              return [];
            }
          })
        );
        return regionResults.flat();
      }
    });

    this.tools.push({
      name: 'global_search_rds',
      description: 'Search for all RDS database instances across all available regions in the account.',
      parameters: {},
      execute: async () => {
        if (this.cache.length === 0) {
          return { error: 'No regions available. The Huawei Cloud cache failed to initialize — check your AK/SK credentials and IAM permissions.' };
        }
        const regionResults = await Promise.all(
          this.cache.map(async (region) => {
            try {
              const data = await HuaweiCloudService.request({
                service: 'rds',
                region_id: region.region_id,
                project_id: region.project_id,
                method: 'GET',
                path: '/v3/{project_id}/instances',
              });
              const instances = data?.instances || [];
              const primaryInstances = instances.filter((i: any) => i.type !== 'Replica');
              return primaryInstances.map((i: any) => ({
                name: i.name,
                id: i.id,
                status: i.status,
                role: i.type,
                type: i.datastore?.type,
                version: i.datastore?.version,
                region: region.region_id,
                private_ips: i.private_ips || []
              }));
            } catch (e: any) {
              console.warn(`global_search_rds: failed in region ${region.region_id}: ${e.message}`);
              return [];
            }
          })
        );
        return regionResults.flat();
      }
    });
  }

  get aliases(): Record<string, string> {
    return TOOL_ALIASES;
  }

  private getProject(region_id: string) {
    const target = region_id.trim().toLowerCase();
    const project = this.cache.find(p => p.region_id.toLowerCase() === target);
    if (!project) {
      console.error(`Cache keys available: ${this.cache.map(p => p.region_id).join(', ')}`);
      throw new Error(`Region ${region_id} not found in cache.`);
    }
    return project;
  }

  /**
   * Automatically resolves server names to UUIDs for ECS batch operations,
   * and normalizes the body into the correct nested structure if the LLM
   * passed a flat shape (e.g. { servers: [...] } instead of { "os-stop": { servers: [...] } }).
   */
  private async resolveEcsParams(args: any, toolName: string) {
    const region_id = args.region_id;
    if (!region_id) return;

    // --- NORMALIZATION ---
    // Map tool names to their required body action keys
    const actionKeyMap: Record<string, string> = {
      'BatchStopServers':   'os-stop',
      'BatchStartServers':  'os-start',
      'BatchRebootServers': 'os-reboot',
    };
    const actionKey = actionKeyMap[toolName];

    if (actionKey) {
      // If the LLM produced a FLAT body (servers at top level instead of nested),
      // wrap it into the correct structure.
      if (!args[actionKey]) {
        // Build the nested sub-body from whatever the LLM provided
        const servers: any[] = [];

        if (Array.isArray(args.servers)) {
          servers.push(...args.servers);
          delete args.servers;
        } else if (args.server_id) {
          servers.push({ id: args.server_id });
          delete args.server_id;
        }

        args[actionKey] = {
          servers,
          ...(args.type ? { type: args.type } : { type: 'SOFT' })
        };
        delete args.type;
        console.log(`[resolveEcsParams] Normalized flat body -> ${actionKey}: ${JSON.stringify(args[actionKey])}`);
      }
    }

    // --- UUID RESOLUTION ---
    // Check for Batch operations (os-stop, os-start, os-reboot)
    const subBody = args['os-stop'] || args['os-start'] || args['os-reboot'];
    if (subBody && Array.isArray(subBody.servers)) {
      for (const server of subBody.servers) {
        if (server.id && !this.isUuid(server.id)) {
          console.log(`Resolving ECS name "${server.id}" to UUID...`);
          const resolvedId = await this.resolveName(region_id, server.id);
          if (resolvedId) {
            console.log(`Resolved "${server.id}" to ${resolvedId}`);
            server.id = resolvedId;
          } else {
            console.warn(`Could not resolve ECS name "${server.id}"`);
          }
        }
      }
    }

    // Check for direct server_ids array (common in some tools)
    if (Array.isArray(args.server_ids)) {
      for (let i = 0; i < args.server_ids.length; i++) {
        if (!this.isUuid(args.server_ids[i])) {
          const resolvedId = await this.resolveName(region_id, args.server_ids[i]);
          if (resolvedId) args.server_ids[i] = resolvedId;
        }
      }
    }

    // --- CREATION AUTO-FIX ---
    if (toolName === 'CreatePostPaidServers' && args.server) {
      // 1. Normalize field names (LLM often uses underscore, API uses no underscore)
      if (args.server.vpc_id && !args.server.vpcid) {
        args.server.vpcid = args.server.vpc_id;
        delete args.server.vpc_id;
      }

      // 2. Resolve VPC Name/ID to UUID
      if (args.server.vpcid && !this.isUuid(args.server.vpcid)) {
        console.log(`Resolving VPC name "${args.server.vpcid}" to UUID...`);
        const resolvedVpc = await this.resolveVpcName(region_id, args.server.vpcid);
        if (resolvedVpc) {
          console.log(`Resolved VPC "${args.server.vpcid}" to ${resolvedVpc}`);
          args.server.vpcid = resolvedVpc;
        } else {
          // Fallback: If not found, try to search for any VPC in the region
          const vpcId = await this.searchVpc(region_id);
          if (vpcId) {
            args.server.vpcid = vpcId;
            console.log(`[resolveEcsParams] Auto-resolved to FIRST available vpcid: ${vpcId}`);
          }
        }
      } else if (!args.server.vpcid) {
        console.log(`[resolveEcsParams] Missing vpcid for creation in ${region_id}. searching...`);
        const vpcId = await this.searchVpc(region_id);
        if (vpcId) {
          args.server.vpcid = vpcId;
          console.log(`[resolveEcsParams] Auto-resolved vpcid: ${vpcId}`);
        }
      }

      // 3. Resolve Subnet Names within nics
      if (Array.isArray(args.server.nics)) {
        for (const nic of args.server.nics) {
          // Normalize subnet_id field name if LLM hallucinated
          if (nic.subnetid && !nic.subnet_id) {
            nic.subnet_id = nic.subnetid;
            delete nic.subnetid;
          }

          if (nic.subnet_id && !this.isUuid(nic.subnet_id)) {
            console.log(`Resolving Subnet name "${nic.subnet_id}" to UUID...`);
            const resolvedSubnet = await this.resolveSubnetName(region_id, nic.subnet_id, args.server.vpcid);
            if (resolvedSubnet) {
              console.log(`Resolved Subnet "${nic.subnet_id}" to ${resolvedSubnet}`);
              nic.subnet_id = resolvedSubnet;
            }
          }

          if (!nic.subnet_id) {
            console.log(`[resolveEcsParams] Missing subnet_id for creation in ${region_id}. searching...`);
            const subnetId = await this.searchSubnet(region_id, args.server.vpcid);
            if (subnetId) {
              nic.subnet_id = subnetId;
              console.log(`[resolveEcsParams] Auto-resolved subnet_id: ${subnetId}`);
            }
          }
        }
      }
    }
  }

  private async searchVpc(region_id: string): Promise<string | null> {
    try {
      const project = this.getProject(region_id);
      const data = await this.mcpCall('vpc', 'ListVpcs', {
        region_id, project_id: project.project_id,
      });
      return data?.vpcs?.length > 0 ? data.vpcs[0].id : null;
    } catch (e) {
      return null;
    }
  }

  private async searchSubnet(region_id: string, vpc_id?: string): Promise<string | null> {
    try {
      const project = this.getProject(region_id);
      const data = await this.mcpCall('vpc', 'ListSubnets', {
        region_id, project_id: project.project_id,
        ...(vpc_id ? { vpc_id } : {}),
      });
      return data?.subnets?.length > 0 ? data.subnets[0].id : null;
    } catch (e) {
      return null;
    }
  }

  private isUuid(id: string): boolean {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    return uuidRegex.test(id);
  }

  private async resolveName(region_id: string, name: string): Promise<string | null> {
    try {
      const project = this.getProject(region_id);
      const data = await this.mcpCall('ecs', 'ListServersDetails', {
        region_id, project_id: project.project_id, name,
      });
      const server = (data?.servers || []).find((s: any) => s.name === name || s.id === name);
      return server ? server.id : null;
    } catch (e) {
      return null;
    }
  }

  private isRdsUuid(id: string): boolean {
    const regex = /^[0-9a-f\-]{32,36}(in[0-9]{2})?$/i;
    return regex.test(id);
  }

  private async resolveRdsName(region_id: string, name: string): Promise<string | null> {
    try {
      const project = this.getProject(region_id);
      const data = await this.mcpCall('rds', 'ListInstances', {
        region_id, project_id: project.project_id, name,
      });
      const instance = (data?.instances || []).find((i: any) => i.name === name || i.id === name);
      return instance ? instance.id : null;
    } catch (e) {
      return null;
    }
  }

  private async resolveVpcName(region_id: string, name: string): Promise<string | null> {
    try {
      const project = this.getProject(region_id);
      const data = await this.mcpCall('vpc', 'ListVpcs', {
        region_id, project_id: project.project_id,
      });
      const vpc = (data?.vpcs || []).find((v: any) => v.name === name || v.id === name);
      return vpc ? vpc.id : null;
    } catch (e) {
      return null;
    }
  }

  private async resolveSubnetName(region_id: string, name: string, vpc_id?: string): Promise<string | null> {
    try {
      const project = this.getProject(region_id);
      const data = await this.mcpCall('vpc', 'ListSubnets', {
        region_id, project_id: project.project_id,
        ...(vpc_id ? { vpc_id } : {}),
      });
      const subnet = (data?.subnets || []).find((s: any) => s.name === name || s.id === name);
      return subnet ? subnet.id : null;
    } catch (e) {
      return null;
    }
  }

  /**
   * Execute a tool call through the Huawei Cloud MCP server.
   * Normalizes region_id → region for MCP server compatibility.
   * Injects project_id from cache.
   */
  private async mcpCall(service: string, toolName: string, args: any): Promise<any> {
    const server = this.mcpManager.getServer(service);
    if (!server) throw new Error(`No MCP server for service ${service}`);

    // Normalize: MCP server uses 'region' not 'region_id'
    const mcpArgs = { ...args };
    if (mcpArgs.region_id && !mcpArgs.region) {
      mcpArgs.region = mcpArgs.region_id;
      delete mcpArgs.region_id;
    }

    const result = await McpProcessService.executeTool({
      command: server.command,
      args: server.args,
      tool: toolName,
      toolArgs: mcpArgs,
      timeout: 60_000,
    });

    if (typeof result === 'string') {
      try { return JSON.parse(result); } catch { return result; }
    }
    return result;
  }

  /**
   * Infers the best region_id from the cache if one is missing.
   */
  private inferRegion(): string {
    // If only one region, use it.
    if (this.cache.length === 1) return this.cache[0].region_id;

    // Default to the first found region or a common one (Hong Kong is very common in this project)
    const hk = this.cache.find(c => c.region_id === 'ap-southeast-1');
    return hk ? hk.region_id : (this.cache[0]?.region_id || 'ap-southeast-1');
  }

  async initialize() {
    console.log('Initializing Huawei Cloud subagent cache...');
    const ak = (process.env.HUAWEI_ACCESS_KEY || '').trim();
    const sk = (process.env.HUAWEI_SECRET_KEY || '').trim();

    if (!ak || !sk) {
      console.warn('[HuaweiCloudAgent] Authentication keys (AK/SK) missing.');
      return;
    }
    
    HuaweiCloudService.setCredentials(ak, sk);

    try {
      const projectsUrl = "https://iam.myhuaweicloud.com/v3/projects";
      const regionsUrl = "https://iam.myhuaweicloud.com/v3/regions";

      const projectsRes = await axios.get(projectsUrl, {
        headers: HuaweiSigner.sign(ak, sk, { method: 'GET', url: projectsUrl, headers: { 'Accept': 'application/json' } })
      });

      const regionsRes = await axios.get(regionsUrl, {
        headers: HuaweiSigner.sign(ak, sk, { method: 'GET', url: regionsUrl, headers: { 'Accept': 'application/json' } })
      });

      const projects = projectsRes.data.projects || [];
      const regions = regionsRes.data.regions || [];

      const rawCache = projects
        .filter((p: any) => p.name !== 'MOS' && p.name !== 'global')
        .map((p: any) => {
          const region = regions.find((r: any) => r.id === p.name);
          return {
            region_id: p.name,
            project_id: p.id,
            project_name: p.name,
            display_names: region ? Object.values(region.locales || {}) : [p.name]
          };
        });

      // Deduplicate by region_id: keep only the first project per region to avoid
      // querying the same region twice (which causes duplicate RDS/ECS results).
      const seenRegions = new Set<string>();
      const potentialCache = rawCache.filter((item: any) => {
        if (seenRegions.has(item.region_id)) {
          console.warn(`Skipping duplicate project for region ${item.region_id} (project: ${item.project_id})`);
          return false;
        }
        seenRegions.add(item.region_id);
        return true;
      });

      console.log(`Validating ${potentialCache.length} potential regions (5s timeout each)...`);

      const VALIDATION_TIMEOUT = 5_000;

      const validationPromises = potentialCache.map(async (item: any) => {
        try {
          const result = await Promise.race([
            HuaweiCloudService.request({
              service: 'ecs',
              region_id: item.region_id,
              project_id: item.project_id,
              method: 'GET',
              path: '/v1/{project_id}/cloudservers/detail',
              queryParams: { limit: '1' }
            }),
            new Promise((_, reject) =>
              setTimeout(() => reject(new Error('Validation timeout')), VALIDATION_TIMEOUT)
            )
          ]);
          return item;
        } catch (e: any) {
          console.warn(`Pruning region ${item.region_id}: ${e.message}`);
          return null;
        }
      });

      const results = await Promise.all(validationPromises);
      const validatedCache = results.filter((r: any): r is any => r !== null);

      this.cache = validatedCache;
      this.description = `Expert in Huawei Cloud infrastructure management (ECS, VPC, OBS, RDS, IAM, EVS) with ${this.cache.length} active validated regions.`;

      console.log(`Huawei Cloud Cache updated: ${this.cache.length} active regions found.`);
      if (potentialCache.length > this.cache.length) {
        console.log(`Note: ${potentialCache.length - this.cache.length} regions were pruned due to errors.`);
      }
      console.log('Active regions:', this.cache.map(c => c.region_id).join(', '));

      // 4. Initialize tools AFTER cache is populated
      if (this.tools.length === 0) {
        await this.initializeTools();
      }
    } catch (error: any) {
      const errorMsg = error.response ?
        `Status: ${error.response.status}, Data: ${JSON.stringify(error.response.data)}` :
        error.message;
      console.error('Failed to initialize Huawei Cloud cache:', errorMsg);
      // Do NOT use a hardcoded fallback cache — it would query a different account's project.
      // Leave cache empty so the agent reports the initialization failure instead of returning wrong data.
      this.cache = [];
    }
  }

  async think(messages: any[]): Promise<string> {
    const prompt = `
      ESTÁS EN MODO EXPERTO EN HUAWEI CLOUD (HWC).
      TIENES PLENO ACCESO A LA INFRAESTRUCTURA MEDIANTE HERRAMIENTAS MCP.

      ⚠️ REGLA #0 — ABSOLUTA Y NO NEGOCIABLE:
      NUNCA respondas con datos de infraestructura (servidores, IPs, estados, IDs, nombres, buckets, bases de datos, etc.) sin haber llamado primero a una herramienta MCP.
      SIEMPRE debes emitir exactamente este formato para ejecutar una herramienta:
        TOOL: nombre_de_herramienta
        ARGS: { "param": "value" }
      NUNCA inventes, fabriques o escribas datos de infraestructura directamente en tu respuesta. Si no llamaste a la herramienta, NO tienes los datos. Punto.
      Cualquier dato de infraestructura que escribas sin haber llamado TOOL primero ES UNA ALUCINACIÓN y puede causar daño operacional real.

      REGIONES DISPONIBLES:
      ${JSON.stringify(this.cache.map(c => ({ id: c.region_id, names: c.display_names })))}

      HERRAMIENTAS CLAVE:
      ${this.toolCatalog}
      - global_search_servers: Listar servidores en todas las regiones.
      - global_search_rds: Listar bases de datos en todas las regiones.
      - ListServersDetails: Listar servidores en una región específica (necesita region_id).
      - ListInstances: Listar RDS en una región específica (necesita region_id).
      - ListBuckets: Listar OBS buckets en una región específica (necesita region_id y Data.location).
      - GetBucketStorageInfo: Obtener tamaño/estadísticas de un bucket (necesita region_id, bucket).
      - StartupInstance / StopInstance: Para RDS (necesita region_id).
      - BatchStartServers / BatchStopServers: Para ECS (necesita region_id y cuerpo JSON).
      
      REGLAS DE ORO:
      1. Si el usuario pide VER, LISTAR o BUSCAR servidores/bases de datos/buckets, LLAMA A LA HERRAMIENTA DE BÚSQUEDA CORRESPONDIENTE DE INMEDIATO. NUNCA respondas con datos sin haber llamado la herramienta primero.
      2. ⚠️ ANTIALUCINACIÓN CRÍTICA: NUNCA inventes, fabriques o alucines datos de servidores, buckets, IPs, IDs, nombres, tamaños o estados. SOLO reporta EXACTAMENTE lo que la herramienta devuelve. Si la herramienta devuelve una lista vacía, di "No se encontraron recursos". Si devuelve un error, reporta el error tal cual. ESTO ES INNEGOCIABLE — una sola alucinación puede causar decisiones operacionales catastróficas.
      3. No pidas confirmación para listar. Lánzalo de inmediato.
      4. ¡PROHIBICIÓN ABSOLUTA!: ESTÁ TOTAL Y ABSOLUTAMENTE PROHIBIDO INICIAR, APAGAR, REINICIAR O BORRAR SERVIDORES O BASES DE DATOS A MENOS QUE EL USUARIO USE PALABRAS EXPLÍCITAS COMO "APAGA", "INICIA", O "BORRA". SI EL USUARIO SOLO PIDE "LISTAR", "VER" O "BUSCAR", DEBES ÚNICAMENTE LISTARLOS, MOSTRAR LA INFORMACIÓN Y CONTESTAR, SIN TOMAR NINGUNA ACCIÓN ADICIONAL DE ALTERACIÓN. ESTO ES UNA REGLA CRÍTICA DE AISLAMIENTO.
      5. Utiliza la lista de REGIONES DISPONIBLES arriba para mapear nombres de ciudades a region_id y project_id. No inventes IDs.

      6. SELECCIÓN DE HERRAMIENTA POR REGIÓN (CRÍTICO):
         - SI el usuario especifica una región (ej: "Hong Kong", "Santiago", "ap-southeast-1", "la-south-2"):
           * Para RDS: USA ListInstances con {"region_id": "REGION_ID"}
           * Para ECS: USA ListServersDetails con {"region_id": "REGION_ID"}
         - SI el usuario pide "TODAS las bases de datos" o "TODOS los servidores" SIN especificar región:
           * Para RDS: USA global_search_rds (sin parámetros)
           * Para ECS: USA global_search_servers (sin parámetros)
         - MAPEO DE REGIONES COMUNES:
           * "Hong Kong" → "ap-southeast-1"
           * "Santiago" → "la-south-2"
           * "México" → "na-mexico-1"
           * "São Paulo" → "sa-brazil-1"
           * "Singapur" → "ap-southeast-3"
         - EJEMPLO: "listar bases de datos en Hong Kong" → TOOL: ListInstances ARGS: {"region_id": "ap-southeast-1"}

      7. FORMATO EXACTO PARA ACCIONES:
         ECS (ÚSALO SOLO SI EL USUARIO PIDE ESTAS ACCIONES EXPLÍCITAMENTE):
         - INICIAR: TOOL: BatchStartServers ARGS: {"region_id": "...", "os-start": {"servers": [{"id": "ID_DEL_SERVIDOR"}]}}
         - APAGAR/DETENER: TOOL: BatchStopServers ARGS: {"region_id": "...", "os-stop": {"servers": [{"id": "ID_DEL_SERVIDOR"}], "type": "SOFT"}}  ⚠️ "APAGAR" significa DETENER (BatchStopServers), NUNCA ELIMINAR. DeleteServers SOLO si el usuario dice explícitamente "ELIMINAR" o "BORRAR".
         - REINICIAR: TOOL: BatchRebootServers ARGS: {"region_id": "...", "os-reboot": {"servers": [{"id": "ID_DEL_SERVIDOR"}], "type": "SOFT"}}
         RDS (ÚSALO SOLO SI EL USUARIO PIDE ESTAS ACCIONES EXPLÍCITAMENTE):
         - INICIAR: TOOL: StartupInstance ARGS: {"region_id": "REGION", "instance_id": "NOMBRE_O_UUID"}
         - APAGAR/DETENER: TOOL: StopInstance ARGS: {"region_id": "REGION", "instance_id": "NOMBRE_O_UUID"}  ⚠️ "APAGAR" significa DETENER (StopInstance), NUNCA ELIMINAR (DeleteInstance). DeleteInstance SOLO si el usuario dice explícitamente "ELIMINAR" o "BORRAR".
         - REINICIAR: TOOL: RestartInstance ARGS: {"region_id": "REGION", "instance_id": "NOMBRE_O_UUID"}
         Puedes usar el nombre de la instancia (ej: "rds-ocr") o su UUID. SIEMPRE incluye region_id e instance_id.
      8. TAREAS ASÍNCRONAS (JOBS): Si una acción devuelve un "job_id", VERIFICA su estado usando:
         - Para servidores (ECS): TOOL: ShowJob ARGS: {"region_id": "...", "job_id": "..."}
         - Para bases de datos (RDS): TOOL: ListJobInfo ARGS: {"region_id": "...", "id": "..."}
      9. CREACIÓN DE RECURSOS (CRÍTICO): 
         - Para crear un ECS (servidor), usa SIEMPRE: TOOL: CreatePostPaidServers.
         - Necesitas: vpcid, subnet_id (dentro de nics), flavorRef e imageRef.
         - SI NO TIENES el vpcid o subnet_id, PRIMERO llama a "ListVpcs" y "ListSubnets" en la región destino. 
         - SI NO TIENES el flavorRef, llama a "ListFlavors" o "ListFlavorSellPolicies".
         - SI NO TIENES el imageRef, llama a "ListImages" (del servicio images o IMS).
         - NO INTENTES crear recursos con IDs inventados o nulos.
      10. FIDELIDAD ABSOLUTA DE DATOS: Cuando recibas el resultado de una herramienta (Tool result), reproduce EXACTAMENTE lo que devuelve. NO agregues servidores, bases de datos, IPs ni ningún dato que no esté en el resultado. Si el resultado tiene 1 instancia, muestra 1 instancia. Si tiene 0, muestra 0. NUNCA "completes" la lista con datos de tu conocimiento previo. Si te encuentras tentado a agregar un servidor que no vino en el resultado, NO LO HAGAS — es una alucinación y puede causar daño real.

      FORMATO OBLIGATORIO — Tu respuesta DEBE ser exactamente así:
      TOOL: tool_name
      ARGS: { "param": "value" }

      EJEMPLOS:
      - "listar servidores en Hong Kong" →
        TOOL: ListServersDetails
        ARGS: { "region_id": "ap-southeast-1" }

      - "listar bases de datos en Santiago" →
        TOOL: ListInstances
        ARGS: { "region_id": "la-south-2" }

      - "listar VPCs en México" →
        TOOL: ListVpcs
        ARGS: { "region_id": "na-mexico-1" }

      - "buscar todos los servidores" →
        TOOL: global_search_servers
        ARGS: {}

      NO escribas ningún otro texto. SOLO el TOOL y ARGS.
    `;

    return await LLMService.chat([
      ...messages,
      { role: 'system', content: prompt }
    ], this.model);
  }
}
