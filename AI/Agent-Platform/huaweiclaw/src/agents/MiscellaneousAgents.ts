import { Agent, Tool } from '../core/Agent.js';
import { LLMService } from '../services/LLMService.js';
import { Audit } from '../core/Audit.js';
import { VectorStore, VectorStoreFactory } from '../core/VectorStore.js';
import { OllamaEmbeddingService } from '../services/OllamaEmbeddingService.js';
import path from 'path';
import dotenv from 'dotenv';
import { memory } from '../core/Memory.js';

dotenv.config();

export class KnowledgeAgent extends Agent {
  private vectorStore?: VectorStore;

  constructor() {
    super('knowledge-agent', 'Knowledge Expert', 'knowledge', process.env.KNOWLEDGE_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3', 'General knowledge expert and internet researcher using RAG for factual inquiries.');
    this.initialize();
  }

  async initialize() {
    this.tools = [this.searchWebTool()];

    const vsType = process.env.VECTOR_STORE_TYPE;
    if (vsType) {
      try {
        const embeddingService = new OllamaEmbeddingService();
        this.vectorStore = await VectorStoreFactory.create(vsType, embeddingService);
        this.tools.push(this.learnInformationTool());
        this.tools.push(this.recallInformationTool());
        console.log('KnowledgeAgent: Vector Store (RAG) initialized.');
      } catch (e: any) {
        console.warn('KnowledgeAgent: Failed to initialize Vector Store:', e.message);
      }
    }
  }

  async think(messages: any[]): Promise<string> {
    const systemPrompt = `
      [MANDATORY: RESPOND IN THE SAME LANGUAGE AS THE USER. ALWAYS DETECT AND MATCH THE USER'S LANGUAGE.]

      You are the Knowledge Agent. You manage the knowledge base (PDFs, documents, facts).

      ═══════════════════════════════════════════════════════════════
      🛠️ TOOLS AVAILABLE
      ═══════════════════════════════════════════════════════════════
      1. learn_information → Store content in knowledge base
         REQUIRED PARAM: "text" - The FULL, COMPLETE content to store
         EXAMPLE: TOOL: learn_information ARGS: {"text": "The company revenue was $5M in 2023..."}

      2. recall_information → Search knowledge base
         REQUIRED PARAM: "query" - Search terms
         EXAMPLE: TOOL: recall_information ARGS: {"query": "revenue 2023"}

      3. search_web → Search internet (optional)

      ═══════════════════════════════════════════════════════════════
      ⚠️ CRITICAL RULES FOR STORING CONTENT
      ═══════════════════════════════════════════════════════════════
      When user wants to SAVE/STORE a document:
      1. DO NOT summarize, DO NOT truncate, DO NOT extract key points
      2. Pass the ENTIRE content verbatim to learn_information
      3. The "text" parameter must contain the FULL document text as provided
      4. If the content is long, still pass it ALL - do not shorten it

      ═══════════════════════════════════════════════════════════════
      ⚠️ CRITICAL RULES FOR RECALLING CONTENT
      ═══════════════════════════════════════════════════════════════
      When user wants to SEARCH/QUERY the knowledge base:
      - Use recall_information with a search query
      - You may summarize the results for the user

      RESPONSE FORMAT: TOOL: tool_name ARGS: {"param": "value"}
    `;
    return await LLMService.chat([
      { role: 'system', content: systemPrompt },
      ...messages
    ], this.model);
  }

  private searchWebTool(): Tool {
    return {
      name: 'search_web',
      description: 'Search the internet for information using DuckDuckGo',
      parameters: { query: { type: 'string', description: 'Search query' } },
      execute: async ({ query }) => {
        Audit.logToolCall(this.id, 'search_web', { query });
        try {
          const { execFile } = await import('child_process');
          const { promisify } = await import('util');
          const execFilePromise = promisify(execFile);
          // Use ddgs CLI if available, otherwise fall back to curl + DuckDuckGo HTML
          const { stdout } = await execFilePromise('curl', [
            '-sL', `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`,
            '-H', 'User-Agent: Mozilla/5.0'
          ], { encoding: 'utf-8', timeout: 10_000 });

          // Extract result snippets from HTML
          const results: string[] = [];
          const regex = /class="result__snippet"[^>]*>([\s\S]*?)<\/a>/g;
          let match;
          while ((match = regex.exec(stdout)) !== null && results.length < 5) {
            results.push(match[1].replace(/<[^>]+>/g, '').trim());
          }
          return results.length > 0
            ? results.map((r, i) => `${i + 1}. ${r}`).join('\n')
            : 'No results found.';
        } catch (e: any) {
          return `Search failed: ${e.message}. Try again later.`;
        }
      }
    };
  }

  private learnInformationTool(): Tool {
    return {
      name: 'learn_information',
      description: 'Store new information in the long-term semantic memory (Vector Store)',
      parameters: {
        text: { type: 'string', description: 'The text to remember' },
        metadata: { type: 'object', description: 'Optional metadata (author, source, etc.)', required: false }
      },
      execute: async ({ text, metadata }) => {
        if (!this.vectorStore) return 'Vector Store not initialized.';
        Audit.logToolCall(this.id, 'learn_information', { text });
        await this.vectorStore.addDocument({ text, metadata });
        return 'Information successfully learned and stored.';
      }
    };
  }

  private recallInformationTool(): Tool {
    return {
      name: 'recall_information',
      description: 'Query the semantic memory for relevant information (RAG)',
      parameters: {
        query: { type: 'string', description: 'The semantic query to search for' }
      },
      execute: async ({ query }) => {
        if (!this.vectorStore) return 'Vector Store not initialized.';
        Audit.logToolCall(this.id, 'recall_information', { query });
        const results = await this.vectorStore.search(query);
        if (results.length === 0) return 'No relevant information found in memory.';
        return results.map(r => r.text).join('\n\n---\n\n');
      }
    };
  }
}

import { HuaweiMcpLoader } from '../services/HuaweiMcpLoader.js';
import { McpProcessService } from '../services/McpProcessService.js';

export class DataAgent extends Agent {
  private vectorStore?: VectorStore;

