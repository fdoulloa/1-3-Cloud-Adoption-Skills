import { execFile } from 'child_process';
import { promisify } from 'util';
import { Audit } from '../core/Audit.js';

const execFilePromise = promisify(execFile);

export class CliService {
  /**
   * Executes a CLI command and returns the stdout.
   * Includes basic safety checks and logging.
   */
  static async execute(command: string, args: string[]): Promise<string> {
    try {
      // Ensure all arguments are strings and remove undefined/null safely
      const cleanArgs = args.filter(a => a !== undefined && a !== null).map(String);
      
      console.log(`Executing CLI: ${command} ${cleanArgs.join(' ')}`);
      // Use execFile to prevent truncation on newlines or quotes in Windows cmd
      const { stdout, stderr } = await execFilePromise(command, cleanArgs);
      
      if (stderr && !stdout) {
        throw new Error(stderr);
      }
      
      return stdout;
    } catch (error: any) {
      console.error(`CLI execution error: ${error.message}`);
      throw new Error(`Execution failed: ${error.message}`);
    }
  }
}
