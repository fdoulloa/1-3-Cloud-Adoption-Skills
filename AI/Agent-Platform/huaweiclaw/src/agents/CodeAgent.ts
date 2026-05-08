import { Agent, Tool } from '../core/Agent.js';
import { LLMService } from '../services/LLMService.js';
import { Audit } from '../core/Audit.js';
import { SkillService } from '../services/SkillService.js';
import { SandboxService } from '../services/SandboxService.js';

export class CodeAgent extends Agent {
  private skillService: SkillService;

  constructor() {
    super(
      'code-agent',
      'Superpowered Senior Engineer',
      'code',
      process.env.CODE_LLM_MODEL || process.env.DEFAULT_LLM_MODEL || 'DeepSeek-V3',
      'Senior software engineer specializing in writing, debugging, and executing high-quality code and automation scripts using specialized workflows.'
    );
    this.skillService = new SkillService();
    this.initializeTools();
  }

  private initializeTools() {
    this.tools = [
      this.runPythonTool(),
      this.findSkillTool(),
      this.useSkillTool()
    ];
  }

  async think(messages: any[]): Promise<string> {
    const systemPrompt = `
      You are the Code Agent - a senior software engineer.
      You write, debug, and explain code.

      TOOLS AVAILABLE:
      - find_skill: List available engineering workflows. ARGS: {}
      - use_skill: Read instructions for a skill. ARGS: {"skillName": "name"}
      - run_python: Execute Python code in a Docker sandbox. ARGS: {"code": "print('Hello')"}

      WORKFLOW:
      1. For complex tasks, you MAY use skills for guidance (optional).
      2. Write code directly in your response using markdown code blocks.
      3. Use run_python to test code if needed.

      WHEN TO USE TOOLS vs TEXT:
      - Use TOOL calls when you need to: list skills, read a skill, or execute code.
      - Use TEXT response when: presenting code, explaining, or completing a task.

      EXAMPLES:
      - User: "Write a Flask app" → Respond with code in markdown blocks (no TOOL call)
      - User: "Test this code" → TOOL: run_python ARGS: {"code": "..."}
      - User: "What skills are available?" → TOOL: find_skill ARGS: {}

      CRITICAL:
      - After receiving skill instructions, implement them by WRITING CODE in your response.
      - DO NOT loop forever calling tools. Eventually provide a TEXT response with code.
      - Maximum 2-3 tool calls before providing a final response.

      Response format for TOOL: TOOL: tool_name ARGS: {"param": "value"}
      Response format for TEXT: Just write your response with code in \`\`\` blocks.
    `;
    return await LLMService.chat([
      { role: 'system', content: systemPrompt },
      ...messages
    ], this.model);
  }

  private findSkillTool(): Tool {
    return {
      name: 'find_skill',
      description: 'Lists all available engineering skills/workflows from the Superpowers library.',
      parameters: {},
      execute: async () => {
        Audit.logToolCall(this.id, 'find_skill', {});
        const skills = await this.skillService.listSkills();
        return { skills };
      }
    };
  }

  private useSkillTool(): Tool {
    return {
      name: 'use_skill',
      description: 'Loads the specific instructions and workflow for an engineering skill.',
      parameters: {
        skillName: { type: 'string', description: 'The name of the skill to load (e.g. bootstrapping, test-driven-development)' }
      },
      execute: async ({ skillName }) => {
        Audit.logToolCall(this.id, 'use_skill', { skillName });
        const skill = await this.skillService.getSkill(skillName);
        if (!skill) return { error: `Skill '${skillName}' not found.` };
        return {
          name: skill.name,
          description: skill.description,
          instructions: skill.content
        };
      }
    };
  }

  private runPythonTool(): Tool {
    return {
      name: 'run_python',
      description: 'Executes Python code in an isolated Docker sandbox (no network, memory-limited, read-only fs). Falls back to local exec if Docker unavailable.',
      parameters: {
        code: { type: 'string', description: 'The python code to execute' }
      },
      execute: async ({ code }) => {
        try {
          const result = await SandboxService.executePython(code, this.id);
          if (result.stderr && !result.stdout) {
            return { error: result.stderr };
          }
          return { stdout: result.stdout, stderr: result.stderr };
        } catch (error: any) {
          return { error: error.message, stdout: error.stdout || '', stderr: error.stderr || '' };
        }
      }
    };
  }
}