  constructor() {
    super('data-agent', 'Data Analyst', 'data', process.env.DATA_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3', 'Data analyst expert in SQL/NoSQL queries, database inspection, and statistical visualization using ECharts.');
    this.initializeTools();
    this.initializeVectorStore();
  }

  private async initializeVectorStore() {
    const vsType = process.env.VECTOR_STORE_TYPE;
    if (vsType) {
      try {
        const embeddingService = new OllamaEmbeddingService();
        this.vectorStore = await VectorStoreFactory.create(vsType, embeddingService);
        this.tools.push(this.recallFromKnowledgeTool());
        console.log('DataAgent: Vector Store (Knowledge Base) access initialized.');
      } catch (e: any) {
        console.warn('DataAgent: Failed to initialize Vector Store:', e.message);
      }
    }
  }

  get aliases(): Record<string, string> {
    return {
      // SQL query aliases - all map to analyze_database (the actual tool)
      'execute_sql':   'analyze_database',
      'sql_query':     'analyze_database',
      'run_sql':       'analyze_database',
      'query_sql':     'analyze_database',
      'execute_query': 'analyze_database',
      'run_query':     'analyze_database',
      'query':         'analyze_database',
      // Python execution alias - LLMs often hallucinate this when wanting to run code
      'execute_python': 'analyze_database',
      'run_python':    'analyze_database',
      'python':        'analyze_database',
      // Table inspection aliases
      'list_tables':   'analyze_database',
      'show_tables':   'analyze_database',
      'describe':      'analyze_database',
      'describe_table': 'analyze_database',
      // Chart generation aliases
      'pie_chart':     'generate_pie_chart',
      'bar_chart':     'generate_bar_chart',
      'line_chart':    'generate_line_chart',
      'create_chart':  'generate_bar_chart',
    };
  }

  private initializeTools() {
    // Only register the real Zaturn MCP tool and ECharts.
    // DO NOT load tools from zaturn.json — that file is a fake OpenAPI stub
    // that generates broken HTTP tools via HuaweiMcpLoader (wrong pattern for MCP).
    this.tools = [this.queryDatabaseTool(), this.zaturnTool()];

    // Load ECharts MCP Tools
    try {
      const echartsTools = HuaweiMcpLoader.loadTools('echarts', () => ({}));
      this.tools.push(...echartsTools.map(tool => ({
        ...tool,
        execute: async (args: any) => {
          Audit.logToolCall(this.id, tool.name, args);

          // Parse stringified args that the LLM sometimes sends
          if (args.data && typeof args.data === 'string') {
            try { args.data = JSON.parse(args.data); } catch { /* keep as-is */ }
          }
          if (args.xAxisData && typeof args.xAxisData === 'string') {
            try { args.xAxisData = JSON.parse(args.xAxisData); } catch { /* keep as-is */ }
          }
          if (args.seriesData && typeof args.seriesData === 'string') {
            try { args.seriesData = JSON.parse(args.seriesData); } catch { /* keep as-is */ }
          }

          // Technical fix: LLMs frequently hallucinate "name" instead of "category"
          if (tool.name === 'generate_pie_chart' && Array.isArray(args.data)) {
            args.data = args.data.map((item: any) => ({
              category: item.category || item.name,
              value: item.value
            }));
          }

          // Convert helper tools to generate_echarts with white background.
          // The helpers (generate_pie_chart, etc.) don't expose backgroundColor,
          // and the canvas defaults to black. By converting to generate_echarts
          // we can force a white background while keeping the same chart type.
          let actualTool = tool.name;
          let actualArgs: any = { ...args };

          if (tool.name === 'generate_pie_chart') {
            const pieData = (args.data || []).map((item: any) => ({
              name: item.category || item.name,
              value: item.value
            }));
            actualTool = 'generate_echarts';
            actualArgs = {
              echartsOption: JSON.stringify({
                backgroundColor: 'transparent',
                title: { text: args.title || '', left: 'center', textStyle: { color: '#F8F9FA' } },
                tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
                legend: { orient: 'horizontal', left: 'center', top: 'bottom', textStyle: { color: '#94A3B8' } },
                series: [{
                  type: 'pie',
                  radius: args.innerRadius ? [`${args.innerRadius * 100}%`, '70%'] : '70%',
                  data: pieData,
                  label: { color: '#F8F9FA', fontSize: 13 },
                  emphasis: { itemStyle: { shadowBlur: 0 } }
                }]
              }),
              theme: 'default'
            };
          } else if (tool.name === 'generate_bar_chart') {
            actualTool = 'generate_echarts';
            actualArgs = {
              echartsOption: JSON.stringify({
                backgroundColor: 'transparent',
                title: { text: args.title || '', left: 'center', textStyle: { color: '#F8F9FA' } },
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: args.xAxisData || [], axisLabel: { color: '#94A3B8' }, axisLine: { lineStyle: { color: '#374151' } } },
                yAxis: { type: 'value', axisLabel: { color: '#94A3B8' }, axisLine: { lineStyle: { color: '#374151' } }, splitLine: { lineStyle: { color: '#1f2937' } } },
                series: [{ type: 'bar', data: args.seriesData || [], label: { show: true, color: '#F8F9FA' } }]
              }),
              theme: 'default'
            };
          } else if (tool.name === 'generate_line_chart') {
            actualTool = 'generate_echarts';
            actualArgs = {
              echartsOption: JSON.stringify({
                backgroundColor: 'transparent',
                title: { text: args.title || '', left: 'center', textStyle: { color: '#F8F9FA' } },
                tooltip: { trigger: 'axis' },
                xAxis: { type: 'category', data: args.xAxisData || [], axisLabel: { color: '#94A3B8' }, axisLine: { lineStyle: { color: '#374151' } } },
                yAxis: { type: 'value', axisLabel: { color: '#94A3B8' }, axisLine: { lineStyle: { color: '#374151' } }, splitLine: { lineStyle: { color: '#1f2937' } } },
                series: [{ type: 'line', data: args.seriesData || [], label: { show: true, color: '#F8F9FA' } }]
              }),
              theme: 'default'
            };
          }

          // Return ECharts option JSON for web (fast, responsive, fits container).
          // PNG is only generated on-demand for email/telegram/whatsapp attachments.
          actualArgs.outputType = 'option';

          const TIMEOUT_MS = 60_000;
          const command = 'npx';
          const npxArgs = ['-y', 'mcp-echarts'];
          console.log(`[DataAgent] Calling ECharts Tool: ${actualTool} (mapped from ${tool.name})`);
          const result = await McpProcessService.executeTool({
            command,
            args: npxArgs,
            tool: actualTool,
            toolArgs: actualArgs,
            timeout: TIMEOUT_MS
          });

          // Wrap ECharts JSON in markdown image format for frontend rendering
          const resultStr = typeof result === 'string' ? result : JSON.stringify(result);
          try {
            const config = JSON.parse(resultStr);
            if (config.title || config.series || config.xAxis) {
              const b64 = Buffer.from(resultStr, 'utf-8').toString('base64');
              return `![chart](data:image/echarts;base64,${b64})`;
            }
          } catch { /* not JSON, return as-is */ }
          return result;
        }
      })));
    } catch (e: any) {
      console.warn('ECharts tools not loaded:', e.message);
    }
  }

