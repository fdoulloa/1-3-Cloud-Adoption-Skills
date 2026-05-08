import fs from 'fs';
import path from 'path';
import { Tool, ToolParameter } from '../core/Agent.js';
import { HuaweiCloudService } from './HuaweiCloudService.js';

export class HuaweiMcpLoader {
  static loadTools(serviceName: string, getProject: (region: string) => any): Tool[] {
    const filePath = path.join(process.cwd(), 'src', 'mcp', 'definitions', `${serviceName}.json`);
    if (!fs.existsSync(filePath)) {
      console.warn(`Definition for ${serviceName} not found at ${filePath}`);
      return [];
    }

    const spec = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
    const tools: Tool[] = [];

    const resolveSchema = (schema: any): any => {
      if (!schema) return null;
      if (schema.$ref) {
        const refPath = schema.$ref.replace('#/', '').split('/');
        let current = spec;
        for (const segment of refPath) {
          current = current[segment];
          if (!current) break;
        }
        return resolveSchema(current);
      }
      return schema;
    };

    const paths = spec.paths || {};
    for (const [pathStr, pathItem] of Object.entries(paths)) {
      for (const [method, operation] of Object.entries(pathItem as any)) {
        if (['get', 'post', 'put', 'delete'].includes(method.toLowerCase())) {
          const op = operation as any;
          const name = op.operationId || this.generateName(method, pathStr);
          const description = op.summary || op.description || `${method.toUpperCase()} ${pathStr}`;
          
          const parameters: Record<string, ToolParameter> = {};
          const allParams = [...(pathItem as any).parameters || [], ...op.parameters || []];

          for (const param of allParams) {
            // Filter out system parameters that we inject
            if (['project_id', 'domain_id', 'X-Auth-Token'].includes(param.name)) continue;
            
            const schema = resolveSchema(param.schema);
            parameters[param.name] = {
              type: schema?.type || 'string',
              description: param.description || '',
              // Force region_id and project_id to be optional so the agent doesn't ask the user
              required: (param.name === 'region_id' || param.name === 'project_id') ? false : (param.required || false)
            };
          }

          // Handle requestBody for POST/PUT
          let bodySchema: any = null;
          if (op.requestBody) {
            const content = op.requestBody.content?.['application/json'];
            bodySchema = resolveSchema(content?.schema);
            if (bodySchema?.properties) {
              for (const [propName, propSchema] of Object.entries(bodySchema.properties)) {
                const schema = resolveSchema(propSchema);
                parameters[propName] = {
                  type: schema?.type || 'object',
                  description: schema?.description || '',
                  required: bodySchema.required?.includes(propName) || false
                };
              }
            }
          }

          const currentBodySchema = bodySchema;

          const isMutation = ['post', 'put', 'delete'].includes(method.toLowerCase());
          const requiresConfirmation = op.hasOwnProperty('x-requires-confirmation') 
            ? op['x-requires-confirmation'] 
            : isMutation;

          tools.push({
            name,
            description,
            parameters,
            requires_confirmation: requiresConfirmation,
            execute: async (args: any) => {
              const region = args.region_id;
              // No longer throwing here, letting the Agent wrapper handle resolution
              
              const project = getProject(region || 'ap-southeast-1');
              
              // Prepare path by replacing {project_id} and other path params
              let pathTemplate = (pathItem as any)['x-url'] 
                ? (pathItem as any)['x-url'].replace('{endpoint}', '') 
                : pathStr;
              
              let finalPath = pathTemplate.replace('{project_id}', project.project_id);
              const queryParams: Record<string, string> = {};
              const body: any = {};

              for (const param of allParams) {
                if (param.in === 'path' && args[param.name]) {
                  finalPath = finalPath.replace(`{${param.name}}`, args[param.name]);
                } else if (param.in === 'query' && args[param.name]) {
                  queryParams[param.name] = args[param.name];
                }
              }

              // Collect body params using resolved schema
              if (currentBodySchema?.properties) {
                for (const propName of Object.keys(currentBodySchema.properties)) {
                  if (args[propName] !== undefined) {
                    body[propName] = args[propName];
                  }
                }
              }

              return await HuaweiCloudService.request({
                service: serviceName as any,
                region_id: region,
                project_id: project.project_id,
                bucket_name: args.bucket_name || args.bucket || undefined,
                method: method.toUpperCase() as any,
                path: finalPath,
                body: Object.keys(body).length > 0 ? body : undefined,
                queryParams: Object.keys(queryParams).length > 0 ? queryParams : undefined
              });
            }
          });
        }
      }
    }

    return tools;
  }

  private static generateName(method: string, path: string): string {
    const cleanPath = path.replace(/\{|\}/g, '').replace(/\//g, '_');
    return `${method.toLowerCase()}${cleanPath}`;
  }
}
