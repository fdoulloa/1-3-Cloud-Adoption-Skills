import { spawn, ChildProcess } from 'child_process';
import { Audit } from '../core/Audit.js';

export interface McpProcessOptions {
  command: string;
  args: string[];
  tool: string;
  toolArgs: any;
  timeout?: number;
}

interface McpSession {
  child: ChildProcess;
  idCounter: number;
  pending: Map<number, (msg: any) => void>;
  handshakeComplete: Promise<void>;
  buffer: string;
}

export class McpProcessService {
  private static sessions: Map<string, McpSession> = new Map();

  /**
   * Executes a tool from a local MCP server.
   * Maintains persistent connections to servers to avoid re-installation and handshake overhead.
   */
  static async executeTool(options: McpProcessOptions): Promise<any> {
    const { command, args, tool, toolArgs, timeout: customTimeout } = options;
    const TIMEOUT_MS = customTimeout || 60_000;
    const sessionId = `${command} ${args.join(' ')}`;

    let session = this.sessions.get(sessionId);

    // Start server if not running or if exited
    if (!session || (session.child as any).exitCode !== null) {
      console.log(`[MCP] Starting persistent server: ${sessionId}`);
      session = this.startSession(command, args);
      this.sessions.set(sessionId, session);
    }

    // Wait for handshake if it's a new session
    await session.handshakeComplete;

    return new Promise((resolve, reject) => {
      const waitTimeout = setTimeout(() => {
        reject(new Error(`MCP tool [${tool}] timed out waiting for response (Session: ${sessionId})`));
      }, TIMEOUT_MS);

      this.sendRequest(session!, 'tools/call', {
        name: tool,
        arguments: toolArgs
      })
      .then(result => {
        clearTimeout(waitTimeout);
        // MCP result.content can contain 'text' or 'image'
        if (result?.content && Array.isArray(result.content)) {
          const parts = result.content.map((c: any) => {
            if (c.type === 'text') return c.text;
            if (c.type === 'image') return `![chart](data:${c.mimeType};base64,${c.data})`;
            return JSON.stringify(c);
          });
          resolve(parts.join('\n'));
        } else {
          resolve(result ?? 'Tool executed successfully.');
        }
      })
      .catch(err => {
        clearTimeout(waitTimeout);
        // If error is related to process death, remove from cache
        if (err.message.includes('closed') || err.message.includes('pipe')) {
          this.sessions.delete(sessionId);
        }
        reject(err);
      });
    });
  }

  private static startSession(command: string, args: string[]): McpSession {
    const child = spawn(command, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      shell: true,
      env: { ...process.env }
    });

    const session: McpSession = {
      child,
      idCounter: 1,
      pending: new Map(),
      buffer: '',
      handshakeComplete: Promise.resolve() // replaced below
    };

    child.stdout.on('data', (chunk: Buffer) => {
      session.buffer += chunk.toString();
      const lines = session.buffer.split('\n');
      session.buffer = lines.pop() ?? '';

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const msg = JSON.parse(trimmed);
          if (msg.id !== undefined && session.pending.has(msg.id)) {
            const handler = session.pending.get(msg.id)!;
            session.pending.delete(msg.id);
            handler(msg);
          }
        } catch { /* ignore non-json */ }
      }
    });

    child.stderr.on('data', (data: Buffer) => {
      console.debug(`[MCP stderr] ${data.toString().trim()}`);
    });

    child.on('close', (code) => {
      console.log(`[MCP] Server ${command} closed with code ${code}`);
      // Reject any pending requests
      for (const [id, handler] of session.pending) {
        handler({ error: { message: `MCP process closed unexpectedly (code ${code})` } });
      }
      session.pending.clear();
    });

    // ── Handshake ────────────────────────────────────────────────────
    session.handshakeComplete = (async () => {
      await this.sendRequest(session, 'initialize', {
        protocolVersion: '2024-11-05',
        capabilities: { roots: { listChanged: false } },
        clientInfo: { name: 'HuaweiClaw', version: '1.0.0' }
      });
      this.sendNotification(session, 'notifications/initialized', {});
      console.log(`[MCP] Handshake complete for server: ${command}`);
    })();

    return session;
  }

  private static sendRequest(session: McpSession, method: string, params: any): Promise<any> {
    return new Promise((res, rej) => {
      const id = session.idCounter++;
      session.pending.set(id, (msg) => {
        if (msg.error) rej(new Error(`MCP error: ${msg.error.message || JSON.stringify(msg.error)}`));
        else res(msg.result);
      });
      const payload = JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n';
      if (!session.child.stdin?.writable) {
         return rej(new Error('MCP stdin pipe not writable'));
      }
      session.child.stdin.write(payload);
    });
  }

  private static sendNotification(session: McpSession, method: string, params: any) {
    const payload = JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n';
    session.child.stdin?.write(payload);
  }
}