  async think(messages: any[]): Promise<string> {
    const prompt = `
      ESTÁS EN MODO AGENTE DE DATOS. REGLAS DE ORO:

      ═══════════════════════════════════════════════════════════════
      ⚠️ REGLA CRÍTICA #0: SILENCIO ABSOLUTO ANTES DE TOOL CALLS
      ═══════════════════════════════════════════════════════════════
      NUNCA generes texto explicativo, encabezados, pasos numerados, o markdown ANTES de un TOOL call.
      Tu respuesta debe comenzar INMEDIATAMENTE con:

      TOOL: tool_name
      ARGS: { ... }

      NO escribas: "📊 Generando gráfico...", "Ejecutaré el proceso...", "PASO 1:", etc.
      SIMPLEMENTE EJECUTA EL TOOL CALL DIRECTAMENTE.

      ═══════════════════════════════════════════════════════════════
      📊 PIPELINE PARA GRÁFICOS (REGLA #1)
      ═══════════════════════════════════════════════════════════════
      Cuando el usuario pida un gráfico, debes ejecutar DOS TOOL CALLS SECUENCIALES:

      TURN 1: Obtén los datos
        - Si los datos vienen de la BASE DE DATOS: usa analyze_database
        - Si los datos vienen de PDF/DOCUMENTOS: usa recall_from_knowledge
        → NO respondas con texto, espera el siguiente turn

      TURN 2: Con los datos recibidos, ejecuta la herramienta de visualización
        → Para "distribución" o "proporción": usa generate_pie_chart con {"title": "...", "data": [{"category": "...", "value": N}]}
        → Para "comparación" o cantidades: usa generate_bar_chart con {"title": "...", "xAxisData": [...], "seriesData": [...]}
        → Para "tendencia" o evolución: usa generate_line_chart con {"title": "...", "xAxisData": [...], "seriesData": [...]}

      TURN 3: Solo aquí puedes escribir texto descriptivo FINAL (opcional)

      ═══════════════════════════════════════════════════════════════
      🛠️ HERRAMIENTAS DISPONIBLES (REGLA #2)
      ═══════════════════════════════════════════════════════════════
      - analyze_database → {"query": "SQL query"} (para datos de base de datos)
      - recall_from_knowledge → {"query": "search query"} (para datos de PDFs/documentos)
      - generate_pie_chart → {"title": "...", "data": [{"category": "...", "value": N}]}
      - generate_bar_chart → {"title": "...", "xAxisData": [...], "seriesData": [...]}
      - generate_line_chart → {"title": "...", "xAxisData": [...], "seriesData": [...]}

      ═══════════════════════════════════════════════════════════════
      🚫 PROHIBICIONES ABSOLUTAS (REGLA #3)
      ═══════════════════════════════════════════════════════════════
      - NO uses "execute_python", "run_query", "sql_query" - NO EXISTEN
      - NO inventes nombres de herramientas
      - NO digas "no tengo acceso" - ERES el administrador de la base de datos
      - NO generes tablas Markdown si el usuario pidió un gráfico

      ═══════════════════════════════════════════════════════════════
      💡 CONTEXTO DE BASE DE DATOS (REGLA #4)
      ═══════════════════════════════════════════════════════════════
      La conexión ya apunta al esquema correcto. Usa "WHERE table_schema = DATABASE()"
      en lugar de asumir el nombre del servicio.
      REGLA #4a: NUNCA inventes nombres de columnas. Si no conoces el schema, primero ejecuta:
        TOOL: analyze_database ARGS: {"query": "SHOW TABLES"}
      y luego DESCRIBE <tabla> para ver las columnas exactas.
      Los nombres de columnas pueden ser PascalCase (ej: TipoDocumento, OCRTaskId).
      REGLA #4b: Si un query falla con "Unknown column", el sistema te mostrará automáticamente
      el schema de la tabla. Usa ESOS nombres exactos para corregir tu query inmediatamente.

      ═══════════════════════════════════════════════════════════════
      FORMATO OBLIGATORIO DE RESPUESTA:
      ═══════════════════════════════════════════════════════════════
      TOOL: tool_name
      ARGS: { "parametro": "valor" }
    `;

    return await LLMService.chat([
      ...messages,
      { role: 'system', content: prompt }
    ], this.model);
  }

