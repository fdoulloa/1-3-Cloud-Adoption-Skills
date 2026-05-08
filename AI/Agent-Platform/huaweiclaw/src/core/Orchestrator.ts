import { registry } from './Registry.js';
import { LLMService } from '../services/LLMService.js';
import { memory } from './Memory.js';
import { AgentRole } from './Agent.js';
import { Audit } from './Audit.js';
import { McpProcessService } from '../services/McpProcessService.js';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';

/** Generate a PNG file from an ECharts JSON config (on-demand for email/telegram). */
async function echartsToPng(echartsConfig: string): Promise<string> {
  const tmpDir = '/tmp/huaweiclaw-charts';
  if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });
  const chartId = crypto.randomBytes(8).toString('hex');
  const chartPath = path.join(tmpDir, `chart-${chartId}.png`);

  // Force dark background for standalone PNG (no cockpit context)
  let pngConfig: any;
  try {
    pngConfig = JSON.parse(echartsConfig);
    pngConfig.backgroundColor = '#1a1a1d';
  } catch { pngConfig = echartsConfig; }

  const result = await McpProcessService.executeTool({
    command: 'npx',
    args: ['-y', 'mcp-echarts'],
    tool: 'generate_echarts',
    toolArgs: { echartsOption: JSON.stringify(pngConfig), outputType: 'png', theme: 'default' },
    timeout: 60_000
  });

  const b64Match = (typeof result === 'string' ? result : JSON.stringify(result)).match(/data:image\/png;base64,([^\s")]+)/);
  if (b64Match) {
    fs.writeFileSync(chartPath, Buffer.from(b64Match[1], 'base64'));
    return chartPath;
  }
  throw new Error('No PNG data in ECharts render response');
}

export class Orchestrator {
  private maxIterations = parseInt(process.env.MAX_ITERATIONS || '10');

  async processRequest(sessionId: string, text: string): Promise<string> {
    // 1. Store user message
    await memory.storeMessage(sessionId, 'user', text);

    // 2. Fetch Session History — last 20 rows = up to 10 turns of context
    const history = await memory.getHistory(sessionId, 20);
    const messages = history.reverse().map((m: any) => {
      // TRUNCATION: Conversations in history should be concise.
      const MAX_HIST_CHARS = 5_000;
      let content = m.content || '';
      
      // CRITICAL STRIPPING: Do not flood the LLM's prompt with massive ECharts UI JSON configurations.
      // Replace it with a lightweight placeholder to maintain context without token saturation.
      if (content.includes('![chart](data:image/echarts;')) {
        content = content.replace(/!\[chart\]\(data:image\/echarts;[^\n]+/g, '\n[Visualization Graph: Chart rendered successfully on user UI]\n');
      }
      
      if (content.length > MAX_HIST_CHARS) {
        content = content.substring(0, MAX_HIST_CHARS) + '... [TRUNCATED in history]';
      }
      return {
        role: m.sender === 'user' ? 'user' : 'assistant',
        content
      };
    }).filter((m: any) => {
      // Remove raw tool messages — agents only need the conversational context and current results.
      const lowContent = m.content.trim().toLowerCase();
      const isStaleToolResult = m.role === 'user' && lowContent.startsWith('tool result:');
      const isStaleToolCall = m.role === 'assistant' && lowContent.startsWith('tool:');
      // Remove stale server/instance listings from previous turns to prevent the LLM from
      // hallucinating or repeating servers that may no longer exist in the account.
      const isStaleServerListing = m.role === 'assistant' && (
        // JSON format: {"name": "...", "id": "...", "status": "...", "region": "..."}
        (lowContent.includes('"name"') && lowContent.includes('"id"') && lowContent.includes('"status"') && lowContent.includes('"region"')) ||
        // Markdown table format: | name | id | status | region |
        (lowContent.includes('|') && (lowContent.includes('servidor') || lowContent.includes('server') || lowContent.includes('instancia') || lowContent.includes('instance') || lowContent.includes('rds') || lowContent.includes('ecs')) && lowContent.includes('status')) ||
        lowContent.includes('"server_id"') ||
        lowContent.includes('"instance_id"')
      );
      return !isStaleToolResult && !isStaleToolCall && !isStaleServerListing;
    });

    // Inject language directive
    messages.unshift({
      role: 'system',
      content: 'IMPORTANT: Respond in the SAME LANGUAGE as the user. If the user asks in Spanish, respond in Spanish. If English, answer in English.'
    });

    // Build compact conversation summary (last 10 messages) for routing
    const last10 = messages.slice(-10);
    const conversationContext = last10
      .map((m, i) => `[${i + 1}] ${m.role.toUpperCase()}: ${m.content.substring(0, 300)}${m.content.length > 300 ? '...' : ''}`)
      .join('\n');

    const lowerText = text.toLowerCase();

    // 3. Check for Pending Confirmation
    const pending = await memory.getSessionState(sessionId);
    const confirmationKeywords = [
      'confirm', 'yes', 'proceed', 'go ahead', 'affirmative', 'ok', 'sure',
      'yes please', 'si', 'dale', 'hazlo', 'adelante', 'procede',
      'ejecutalo', 'ejecuta', 'perfecto', 'listo', 'andale',
    ];
    let isConfirmation = confirmationKeywords.some(k => lowerText.includes(k));

    let agentRole: AgentRole = 'knowledge';
    let initialToolCall: any = null;

    if (isConfirmation && pending && pending.toolCall) {
      console.log(`[Orchestrator] Resuming pending action: ${pending.toolCall.name}`);
      agentRole = pending.role;
      initialToolCall = pending.toolCall;
      messages.push({ role: 'system', content: 'User confirmed the action. Executing immediately...' });
    } else {
      if (pending) await memory.clearSessionState(sessionId);

      // --- FAST KEYWORD CLASSIFICATION (skip LLM for obvious cases) ---
      // ── COMPOUND REQUEST DETECTION ──
      // When the message contains "X and send email" or "X and graph",
      // route to the FIRST agent (the one that produces data) not the second.
      // The post-loop A2A will handle the delegation to the second agent.
      const compoundFirstAgent: [RegExp, AgentRole][] = [
        [/\b(servidor|ecs|cloud|huawei|rds|vpc|obs|buckets?|region|listar|buscar|mostrar)\b.*\b(env[ií]a|manda|send|mail|correo|email)\b/i, 'huaweicloud'],
        // Cloud resource + chart (any order): "gráfica de buckets" or "buckets...gráfica"
        [/\b(servidor|ecs|cloud|huawei|rds|vpc|obs|buckets?|region)\b.*\b(graf[ií]ca|visualiza|chart|plot|dibuja|diagrama)\b/i, 'huaweicloud'],
        [/\b(graf[ií]ca|visualiza|chart|plot|dibuja|diagrama)\b.*\b(servidor|ecs|cloud|huawei|rds|vpc|obs|buckets?|region)\b/i, 'huaweicloud'],
        [/\b(explica|describe|qu[eé]|c[oó]mo|defin)\b.*\b(graf[ií]ca|visualiza|chart|plot|dibuja)\b/i, 'knowledge'],
        [/\b(sql|query|tabla|database|base de datos)\b.*\b(env[ií]a|manda|send|mail|correo|email)\b/i, 'data'],
        // "manda/gráf/al correo" or "manda el correo con gráfico" → communication (any order)
        [/\b(env[ií]a|manda|send|mail)\b.*\b(correo|email|mail|mensaje)\b/i, 'communication'],
      ];

      let compoundRole: AgentRole | null = null;
      for (const [regex, role] of compoundFirstAgent) {
        if (regex.test(lowerText)) {
          compoundRole = role;
          console.log(`[Orchestrator] Compound request detected → routing to first agent: ${compoundRole}`);
          break;
        }
      }

      const keywordMap: [RegExp, AgentRole][] = [
        // ── HuaweiCloud: MUST match before Data to resolve "base de datos" ambiguity ──
        // Cloud infrastructure keywords (ECS, VPC, OBS, EVS, IAM, RDS)
        [/\b(servidor|ecs|cloud|huawei|vpc|obs|buckets?|evs|iam|regi[oó]n|instance|apag[aá](r|l|la|lo|s)?|encend[eé]r|reboot|start|stop|det[eé]n|inici[aá](r|l|la|lo)?|reinici[aá](r|l|la|lo)?)\b/i, 'huaweicloud'],
        // RDS / cloud database keywords — "listar bases de datos RDS", "instancia RDS", "database server"
        [/\b(rds|instancia de base de datos|database instance|base de datos rds|bases de datos en|listar bases de datos|db instance|mysql instance|postgres instance)\b/i, 'huaweicloud'],
        // Cloud management verbs with "base de datos" — "apagar/iniciar/reiniciar base de datos"
        [/\b(apagar|iniciar|reiniciar|crear|borrar|eliminar)\s+(la\s+)?(base de datos|base de dato|database|db)\b/i, 'huaweicloud'],
        // ── Data: SQL/tables/charts (NOT cloud RDS) ──
        [/\b(gr[aá]fico|chart|graficar|visualizar|plot|pie chart|bar chart|echarts)\b/i, 'data'],
        [/\b(sql|query|tabla|table|zaturn|analyze_database|ejecutar query|run query|consulta sql)\b/i, 'data'],
        // "base de datos" WITHOUT cloud context → data (SQL queries)
        [/\b(base de datos|database)\b(?![\s\S]*\b(rds|instance|servidor|cloud|huawei|apagar|iniciar|reiniciar|region|regi[oó]n)\b)/i, 'data'],
        // ── Communication ──
        [/\b(email|correo|gmail|calendar|calendario|drive|google workspace|smtp|enviar email|mandar email|send email)\b/i, 'communication'],
        // ── Code ──
        [/\b(c[oó]digo|code|python|script|programa|debug|bug|flask|javascript|typescript)\b/i, 'code'],
        // ── Knowledge ──
        [/\b(base de conocimiento|knowledge base|aprender|memorizar|subir pdf|upload pdf|store document)\b/i, 'knowledge'],
        // ── Business ──
        [/\b(negocio|business|crm|proceso|workflow|ventas|marketing)\b/i, 'business'],
        // ── Orchestrator ──
        [/\b(qui[eé]n eres|agentes|expertos|help|available agents|que agentes)\b/i, 'orchestrator'],
      ];

      let fastRole: AgentRole | null = null;
      for (const [regex, role] of keywordMap) {
        if (regex.test(lowerText)) {
          fastRole = role;
          break;
        }
      }

      if (compoundRole) {
        agentRole = compoundRole;
        console.log(`[Orchestrator] Compound route → ${agentRole} (first agent, A2A will delegate second part)`);
      } else if (fastRole) {
        agentRole = fastRole;
        console.log(`[Orchestrator] Fast keyword route → ${agentRole}`);
      } else {
        // Sticky agent: if last message was from huaweicloud and this is a short follow-up
        // (e.g. "apágala", "reiníciala", "deténla"), keep huaweicloud
        const lastMessages = await memory.getHistory(sessionId, 4);
        const lastAssistant = lastMessages.filter((m: any) => m.role === 'assistant').pop();
        if (lastAssistant && text.split(/\s+/).length <= 5) {
          const lastContent = typeof lastAssistant.content === 'string' ? lastAssistant.content : '';
          if (lastContent.includes('[HWC]') || lastContent.includes('huaweicloud') || lastContent.includes('ECS') || lastContent.includes('RDS') || lastContent.includes('servidor') || lastContent.includes('instancia')) {
            agentRole = 'huaweicloud';
            console.log(`[Orchestrator] Sticky route → huaweicloud (follow-up on infra context)`);
          }
        }
      }

      if (!compoundRole && !fastRole && agentRole !== 'huaweicloud') {
        // --- FALLBACK: CONTEXT-AWARE LLM CLASSIFICATION ---
      const roles = ['huaweicloud', 'business', 'data', 'code', 'communication', 'knowledge', 'orchestrator'];

      const classificationPrompt = `
You are the routing brain of HuaweiClaw, a multi-agent system.
Decide which agent handles the CURRENT USER MESSAGE based on the full conversation context.

═══ CURRENT USER MESSAGE ═══
"${text}"

═══ LAST ${last10.length} INTERACTIONS (CONTEXT) ═══
${conversationContext}

═══ ROUTING RULES (strict order — first match wins) ═══
RULE 1 — CHARTS / VISUALIZATION (HIGHEST PRIORITY):
  User wants to generate, create, or draw a chart, graph, visualization, or plot.
  Keywords: "gráfico", "chart", "graficar", "visualizar", "plot", "pie chart", "bar chart", "line chart", "dibujar", "generar gráfico".
  → USE "data" (DataAgent handles ALL visualizations, regardless of data source)

RULE 2 — KNOWLEDGE / MEMORY:
  User wants to save, store, learn, memorize, upload, or remember information in the KNOWLEDGE BASE.
  Keywords: "base de conocimiento", "knowledge base", "aprender", "memorizar", "guardar", "subir", "save to knowledge", "remember this", "store document", "upload pdf", "subir pdf", "guardar documento".
  CRITICAL: "base de conocimiento" ≠ "base de datos". Knowledge base is for documents/PDFs, database is for SQL/tables.
  → USE "knowledge"

RULE 3 — DATA / SQL:
  User wants to connect to a DATABASE (MySQL, PostgreSQL, etc), analyze tables, run SQL queries, or examine data structures.
  CRITICAL DISTINCTION: "base de datos" (SQL/tables) goes to "data". "base de conocimiento" (documents/PDFs) goes to "knowledge".
  → USE "data"

RULE 4 — CLOUD ACTION:
  The user is requesting an ACTION on cloud infrastructure: stop, start, reboot, delete, shut down, apagar, encender, reiniciar.
  -OR- follow-up commands like "sí", "ok", "hazlo" regarding infrastructure.
  → USE "huaweicloud"

RULE 5 — CLOUD DISCOVERY:
  User wants to list, show, search, or check the status of cloud resources (servers, databases, VPCs, network).
  → USE "huaweicloud"

RULE 6 — COMMUNICATION:
  User wants to send messages, emails, or interact with Google Workspace/Telegram.
  → USE "communication"

RULE 7 — CODE:
  User wants code written, reviewed, or debugged.
  OR: User wants to create a web page, website, HTML, CSS, JavaScript, frontend, backend, API, script, or application.
  OR: User wants to generate, build, or develop software.
  → USE "code"

RULE 8 — BUSINESS:
  User wants business process analysis or CRM logic.
  → USE "business"

RULE 9 — SYSTEM / META QUESTIONS:
	  User asks about the system itself: "que expertos hay", "who are you", "available agents", "que agentes", "quien eres", "list experts", "show agents", "help", "expertos disponibles".
	  → USE "orchestrator"

RULE 10 — GENERAL KNOWLEDGE (fallback):
  → USE "knowledge"

KEY INSIGHTS:
1. "base de conocimiento" / "knowledge base" = documents, PDFs, memory → "knowledge"
2. "base de datos" / "database" / "SQL" = tables, queries, charts → "data"
3. "Managing the Database Server" (Start/Stop) → "huaweicloud"
4. Short answers like "dale" or "hazlo" follow the context.

AGENTS: ${roles.join(', ')}
Respond ONLY with the agent role name (one word, lowercase).
      `;

      const resp = await LLMService.chat([{ role: 'user', content: classificationPrompt }]);
      const match = resp.match(new RegExp(`\\b(${roles.join('|')})\\b`, 'i'));

      // Handle LLM variations like "KnowledgeBaseAgent" -> "knowledge", "DataAgent" -> "data"
      const roleAliases: Record<string, string> = {
        'knowledgebase': 'knowledge',
        'knowledgebaseagent': 'knowledge',
        'knowledgeagent': 'knowledge',
        'dataagent': 'data',
        'huaweicloudagent': 'huaweicloud',
        'businessagent': 'business',
        'codeagent': 'code',
        'communicationagent': 'communication',
        'orchestratoragent': 'orchestrator'
      };

      const respLower = resp.toLowerCase().replace(/[^a-z]/g, '');
      let matchedRole = match ? match[1].toLowerCase() : null;

      // Check aliases if no direct match
      if (!matchedRole) {
        for (const [alias, role] of Object.entries(roleAliases)) {
          if (respLower.includes(alias)) {
            matchedRole = role;
            break;
          }
        }
      }

      agentRole = (matchedRole || 'knowledge') as AgentRole;
      console.log(`[Orchestrator] Context-aware route → ${agentRole} (raw: "${resp.trim().substring(0, 60)}")`);
      } // end fallback LLM classification
    }

    const roleToCode: Record<string, string> = {
      'huaweicloud': 'HWC',
      'business': 'BIZ',
      'data': 'DAT',
      'code': 'CODE',
      'communication': 'COM',
      'knowledge': 'KNOW',
      'orchestrator': 'ORCH'
    };

    const usedCodes = new Set<string>();
    let finalResponse = '';
    let accumulatedToolResults = '';
    let stickyRole: AgentRole | null = null;

    if (isConfirmation && pending) {
      stickyRole = pending.role;
    }

    if (agentRole === 'orchestrator' as any) {
      const agents = registry.getAllAgents();
      const agentsInfo = agents.map(a => `- **${a.name}** (@${a.role}): ${a.description}`).join('\n');
      const orchPrompt = `
        LANGUAGE: Respond in the same language as the user.
        You are the Orchestrator of HuaweiClaw.
        CRITICAL: List all 7 agent roles. Include yourself as the 7th (@orchestrator).
        For Huawei Cloud, mention the exact number of active regions.
        FORMAT: Markdown.
        AGENTS: ${agentsInfo}
      `;
      finalResponse = await LLMService.chat([
        { role: 'system', content: orchPrompt },
        { role: 'user', content: text }
      ]);
      usedCodes.add('ORCH');
    } else {
      // ── PRE-LOOP FAST PATH: Direct email send if chart is in session ──
      // Intercept before the agent loop to avoid LLM truncating base64 data.
      const emailRegex = /\b(env[ií]a\w*|manda\w*|enviar\w*|send|mail|correo|email)\b.*\b(email|correo|mail|mensaje)\b/i;
      if (emailRegex.test(text.toLowerCase())) {
        const sessionState = await memory.getSessionState(sessionId);
        let chartPath: string | undefined = sessionState?.lastChartPath;
        // If no PNG but ECharts config exists, render PNG on-demand
        if (!chartPath && sessionState?.lastEchartsConfig) {
          try {
            chartPath = await echartsToPng(sessionState.lastEchartsConfig);
            await memory.setSessionState(sessionId, { ...sessionState, lastChartPath: chartPath });
            console.log(`[Pre-loop Fast] Rendered ECharts → PNG on-demand: ${chartPath}`);
          } catch (e: any) {
            console.warn('[Pre-loop Fast] Failed to render ECharts to PNG:', e.message);
          }
        }
        if (chartPath && fs.existsSync(chartPath)) {
          const commAgent = registry.getAgent('communication');
          if (commAgent) {
            const gmailTool = commAgent.tools.find((t: any) => t.name === 'gmail_send');
            if (gmailTool) {
              const chartSize = Math.round(fs.statSync(chartPath).size / 1024);
              console.log(`[Pre-loop Fast] Direct email send with chart file (${chartSize}KB), skipping agent loop`);
              try {
                const emailMatch = text.match(/[\w.-]+@[\w.-]+\.\w+/);
                const to = emailMatch ? emailMatch[0] : '';
                await gmailTool.execute({
                  to,
                  subject: 'Gráfico HuaweiClaw',
                  body: 'Gráfico adjunto.',
                  image_path: chartPath,
                  image_name: 'chart.png'
                });
                finalResponse = '✅ Gráfico enviado por correo electrónico.';
                usedCodes.add('COM');
              } catch (e: any) {
                console.error('[Pre-loop Fast] Direct email failed:', e.message);
                finalResponse = `Error al enviar el correo: ${e.message}`;
              }
              await memory.storeMessage(sessionId, 'assistant', finalResponse);
              return finalResponse;
            }
          }
        }
      }

      // START AGENT LOOP
      let iterations = 0;
      let currentAgent: any = registry.getAgent(agentRole) || registry.getAgent('knowledge');
      usedCodes.add(roleToCode[agentRole] || agentRole.toUpperCase());

      // Inject chart attachment context for communication agent
      if (currentAgent.role === 'communication') {
        const sessionState = await memory.getSessionState(sessionId);
        const chartPath = sessionState?.lastChartPath;
        if (chartPath && fs.existsSync(chartPath)) {
          const chartHint = `\n\n[SYSTEM: A chart image is available at path: ${chartPath}. When using gmail_send, include image_path: "${chartPath}" and image_name: "chart.png" to attach it.]`;
          messages.push({ role: 'system', content: chartHint });
        }
      }

      while (iterations < this.maxIterations) {
        let toolCall = initialToolCall;
        initialToolCall = null;

        if (!toolCall && stickyRole) {
          currentAgent = registry.getAgent(stickyRole) || currentAgent;
          usedCodes.add(roleToCode[stickyRole] || stickyRole.toUpperCase());
          stickyRole = null;
        }

        try {
          if (!toolCall) {
            const thought = await currentAgent.think(messages);
            console.log(`[${currentAgent.role}] Thought: ${thought.substring(0, 500)}${thought.length > 500 ? '...' : ''}`);
            toolCall = await LLMService.extractTools(thought);
            if (!toolCall) {
              // ── A2A DELEGATION CHECK ──
              // If the agent's response contains DELEGATE_TO: <role>, we route
              // that sub-task to the target agent and concatenate the result.
              const delegationMatch = thought.match(/DELEGATE_TO:\s*(\w+)\s*\n([\s\S]*)/i);
              if (delegationMatch) {
                const targetRole = delegationMatch[1].toLowerCase() as AgentRole;
                const delegationInstruction = delegationMatch[2].trim();
                const targetAgent = registry.getAgent(targetRole);

                if (targetAgent && targetRole !== currentAgent.role) {
                  console.log(`[A2A] ${currentAgent.role} → ${targetRole}: ${delegationInstruction.substring(0, 100)}...`);
                  Audit.logA2A(currentAgent.role, targetRole, delegationInstruction);

                  try {
                    const delegationMessages = [
                      ...messages,
                      { role: 'system', content: `[A2A Delegation from ${currentAgent.role}]: ${delegationInstruction}` }
                    ];
                    const delegatedResponse = await targetAgent.think(delegationMessages);
                    usedCodes.add(roleToCode[targetRole] || targetRole.toUpperCase());

                    // Check if the delegated response has a tool call
                    const delegatedToolCall = await LLMService.extractTools(delegatedResponse);
                    if (delegatedToolCall) {
                      // Execute the tool in the target agent
                      let delegatedToolName = delegatedToolCall.name;
                      if ((targetAgent as any).aliases && (targetAgent as any).aliases[delegatedToolName]) {
                        delegatedToolName = (targetAgent as any).aliases[delegatedToolName];
                      }
                      let delegatedTool = targetAgent.tools.find((t: any) => t.name === delegatedToolName);
                      if (!delegatedTool) {
                        delegatedTool = targetAgent.tools.find((t: any) => t.name.toLowerCase() === delegatedToolName.toLowerCase());
                      }

                      if (delegatedTool) {
                        if (delegatedTool.requires_confirmation && !isConfirmation) {
                          await memory.setSessionState(sessionId, { role: targetRole, toolCall: delegatedToolCall });
                          finalResponse = `⚠️ **SECURITY CONSOLE**: A critical operation has been requested by ${targetRole}:\n\n` +
                            `**Action**: ${delegatedTool.description}\n` +
                            `**Parameters**: ${JSON.stringify(delegatedToolCall.args, null, 2)}\n\n` +
                            `Do you want to proceed?`;
                          break;
                        }
                        console.log(`[A2A] Executing ${delegatedTool.name} in ${targetRole}`);
                        const delegatedResult = await delegatedTool.execute(delegatedToolCall.args);
                        const delegatedResultStr = typeof delegatedResult === 'string' ? delegatedResult : JSON.stringify(delegatedResult, null, 2);
                        finalResponse = (accumulatedToolResults ? accumulatedToolResults + '\n\n' : '') + delegatedResultStr;
                      } else {
                        finalResponse = (accumulatedToolResults ? accumulatedToolResults + '\n\n' : '') + delegatedResponse;
                      }
                    } else {
                      finalResponse = (accumulatedToolResults ? accumulatedToolResults + '\n\n' : '') + delegatedResponse;
                    }
                  } catch (delegationError: any) {
                    console.error(`[A2A] Delegation ${currentAgent.role} → ${targetRole} failed:`, delegationError.message);
                    finalResponse = (accumulatedToolResults ? accumulatedToolResults + '\n\n' : '') + thought.replace(/DELEGATE_TO:\s*\w+\s*\n/i, '');
                  }
                  break;
                }
                // If target agent not found or same role, just return the response as-is
                finalResponse = (accumulatedToolResults ? accumulatedToolResults + '\n\n' : '') + thought.replace(/DELEGATE_TO:\s*\w+\s*\n/i, '');
                break;
              }

              finalResponse = (accumulatedToolResults ? accumulatedToolResults + '\n\n' : '') + thought;

              break;
            }
          }

          let toolName = toolCall.name;
          if ((currentAgent as any).aliases && (currentAgent as any).aliases[toolName]) {
            const mappedName = (currentAgent as any).aliases[toolName];
            console.log(`Alias: '${toolName}' → '${mappedName}'`);
            toolName = mappedName;
          }

          let tool = currentAgent.tools.find((t: any) => t.name === toolName);

          if (!tool) {
            const lowName = toolName.toLowerCase();
            tool = currentAgent.tools.find((t: any) => t.name.toLowerCase() === lowName);

            if (!tool) {
              tool = currentAgent.tools.find((t: any) => {
                const tLow = t.name.toLowerCase();
                return tLow === `batch${lowName}` ||
                  tLow === `nova${lowName}` ||
                  tLow === lowName.replace(/s$/, '') ||
                  tLow === `batch${lowName.replace(/s$/, '')}` ||
                  (lowName.startsWith('get') && tLow === lowName.replace('get', 'show')) ||
                  (lowName.startsWith('show') && tLow === lowName.replace('show', 'get')) ||
                  (lowName.startsWith('list') && tLow === lowName.replace('list', 'query')) ||
                   (lowName.startsWith('query') && tLow === lowName.replace('query', 'list')) ||
                  (lowName === 'getjobstatus' && tLow === 'showjob');
              });
            }
            if (tool) console.log(`Aliasing '${toolCall.name}' → '${tool.name}'`);
          }

          if (tool) {
            if (tool.requires_confirmation && !isConfirmation) {
              await memory.setSessionState(sessionId, { role: currentAgent.role, toolCall });
              finalResponse = `⚠️ **SECURITY CONSOLE**: A critical operation has been requested:\n\n` +
                `**Action**: ${tool.description}\n` +
                `**Parameters**: ${JSON.stringify(toolCall.args, null, 2)}\n\n` +
                `Do you want to proceed? Respond 'Confirm' or press the action button in Telegram.`;
              break;
            }

            console.log(`Executing tool ${tool.name} with args: ${JSON.stringify(toolCall.args)}`);
            const result = await tool.execute(toolCall.args);

            const rawResult = typeof result === 'string' ? result : JSON.stringify(result, null, 2);

            
            // If the result contains a markdown image (visualization), we MUST persist it
            if (rawResult.includes('![chart](data:image')) {
              accumulatedToolResults += (accumulatedToolResults ? '\n\n' : '') + rawResult;
              // Store ECharts config in session state for on-demand PNG generation (email/telegram)
              const echartsMatch = rawResult.match(/!\[chart\]\(data:image\/echarts;base64,([^\)]+)\)/);
              if (echartsMatch) {
                try {
                  const echartsJson = Buffer.from(echartsMatch[1], 'base64').toString('utf-8');
                  await memory.setSessionState(sessionId, { ...(await memory.getSessionState(sessionId) || {}), lastEchartsConfig: echartsJson });
                  console.log(`[Orchestrator] ECharts config stored in session (${echartsJson.length} chars)`);
                } catch (e: any) {
                  console.warn('[Orchestrator] Failed to store ECharts config:', e.message);
                }
              }
              // Legacy: also handle PNG if generated by other channels
              const pngMatch = rawResult.match(/!\[chart\]\(data:image\/png;base64,([^\)]+)\)/);
              if (pngMatch) {
                try {
                  const tmpDir = '/tmp/huaweiclaw-charts';
                  if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });
                  const chartId = crypto.randomBytes(8).toString('hex');
                  const chartPath = path.join(tmpDir, `chart-${chartId}.png`);
                  fs.writeFileSync(chartPath, Buffer.from(pngMatch[1], 'base64'));
                  await memory.setSessionState(sessionId, { ...(await memory.getSessionState(sessionId) || {}), lastChartPath: chartPath });
                  console.log(`[Orchestrator] Chart PNG saved to ${chartPath} (${Math.round(fs.statSync(chartPath).size / 1024)}KB)`);
                } catch (e: any) {
                  console.warn('[Orchestrator] Failed to save chart to disk:', e.message);
                }
              }
            }

            const MAX_RESULT_CHARS = 15_000;
            let resultStr = rawResult;
            
            // CRITICAL STRIPPING: Do not pass the raw JSON render config back to the LLM during the active loop. 
            // It only generates token bloat, timeouts, and hallucinated graphic echoes in the final response.
            if (resultStr.startsWith('![chart](data:image/echarts;')) {
              resultStr = '\n[Visualization Graph: Chart rendered successfully on user UI. You do not need to repeat this code.]\n';
            }
            
            if (resultStr.length > MAX_RESULT_CHARS) {
              console.warn(`[Orchestrator] Truncating large tool result (${resultStr.length} chars)`);
              resultStr = resultStr.substring(0, MAX_RESULT_CHARS) + 
                `... [TRUNCATED for context size. Original result was ${rawResult.length} characters long.]`;
            }

            messages.push({ role: 'assistant', content: `TOOL: ${tool.name}\nARGS: ${JSON.stringify(toolCall.args)}` });
            messages.push({ role: 'user', content: `Tool result: ${resultStr}` });

            if (isConfirmation) {
              await memory.clearSessionState(sessionId);
              isConfirmation = false;
            }
            iterations++;
            continue;
          }

          const suggestions = currentAgent.tools
            .map((t: any) => t.name)
            .filter((name: string) =>
              name.toLowerCase().includes(toolCall.name.toLowerCase()) ||
              toolCall.name.toLowerCase().includes(name.toLowerCase())
            )
            .slice(0, 3);

          let errorMsg = `Error: Tool '${toolCall.name}' not found in agent '${currentAgent.role}'.`;
          if (suggestions.length > 0) errorMsg += `\nDid you mean?: ${suggestions.join(', ')}`;

          finalResponse = accumulatedToolResults ? accumulatedToolResults + '\n\n' + errorMsg : errorMsg;
          break;
        } catch (error: any) {
          console.error(`Orchestrator Loop Error in ${currentAgent?.role}:`, error);
          finalResponse = `I'm sorry, an internal error occurred: ${error.message}`;
          break;
        }
      }
      
      // Safety net: If loop exhausted MAX_ITERATIONS but no text was generated
      if (!finalResponse) {
        finalResponse = accumulatedToolResults ? accumulatedToolResults : `Llegué al límite de iteraciones sin poder generar una conclusión.`;
      }

      // ── POST-LOOP A2A AUTO-DELEGATION ──
      // Detect compound requests like "busca X y envía email" where the second
      // part requires a different agent. If the first agent completed its part
      // but the second part is unhandled, delegate automatically.
      if (finalResponse && !finalResponse.includes('SECURITY CONSOLE')) {
        // ── FAST PATH: Direct email send when chart is available ──
        // Skip the full CommunicationAgent LLM loop and execute gmail_send directly.
        const emailRegex = /\b(env[ií]a|manda|send|mail|correo)\s+(un\s+)?(email|correo|mail|mensaje)\b/i;
        if (emailRegex.test(lowerText)) {
          const sessionState = await memory.getSessionState(sessionId);
          let chartPath: string | undefined = sessionState?.lastChartPath;
          // If no PNG but ECharts config exists, render PNG on-demand
          if (!chartPath && sessionState?.lastEchartsConfig) {
            try {
              chartPath = await echartsToPng(sessionState.lastEchartsConfig);
              await memory.setSessionState(sessionId, { ...sessionState, lastChartPath: chartPath });
              console.log(`[A2A Fast] Rendered ECharts → PNG on-demand: ${chartPath}`);
            } catch (e: any) {
              console.warn('[A2A Fast] Failed to render ECharts to PNG:', e.message);
            }
          }
          if (chartPath && fs.existsSync(chartPath)) {
            const commAgent = registry.getAgent('communication');
            if (commAgent) {
              const gmailTool = commAgent.tools.find((t: any) => t.name === 'gmail_send');
              if (gmailTool) {
                const textWithoutChart = finalResponse.replace(/!\[chart\]\(data:image\/(png|echarts);base64,[^\)]+\)/g, '').trim();
                console.log(`[A2A Fast] Direct email send with chart file, skipping LLM loop`);
                try {
                  await gmailTool.execute({
                    to: '',
                    subject: 'Gráfico HuaweiClaw',
                    body: textWithoutChart.substring(0, 2000) || 'Gráfico adjunto.',
                    image_path: chartPath,
                    image_name: 'chart.png'
                  });
                  finalResponse = '✅ Gráfico enviado por correo electrónico con imagen adjunta.';
                  usedCodes.add('COM');
                } catch (e: any) {
                  console.error('[A2A Fast] Direct email failed:', e.message);
                }
              }
            }
          }
        }

        const compoundPatterns: { regex: RegExp; targetRole: AgentRole; extractInstruction: (match: RegExpMatchArray, result: string) => string }[] = [
          {
            // "busca X y envía/manda email" → delegate to communication
            regex: /\b(env[ií]a|manda|send|mail|correo)\s+(un\s+)?(email|correo|mail|mensaje)\b/i,
            targetRole: 'communication',
            extractInstruction: (match, result) => {
              const textWithoutChart = result.replace(/!\[chart\]\(data:image\/png;base64,[^\)]+\)/g, '[Ver gráfico adjunto]').trim();
              // Check for chart file on disk (sync read from session state cached in memory)
              const chartPath = (memory as any)._sessionStates?.[sessionId]?.lastChartPath;
              if (chartPath) {
                return `Send an email with the following information as the email body. IMPORTANT: A chart image is available at this file path — use the image_path parameter to attach it.\n\nBody text:\n${textWithoutChart.substring(0, 2000)}\n\nimage_path: ${chartPath}\nimage_name: chart.png`;
              }
              return `Send an email with the following information as the email body:\n\n${result.substring(0, 2000)}`;
            }
          },
          {
            // "y grafica/visualiza" → delegate to data
            regex: /\b(graf[ií]ca|visualiza|chart|plot|dibuja)\b/i,
            targetRole: 'data',
            extractInstruction: (match, result) => {
              return `Generate a chart from the following data:\n\n${result.substring(0, 2000)}`;
            }
          },
          {
            // "y guarda/memoriza" → delegate to knowledge
            regex: /\b(guarda|memoriza|save|store|aprende|almacena)\s+(en\s+)?(la\s+)?(base de conocimiento|knowledge|memoria)\b/i,
            targetRole: 'knowledge',
            extractInstruction: (match, result) => {
              return `Store the following information in the knowledge base:\n\n${result.substring(0, 3000)}`;
            }
          }
        ];

        for (const pattern of compoundPatterns) {
          // Only delegate if: 1) user's original message matches the compound pattern,
          // 2) the current agent is NOT the target role (avoid double-routing)
          // 3) the response doesn't already contain evidence the second part was done
          if (pattern.regex.test(lowerText) && currentAgent.role !== pattern.targetRole) {
            console.log(`[A2A Auto] Detected compound request: "${pattern.regex.source}" → delegating to ${pattern.targetRole}`);
            Audit.logA2A(currentAgent.role, pattern.targetRole, 'Auto-delegation from compound request');

            try {
              const targetAgent = registry.getAgent(pattern.targetRole);
              if (targetAgent) {
                const delegationInstruction = pattern.extractInstruction(lowerText.match(pattern.regex)!, finalResponse);
                const delegatedResponse = await targetAgent.think([
                  { role: 'system', content: `[A2A Auto-Delegation]: ${delegationInstruction}` }
                ]);
                usedCodes.add(roleToCode[pattern.targetRole] || pattern.targetRole.toUpperCase());

                // Execute tool if the delegated response contains one
                const delegatedToolCall = await LLMService.extractTools(delegatedResponse);
                if (delegatedToolCall) {
                  let delegatedToolName = delegatedToolCall.name;
                  if ((targetAgent as any).aliases && (targetAgent as any).aliases[delegatedToolName]) {
                    delegatedToolName = (targetAgent as any).aliases[delegatedToolName];
                  }
                  let delegatedTool = targetAgent.tools.find((t: any) => t.name === delegatedToolName);
                  if (!delegatedTool) {
                    delegatedTool = targetAgent.tools.find((t: any) => t.name.toLowerCase() === delegatedToolName.toLowerCase());
                  }

                  if (delegatedTool) {
                    if (delegatedTool.requires_confirmation && !isConfirmation) {
                      await memory.setSessionState(sessionId, { role: pattern.targetRole, toolCall: delegatedToolCall });
                      const confirmMsg = `⚠️ **SECURITY CONSOLE**: ${pattern.targetRole} agent requests confirmation:\n\n` +
                        `**Action**: ${delegatedTool.description}\n` +
                        `**Parameters**: ${JSON.stringify(delegatedToolCall.args, null, 2)}\n\n` +
                        `Do you want to proceed?`;
                      finalResponse = finalResponse + '\n\n---\n\n' + confirmMsg;
                    } else {
                      console.log(`[A2A Auto] Executing ${delegatedTool.name} in ${pattern.targetRole}`);
                      const delegatedResult = await delegatedTool.execute(delegatedToolCall.args);
                      const delegatedResultStr = typeof delegatedResult === 'string' ? delegatedResult : JSON.stringify(delegatedResult, null, 2);
                      finalResponse = finalResponse + '\n\n---\n\n' + delegatedResultStr;
                    }
                  } else {
                    finalResponse = finalResponse + '\n\n---\n\n' + delegatedResponse;
                  }
                } else {
                  finalResponse = finalResponse + '\n\n---\n\n' + delegatedResponse;
                }
              }
            } catch (delegationError: any) {
              console.error(`[A2A Auto] Delegation to ${pattern.targetRole} failed:`, delegationError.message);
              // Don't modify finalResponse - keep the original agent's result
            }
            break; // Only delegate once per request
          }
        }
      }
    }

    const prefix = usedCodes.size > 0 ? `[${Array.from(usedCodes).join(', ')}]` : '';
    if (prefix && !finalResponse.trim().startsWith(prefix)) {
      finalResponse = prefix + ' ' + finalResponse.trim();
    } else {
      finalResponse = finalResponse.trim();
    }


    // ── POST-PROCESS: Render ECharts → PNG for non-web channels ──
    // If the response contains ECharts JSON, generate PNG on-demand and save to disk
    // so Telegram/WhatsApp can send it as an image. Do NOT append PNG inline —
    // each channel extracts it from session state when needed.
    const hasEcharts = finalResponse.includes('data:image/echarts;');
    if (hasEcharts) {
      const sessionState = await memory.getSessionState(sessionId);
      const echartsConfig = sessionState?.lastEchartsConfig;
      if (echartsConfig && !sessionState?.lastChartPath) {
        try {
          const chartPath = await echartsToPng(echartsConfig);
          await memory.setSessionState(sessionId, { ...sessionState, lastChartPath: chartPath });
          console.log(`[Orchestrator] ECharts → PNG cached for non-web channels (${Math.round(fs.statSync(chartPath).size / 1024)}KB)`);
        } catch (e: any) {
          console.warn('[Orchestrator] Failed to render ECharts to PNG for non-web:', e.message);
        }
      }
    }

    await memory.storeMessage(sessionId, 'assistant', finalResponse);
    return finalResponse;
  }

  async setPendingFile(sessionId: string, fileData: { fileName: string, content: string }) {
    const currentState = await memory.getSessionState(sessionId) || {};
    await memory.setSessionState(sessionId, { ...currentState, pendingFile: fileData });
  }

  async getPendingFile(sessionId: string) {
    const state = await memory.getSessionState(sessionId);
    return state?.pendingFile || null;
  }

  async clearPendingFile(sessionId: string) {
    const state = await memory.getSessionState(sessionId);
    if (state && state.pendingFile) {
      delete state.pendingFile;
      await memory.setSessionState(sessionId, state);
    }
  }
}

export const orchestrator = new Orchestrator();
