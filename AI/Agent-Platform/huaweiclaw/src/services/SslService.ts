import { execSync } from 'child_process';
import fs from 'fs';
import path from 'path';

const CERT_DIR = path.join(process.cwd(), '.ssl');
const CERT_FILE = path.join(CERT_DIR, 'cert.pem');
const KEY_FILE = path.join(CERT_DIR, 'key.pem');

/**
 * Get or generate a self-signed TLS certificate for HTTPS.
 * Uses openssl if available, otherwise returns null.
 */
export function getSelfSignedCert(): { cert: Buffer; key: Buffer } | null {
  // Reuse existing cert
  if (fs.existsSync(CERT_FILE) && fs.existsSync(KEY_FILE)) {
    return {
      cert: fs.readFileSync(CERT_FILE),
      key: fs.readFileSync(KEY_FILE)
    };
  }

  // Generate with openssl
  try {
    fs.mkdirSync(CERT_DIR, { recursive: true });
    execSync(
      `openssl req -x509 -newkey rsa:2048 -keyout "${KEY_FILE}" -out "${CERT_FILE}" -days 365 -nodes -subj "/CN=HuaweiClaw"`,
      { stdio: 'pipe', timeout: 10_000 }
    );
    console.log('[SSL] Generated self-signed certificate in .ssl/');
    return {
      cert: fs.readFileSync(CERT_FILE),
      key: fs.readFileSync(KEY_FILE)
    };
  } catch {
    console.warn('[SSL] openssl not available, cannot generate self-signed cert');
    return null;
  }
}