  private queryDatabaseTool(): Tool {
    return {
      name: 'query_db',
      description: 'Run a query against the main database (MongoDB). You can query collections like "messages", "agent_memories" or "session_states".',
      parameters: {
        collection: { type: 'string', description: 'Collection name' },
        query: { type: 'object', description: 'MongoDB query object' },
        limit: { type: 'number', description: 'Max results', required: false }
      },
      execute: async ({ collection, query, limit = 10 }) => {
        Audit.logToolCall(this.id, 'query_db', { collection, query });
        try {
          const db = memory.getDb();
          const data = await db.collection(collection).find(query).limit(limit).toArray();
          return { status: 'success', data };
        } catch (e: any) {
          return { status: 'error', message: e.message };
        }
      }
    };
  }

  private zaturnTool(): Tool {
    return {
      name: 'analyze_database',
      description: 'Analyze the connected database using SQL queries.',
      parameters: {
        query: { type: 'string', description: 'The SQL query to execute.' }
      },
      execute: async ({ query }) => {
        Audit.logToolCall(this.id, 'analyze_database', { query });
        const sources = process.env.ZATURN_SOURCES ? process.env.ZATURN_SOURCES.split(',') : [];
        if (sources.length === 0) return 'No database configuration found (ZATURN_SOURCES is empty).';

        // Basic SQL injection guard: block DDL/DML that modifies data
        const upper = query.trim().toUpperCase();
        const blocked = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'GRANT', 'REVOKE'];
        for (const kw of blocked) {
          if (upper.startsWith(kw)) return `Blocked: ${kw} statements are not allowed for security.`;
        }

        const src = sources[0];
        // Write query to a temp file to avoid shell injection
        try {
           const fs = await import('fs');
           const path = await import('path');
           const { execFile } = await import('child_process');
           const { promisify } = await import('util');
           const execFilePromise = promisify(execFile);

           const scriptPath = path.join(process.cwd(), 'scripts', '__temp_query.py');
           // Use Python's text() with proper escaping via environment variable
           const safeQuery = query.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
           const script = `import sys, json, os
try:
    from sqlalchemy import create_engine, text
    engine = create_engine('${src}')
    q = os.environ['HC_SQL_QUERY']
    with engine.connect() as conn:
        result = conn.execute(text(q))
        if result.returns_rows:
            keys = list(result.keys())
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            print(json.dumps(rows, default=str))
        else:
            print(json.dumps({"status": "Success, no rows returned."}))
except Exception as e:
    print("Error:", str(e))
`;
           fs.writeFileSync(scriptPath, script);

           const { stdout } = await execFilePromise(
             'uv', ['run', '--with', 'sqlalchemy', '--with', 'pymysql', 'python', scriptPath],
             { encoding: 'utf-8', env: { ...process.env, HC_SQL_QUERY: query }, timeout: 30_000 }
           );
           const sqlResult = stdout.trim();

           // Auto-schema recovery: if the query failed due to an unknown column,
           // automatically run DESCRIBE on the referenced table so the LLM can fix its query.
           const unknownColMatch = sqlResult.match(/Unknown column '([^']+)'/i);
           if (unknownColMatch) {
             const tableMatch = query.match(/FROM\s+(\w+)/i);
             if (tableMatch) {
               const tableName = tableMatch[1];
               try {
                 const { stdout: descOut } = await execFilePromise(
                   'uv', ['run', '--with', 'sqlalchemy', '--with', 'pymysql', 'python', scriptPath],
                   { encoding: 'utf-8', env: { ...process.env, HC_SQL_QUERY: `DESCRIBE ${tableName}` }, timeout: 15_000 }
                 );
                 return `${sqlResult}\n\n[Auto-schema] Columns in table \`${tableName}\`:\n${descOut.trim()}\n\nFix your query using the exact column names above.`;
               } catch { /* fallback to just the error */ }
             }
           }

           return sqlResult;
        } catch(e: any) {
           return "Execution Failed: " + e.message;
        }
      }
    };
  }

  private recallFromKnowledgeTool(): Tool {
    return {
      name: 'recall_from_knowledge',
      description: 'Search the knowledge base (PDFs, documents) for information. Use this to get data from uploaded documents.',
      parameters: {
        query: { type: 'string', description: 'The search query to find relevant information in the knowledge base' }
      },
      execute: async ({ query }) => {
        Audit.logToolCall(this.id, 'recall_from_knowledge', { query });
        if (!this.vectorStore) return 'Knowledge base not initialized.';
        const results = await this.vectorStore.search(query);
        if (results.length === 0) return 'No relevant information found in knowledge base.';
        return results.map(r => r.text).join('\n\n---\n\n');
      }
    };
  }
}

