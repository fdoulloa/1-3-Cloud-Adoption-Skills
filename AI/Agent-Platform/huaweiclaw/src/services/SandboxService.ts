import { execFile } from 'child_process';
import { promisify } from 'util';
import { writeFile, unlink, mkdir } from 'fs/promises';
import path from 'path';
import { Audit } from '../core/Audit.js';

const execFilePromise = promisify(execFile);

const SANDBOX_IMAGE = process.env.SANDBOX_DOCKER_IMAGE || 'python:3.12-slim';
const SANDBOX_TIMEOUT = parseInt(process.env.SANDBOX_TIMEOUT_MS || '30000');
const SANDBOX_MAX_MEMORY = process.env.SANDBOX_MAX_MEMORY || '128m';
const SANDBOX_DIR = '/tmp/huaweiclaw-sandbox';

export class SandboxService {
  private static initialized = false;

  /** Ensure the sandbox temp directory exists */
  static async init(): Promise<void> {
    if (this.initialized) return;
    try {
      await mkdir(SANDBOX_DIR, { recursive: true });
      this.initialized = true;
    } catch {
      // Directory may already exist
      this.initialized = true;
    }
  }

  /**
   * Execute Python code inside a Docker container for full isolation.
   * Falls back to local execution if Docker is unavailable.
   */
  static async executePython(code: string, agentId: string): Promise<{ stdout: string; stderr: string }> {
    Audit.logToolCall(agentId, 'run_python_sandbox', { codeLength: code.length });

    await this.init();

    // Try Docker first
    try {
      return await this.executeInDocker(code);
    } catch (dockerError: any) {
      // If Docker fails (daemon not running, permission denied), fall back to local
      if (dockerError.message?.includes('docker') || dockerError.code === 'ENOENT') {
        console.warn('[Sandbox] Docker unavailable, falling back to local execFile (unsandboxed)');
        Audit.logSecurityEvent('sandbox_fallback', { reason: dockerError.message });
        return await this.executeLocal(code);
      }
      throw dockerError;
    }
  }

  private static async executeInDocker(code: string): Promise<{ stdout: string; stderr: string }> {
    // Write code to a temp file (avoids shell injection via command args)
    const scriptId = `hc_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
    const hostPath = path.join(SANDBOX_DIR, `${scriptId}.py`);

    await writeFile(hostPath, code, { mode: 0o644 });

    try {
      const { stdout, stderr } = await execFilePromise('docker', [
        'run',
        '--rm',                    // Remove container after execution
        '--network', 'none',       // No network access
        '--memory', SANDBOX_MAX_MEMORY,  // Memory limit
        '--pids-limit', '50',      // Process limit
        '--read-only',             // Read-only filesystem
        '--tmpfs', '/tmp:size=10m', // Writable temp only
        '-v', `${hostPath}:/app/script.py:ro`,  // Mount script read-only
        '-w', '/app',
        SANDBOX_IMAGE,
        'python3', '/app/script.py'
      ], {
        timeout: SANDBOX_TIMEOUT,
        maxBuffer: 1024 * 1024,
        killSignal: 'SIGKILL'
      });

      return { stdout: stdout || '', stderr: stderr || '' };
    } finally {
      // Clean up temp file
      try { await unlink(hostPath); } catch { /* ignore */ }
    }
  }

  private static async executeLocal(code: string): Promise<{ stdout: string; stderr: string }> {
    const { stdout, stderr } = await execFilePromise('python3', ['-c', code], {
      timeout: 30_000,
      maxBuffer: 1024 * 1024,
      killSignal: 'SIGKILL'
    });
    return { stdout: stdout || '', stderr: stderr || '' };
  }

  /** Pre-pull the sandbox image if not available locally */
  static async pullImage(): Promise<void> {
    try {
      console.log(`[Sandbox] Checking Docker image: ${SANDBOX_IMAGE}`);
      await execFilePromise('docker', ['image', 'inspect', SANDBOX_IMAGE], { timeout: 5_000 });
      console.log(`[Sandbox] Image ${SANDBOX_IMAGE} already available.`);
    } catch {
      console.log(`[Sandbox] Pulling image ${SANDBOX_IMAGE}...`);
      await execFilePromise('docker', ['pull', SANDBOX_IMAGE], { timeout: 120_000 });
      console.log(`[Sandbox] Image ${SANDBOX_IMAGE} pulled successfully.`);
    }
  }
}
