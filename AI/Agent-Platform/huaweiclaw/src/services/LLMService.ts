import OpenAI from 'openai';
import dotenv from 'dotenv';

dotenv.config();

const timeout = parseInt(process.env.TIMEOUT_MS || '60000');

const openai = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
  baseURL: process.env.OPENAI_BASE_URL,
  timeout: timeout
});

export class LLMService {
  static async chat(messages: any[], model: string = process.env.DEFAULT_LLM_MODEL || 'Qwen3-32b'): Promise<string> {
    try {
      // UNIT: Characters (Roughly 4 chars = 1 token)
      // Model limit is 131k tokens (~524k chars). 
      // We set a safe global limit at 400,000 chars (~100k tokens).
      const GLOBAL_MAX_CHARS = 400_000;
      const SYSTEM_MAX_CHARS = 40_000;
      const MESSAGE_MAX_CHARS = 30_000;

      // 1. Individual Message Truncation (Safety first)
      messages = messages.map((m, idx) => {
        let content = m.content || '';
        const limit = idx === 0 ? SYSTEM_MAX_CHARS : MESSAGE_MAX_CHARS;
        
        if (content.length > limit) {
          console.warn(`[LLMService] Message ${idx} is too large (${content.length}). Truncating...`);
          content = content.substring(0, limit) + `... [TRUNCATED for context size]`;
        }
        return { ...m, content };
      });

      // 2. Global History Pruning (If total still too big)
      let totalLength = messages.reduce((acc, m) => acc + (m.content || '').length, 0);

      if (totalLength > GLOBAL_MAX_CHARS) {
        console.warn(`[LLMService] Aggressively pruning history. Total length: ${totalLength}`);
        const system = messages[0];
        const tail = messages.slice(-4);
        const middle = messages.slice(1, -4);
        
        let currentSize = (system.content?.length || 0) + tail.reduce((acc, m) => acc + (m.content?.length || 0), 0);
        const allowedMiddle = GLOBAL_MAX_CHARS - currentSize;
        
        let prunedMiddle = [];
        let runningSize = 0;
        // Keep as much of the recent middle as possible
        for (let i = middle.length - 1; i >= 0; i--) {
          const mSize = middle[i].content?.length || 0;
          if (runningSize + mSize < allowedMiddle) {
            prunedMiddle.unshift(middle[i]);
            runningSize += mSize;
          } else {
            break;
          }
        }
        messages = [system, ...prunedMiddle, ...tail];
        console.log(`[LLMService] Global prompt pruned from ${totalLength} to ${messages.reduce((acc, m) => acc + (m.content || '').length, 0)} chars.`);
      }

      const response = await openai.chat.completions.create({
        model,
        messages,
        temperature: 0.7,
      });

      return response.choices[0].message.content || '';
    } catch (error: any) {
      console.error('LLM Error:', error?.message || error);
      return `I encountered an error while thinking. (Detalle: ${error?.message || 'Unknown'})`;
    }
  }

  static async extractTools(text: string): Promise<{ name: string; args: any } | null> {
    try {
      let name = '';
      let argsPart = '';

      const toolMatch = text.match(/[\*]*TOOL[:][\*]*\s*([\w\-]+)/i);
      if (toolMatch) {
        name = toolMatch[1].trim();
        argsPart = text.split(/[\*]*ARGS[:][\*]*/i)[1] || '';
      } else {
        // Fallback for LLM hallucination like 'analyze_database: {"query": "..."}'
        const fallbackMatch = text.match(/([\w\-]+)\s*:\s*\{/);
        if (!fallbackMatch || fallbackMatch[1].toUpperCase() === 'ARGS' || fallbackMatch[1].toUpperCase() === 'TOOL') {
          return null;
        }
        name = fallbackMatch[1].trim();
        argsPart = text.substring(fallbackMatch.index! + name.length);
      }

      const argsStr = this.findBalancedBraces(argsPart);
      if (!argsStr) return null;

      // Clean markdown, remove comments and trailing commas
      let cleaned = argsStr
        .replace(/```json/gi, '')
        .replace(/```/g, '')
        .replace(/^\s*\*\*/g, '')  // Remove leading markdown bold
        .replace(/\*\*\s*$/g, '')  // Remove trailing markdown bold
        .replace(/^[>\s]+/, '')    // Remove leading > and whitespace
        .trim();

      const sanitized = this.sanitizeJson(cleaned);

      // Validate JSON before parsing
      if (!sanitized.startsWith('{') && !sanitized.startsWith('[')) {
        console.warn('[LLMService] Extracted args don\'t look like JSON:', sanitized.substring(0, 50));
        return null;
      }

      return {
        name,
        args: JSON.parse(sanitized)
      };
    } catch (e) {
      console.error('Failed to parse tool call from text:', e);
      // Log the problematic text for debugging
      console.error('Text that failed parsing:', text.substring(0, 200));
    }
    return null;
  }

  private static sanitizeJson(json: string): string {
    // 1. Strip comments
    let stripped = this.stripComments(json);
    // 2. Remove trailing commas before } or ]
    return stripped.replace(/,\s*([\]}])/g, '$1').trim();
  }

  private static stripComments(json: string): string {
    let result = '';
    let inString = false;
    let escape = false;
    
    for (let i = 0; i < json.length; i++) {
        const char = json[i];
        const next = json[i + 1];

        if (inString) {
            result += char;
            if (escape) {
                escape = false;
            } else if (char === '\\') {
                escape = true;
            } else if (char === '"') {
                inString = false;
            }
        } else {
            if (char === '"') {
                inString = true;
                result += char;
            } else if (char === '/' && next === '/') {
                // Skip single-line comment: // until end of line
                while (i < json.length && json[i] !== '\n') i++;
                result += (json[i] || '');
            } else if (char === '/' && next === '*') {
                // Skip multi-line comment: /* until */
                i += 2;
                while (i < json.length && !(json[i] === '*' && json[i + 1] === '/')) {
                    i++;
                }
                i += 1; // Skip the '*' (next iteration of loop will skip '/')
            } else {
                result += char;
            }
        }
    }
    return result;
  }

  private static findBalancedBraces(text: string): string | null {
    let braceCount = 0;
    let startIndex = text.indexOf('{');
    if (startIndex === -1) return null;
    
    for (let i = startIndex; i < text.length; i++) {
      if (text[i] === '{') braceCount++;
      else if (text[i] === '}') braceCount--;
      
      if (braceCount === 0) {
        return text.substring(startIndex, i + 1);
      }
    }
    return null;
  }
}