import { CliService } from '../services/CliService.js';

export class CommunicationAgent extends Agent {

  constructor() {
    super('communication-agent', 'Communication Strategist', 'communication', process.env.COMMUNICATION_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3', 'Communication strategist managing Telegram messaging and Google Workspace (Gmail, Calendar, Drive).');
    this.initializeTools();
  }

  private initializeTools() {
    this.tools = [
      this.sendMessageTool(),
      this.sendEmailTool(),
      this.gmailSearchTool(),
      this.calendarListTool(),
      this.calendarCreateTool(),
      this.driveSearchTool()
    ];

    // Initialize Google Workspace SDK
    import('../services/GoogleWorkspaceService.js').then(({ GoogleWorkspaceService }) => {
      GoogleWorkspaceService.initialize().then(ok => {
        if (ok) console.log('CommunicationAgent: Google Workspace SDK initialized.');
        else console.warn('CommunicationAgent: Google Workspace SDK not fully authenticated.');
      });
    }).catch(e => console.warn('GoogleWorkspaceService not available:', e.message));
  }

  private sendEmailTool(): Tool {
    return {
      name: 'gmail_send',
      description: 'Send an email via Google Workspace Gmail API. Supports file path or base64 image attachments.',
      parameters: {
        to: { type: 'string', description: 'Recipient email address' },
        subject: { type: 'string', description: 'Email subject' },
        body: { type: 'string', description: 'Email body content' },
        image_path: { type: 'string', description: 'Path to image file on disk to attach (preferred over base64)', required: false },
        image_base64: { type: 'string', description: 'Optional base64-encoded image to attach', required: false },
        image_name: { type: 'string', description: 'Filename for the image attachment (default: chart.png)', required: false }
      },
      execute: async ({ to, subject, body, image_path, image_base64, image_name }) => {
        Audit.logToolCall(this.id, 'gmail_send', { to, subject, hasAttachment: !!(image_path || image_base64) });
        try {
          // Resolve chart path: if provided path doesn't exist, find the latest chart file
          let resolvedPath = image_path;
          const fsMod = await import('fs');
          const pathMod = await import('path');
          if (resolvedPath && !fsMod.default.existsSync(resolvedPath)) {
            console.warn(`[gmail_send] Path not found: ${resolvedPath}, searching for latest chart...`);
            resolvedPath = undefined;
          }
          if (!resolvedPath && !image_base64) {
            // Find the most recent chart file in /tmp/huaweiclaw-charts/
            const chartDir = '/tmp/huaweiclaw-charts';
            if (fsMod.default.existsSync(chartDir)) {
              const files = fsMod.default.readdirSync(chartDir)
                .filter(f => f.endsWith('.png'))
                .map(f => ({ name: f, mtime: fsMod.default.statSync(pathMod.default.join(chartDir, f)).mtime }))
                .sort((a, b) => b.mtime.getTime() - a.mtime.getTime());
              if (files.length > 0) {
                resolvedPath = pathMod.default.join(chartDir, files[0].name);
                console.log(`[gmail_send] Using latest chart: ${resolvedPath}`);
              }
            }
          }
          const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
          const result = await GoogleWorkspaceService.gmailSend(to, subject, body, resolvedPath, image_base64, image_name);
          return { success: true, messageId: result.id };
        } catch (error: any) {
          return { error: `Gmail send failed: ${error.message}. Ensure GOOGLE_REFRESH_TOKEN is set.` };
        }
      }
    };
  }

  private gmailSearchTool(): Tool {
    return {
      name: 'gmail_search',
      description: 'Search Gmail inbox using Google Workspace API',
      parameters: {
        query: { type: 'string', description: 'Gmail search query (e.g. "in:inbox", "from:boss")' },
        max: { type: 'number', description: 'Max results', required: false }
      },
      execute: async ({ query, max = 10 }) => {
        Audit.logToolCall(this.id, 'gmail_search', { query, max });
        try {
          const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
          return await GoogleWorkspaceService.gmailSearch(query, max);
        } catch (e: any) {
          return { error: `Gmail search failed: ${e.message}. Ensure GOOGLE_REFRESH_TOKEN is set.` };
        }
      }
    };
  }

  private calendarListTool(): Tool {
    return {
      name: 'calendar_list',
      description: 'List upcoming calendar events using Google Workspace API',
      parameters: {
        calendarId: { type: 'string', description: 'Calendar ID (default: primary)', required: false },
        from: { type: 'string', description: 'Start date ISO format', required: false },
        to: { type: 'string', description: 'End date ISO format', required: false }
      },
      execute: async ({ calendarId = 'primary', from, to }) => {
        Audit.logToolCall(this.id, 'calendar_list', { calendarId, from, to });
        try {
          const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
          return await GoogleWorkspaceService.calendarList(calendarId, from, to);
        } catch (e: any) {
          return { error: `Calendar list failed: ${e.message}. Ensure GOOGLE_REFRESH_TOKEN is set.` };
        }
      }
    };
  }

  private calendarCreateTool(): Tool {
    return {
      name: 'calendar_create',
      description: 'Create a calendar event using Google Workspace API',
      parameters: {
        calendarId: { type: 'string', description: 'Calendar ID (default: primary)', required: false },
        summary: { type: 'string', description: 'Event title' },
        from: { type: 'string', description: 'Start time ISO format' },
        to: { type: 'string', description: 'End time ISO format' },
        description: { type: 'string', description: 'Event description', required: false }
      },
      execute: async ({ calendarId = 'primary', summary, from, to, description }) => {
        Audit.logToolCall(this.id, 'calendar_create', { summary, from, to });
        try {
          const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
          return await GoogleWorkspaceService.calendarCreate(calendarId, summary, from, to, description);
        } catch (e: any) {
          return { error: `Calendar create failed: ${e.message}` };
        }
      }
    };
  }

  private driveSearchTool(): Tool {
    return {
      name: 'drive_search',
      description: 'Search Google Drive files using Google Workspace API',
      parameters: {
        query: { type: 'string', description: 'Drive search query (e.g. "name contains \'report\'")' }
      },
      execute: async ({ query }) => {
        Audit.logToolCall(this.id, 'drive_search', { query });
        try {
          const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
          return await GoogleWorkspaceService.driveSearch(query);
        } catch (e: any) {
          return { error: `Drive search failed: ${e.message}` };
        }
      }
    };
  }

  async think(messages: any[]): Promise<string> {
    const systemPrompt = `
      You are the Communication Agent. You manage emails, calendar, and Google Workspace.

      CRITICAL RULES:
      1. ONLY ONE TOOL CALL PER TURN. Do not output multiple "TOOL:" blocks.
      2. NO CONVERSATIONAL TEXT when calling a tool. Output only the TOOL and ARGS.
      3. PARAMETER PRECISION: You MUST use the exact parameter names defined below.

      TOOLS AND PARAMETERS:
      - "gmail_search": { "query": "...", "max": 10 } (query MUST not be empty. Use "in:inbox" for latest mail)
      - "gmail_send": { "to": "...", "subject": "...", "body": "...", "image_path": "/tmp/chart.png", "image_base64": "...", "image_name": "chart.png" } (use image_path when available, fallback to image_base64)
      - "calendar_list": { "calendarId": "primary", "from": "ISO_DATE", "to": "ISO_DATE" }
      - "calendar_create": { "calendarId": "primary", "summary": "...", "from": "ISO_DATE", "to": "ISO_DATE" }
      - "drive_search": { "query": "..." } (query MUST not be empty. Use "name contains '...'" or similar)
      - "send_message": { "to": "...", "message": "..." } (Telegram)

      EXAMPLE SEARCH:
      TOOL: gmail_search ARGS: {"query": "in:inbox", "max": 5}

      RESPONSE FORMAT: TOOL: tool_name ARGS: {"param": "value"}
    `;
    return await LLMService.chat([
      { role: 'system', content: systemPrompt },
      ...messages
    ], this.model);
  }
  private sendMessageTool(): Tool {
    return {
      name: 'send_message',
      description: 'Send a message through Telegram or Email',
      parameters: {
        to: { type: 'string', description: 'Recipient ID or address' },
        message: { type: 'string', description: 'Content of the message' }
      },
      execute: async ({ to, message }) => {
        Audit.logToolCall(this.id, 'send_message', { to, message });
        return { status: 'sent', timestamp: new Date().toISOString() };
      }
    };
  }
}

export class BusinessAgent extends Agent {
  constructor() {
    super('business-agent', 'Business Analyst', 'business', process.env.BUSINESS_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3', 'Business analyst for process optimization, CRM concepts, KPI tracking, and workflow logic.');
    this.tools = [this.analyzeProcessTool(), this.generateKpiTool()];
  }
  async think(messages: any[]): Promise<string> {
    const systemPrompt = `
      [MANDATORY: RESPOND IN THE SAME LANGUAGE AS THE USER. ALWAYS DETECT AND MATCH THE USER'S LANGUAGE.]
      
      You are the Business Agent. You handle abstract business process analysis and CRM-related logic.
      
      AVAILABLE TOOLS:
      1. "analyze_process": Use this to analyze a business workflow or process.
      2. "generate_kpi": Generate KPI metrics for a business area.

      CRITICAL LIMITATIONS:
      - You CAN NOT manage cloud infrastructure (ECS, servers, VPC, RDS, etc.).
      - If the user asks for cloud operations, professionally explain that you are the Business Agent and they should ask for the Huawei Cloud Agent instead.
      - DO NOT hallucinate tool names.
      - RESPONSE FORMAT: TOOL: tool_name ARGS: {"param": "value"}
      - LANGUAGE: Always respond to the user in their own language.
    `;
    return await LLMService.chat([
      { role: 'system', content: systemPrompt },
      ...messages
    ], this.model);
  }
  private analyzeProcessTool(): Tool {
    return {
      name: 'analyze_process',
      description: 'Analyze a business process',
      parameters: { name: { type: 'string', description: 'Process name' } },
      execute: async ({ name }) => {
        Audit.logToolCall(this.id, 'analyze_process', { name });
        return `Process ${name} analysis complete.`;
      }
    };
  }
  private generateKpiTool(): Tool {
    return {
      name: 'generate_kpi',
      description: 'Generate KPI metrics and recommendations for a business area',
      parameters: {
        area: { type: 'string', description: 'Business area (e.g. sales, operations, customer_service)' },
        period: { type: 'string', description: 'Time period (e.g. Q1 2026, last_month)', required: false }
      },
      execute: async ({ area, period }) => {
        Audit.logToolCall(this.id, 'generate_kpi', { area, period });
        const kpiPrompt = `Generate 5 relevant KPIs for the business area "${area}"${period ? ` for ${period}` : ''}. Include name, target, and measurement method for each. Respond in JSON array format.`;
        return await LLMService.chat([{ role: 'user', content: kpiPrompt }], this.model);
      }
    };
  }
}

export class OrchestratorAgent extends Agent {
  constructor() {
    super(
      'orchestrator-agent',
      'Orchestrator',
      'orchestrator',
      process.env.ORCHESTRATOR_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3',
      'Central orchestrator that classifies tasks, routes to specialized agents, and synthesizes responses.'
    );
    this.tools = [this.listAgentsTool()];
  }

  async think(messages: any[]): Promise<string> {
    const { registry } = await import('../core/Registry.js');
    const agents = registry.getAllAgents();
    const agentsInfo = agents.map(a => `- **${a.name}** (@${a.role}): ${a.description}`).join('\n');

    const systemPrompt = `
      [MANDATORY: RESPOND IN THE SAME LANGUAGE AS THE USER.]
      You are the Orchestrator of HuaweiClaw, a multi-agent AI system.
      You classify tasks, route them to the appropriate specialist agent, and synthesize final responses.

      AVAILABLE AGENTS:
      ${agentsInfo}

      RULES:
      1. When asked about the system, list all agents with their roles and descriptions.
      2. When asked to route a task, identify the best agent and explain why.
      3. You can delegate tasks to other agents using A2A messaging.
      4. Always respond in the user's language.
    `;
    return await LLMService.chat([
      { role: 'system', content: systemPrompt },
      ...messages
    ], this.model);
  }

  private listAgentsTool(): Tool {
    return {
      name: 'list_agents',
      description: 'List all available agents and their capabilities',
      parameters: {},
      execute: async () => {
        const { registry } = await import('../core/Registry.js');
        const agents = registry.getAllAgents();
        Audit.logToolCall(this.id, 'list_agents', {});
        return agents.map(a => ({ role: a.role, name: a.name, description: a.description }));
      }
    };
  }
}
