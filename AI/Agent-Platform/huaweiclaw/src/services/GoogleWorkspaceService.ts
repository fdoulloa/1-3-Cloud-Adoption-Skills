import { google } from 'googleapis';
import fs from 'fs';
import path from 'path';
import { Audit } from '../core/Audit.js';

/**
 * Google Workspace Service using the official googleapis Node.js SDK.
 * Supports Gmail, Calendar, and Drive with OAuth2 authentication.
 *
 * Setup: Place your OAuth2 client_secret JSON in the project root,
 * and set GOOGLE_ACCESS_TOKEN + GOOGLE_REFRESH_TOKEN in .env
 * (obtained via a one-time OAuth2 flow).
 */
export class GoogleWorkspaceService {
  private static auth: any = null;
  private static initialized = false;

  static async initialize(): Promise<boolean> {
    if (this.initialized) return true;

    try {
      const clientSecretPath = path.join(process.cwd(), 'client_secret_google.json');
      if (!fs.existsSync(clientSecretPath)) {
        // Try the existing file pattern
        const altPath = path.join(process.cwd(), 'client_secret_207025669188-lfh05nvdafj75hm7ojfbipd4pdbdmsdt.apps.googleusercontent.com.json');
        if (!fs.existsSync(altPath)) {
          console.warn('[GoogleWorkspace] No client_secret JSON found. Google Workspace tools will be limited.');
          this.initialized = true;
          return false;
        }
      }

      // Load client secrets
      const secretFile = fs.existsSync(path.join(process.cwd(), 'client_secret_google.json'))
        ? path.join(process.cwd(), 'client_secret_google.json')
        : path.join(process.cwd(), 'client_secret_207025669188-lfh05nvdafj75hm7ojfbipd4pdbdmsdt.apps.googleusercontent.com.json');

      const credentials = JSON.parse(fs.readFileSync(secretFile, 'utf-8'));
      const installed = credentials.installed || credentials.web;
      const { client_id, client_secret, redirect_uris } = installed;

      const oauth2Client = new google.auth.OAuth2(
        client_id,
        client_secret,
        process.env.GOOGLE_REDIRECT_URI || redirect_uris?.[0] || 'http://localhost'
      );

      // Set credentials from env (access + refresh tokens)
      const accessToken = process.env.GOOGLE_ACCESS_TOKEN;
      const refreshToken = process.env.GOOGLE_REFRESH_TOKEN;

      if (refreshToken) {
        oauth2Client.setCredentials({
          access_token: accessToken || undefined,
          refresh_token: refreshToken
        });
        this.auth = oauth2Client;
        console.log('[GoogleWorkspace] OAuth2 initialized with refresh token.');
      } else {
        console.warn('[GoogleWorkspace] No GOOGLE_REFRESH_TOKEN in .env. Run OAuth2 flow first.');
        console.warn('[GoogleWorkspace] Visit /api/google/auth to start the OAuth2 flow.');
        this.auth = oauth2Client; // Store for auth URL generation
      }

      this.initialized = true;
      return !!refreshToken;
    } catch (error: any) {
      console.error('[GoogleWorkspace] Initialization error:', error.message);
      this.initialized = true;
      return false;
    }
  }

  static getAuth(): any {
    return this.auth;
  }

  // ── Gmail ──────────────────────────────────────────────────────────

  static async gmailSearch(query: string, maxResults: number = 10): Promise<any[]> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const gmail = google.gmail({ version: 'v1', auth: this.auth });

    const res = await gmail.users.messages.list({
      userId: 'me',
      q: query,
      maxResults
    });

    const messages = res.data.messages || [];
    const results: any[] = [];

    for (const msg of messages) {
      const detail = await gmail.users.messages.get({
        userId: 'me',
        id: msg.id!,
        format: 'metadata',
        metadataHeaders: ['Subject', 'From', 'Date']
      });

      const headers = detail.data.payload?.headers || [];
      results.push({
        id: msg.id,
        subject: headers.find(h => h.name === 'Subject')?.value || '',
        from: headers.find(h => h.name === 'From')?.value || '',
        date: headers.find(h => h.name === 'Date')?.value || '',
        snippet: detail.data.snippet || ''
      });
    }

    return results;
  }

  static async gmailGet(messageId: string): Promise<any> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const gmail = google.gmail({ version: 'v1', auth: this.auth });

    const res = await gmail.users.messages.get({
      userId: 'me',
      id: messageId,
      format: 'full'
    });

    const headers = res.data.payload?.headers || [];
    const body = res.data.payload?.body?.data
      ? Buffer.from(res.data.payload.body.data, 'base64').toString('utf-8')
      : '';

    return {
      id: res.data.id,
      subject: headers.find(h => h.name === 'Subject')?.value || '',
      from: headers.find(h => h.name === 'From')?.value || '',
      to: headers.find(h => h.name === 'To')?.value || '',
      date: headers.find(h => h.name === 'Date')?.value || '',
      body
    };
  }

  static async gmailSend(to: string, subject: string, body: string, imagePath?: string, imageBase64?: string, imageName?: string): Promise<any> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const gmail = google.gmail({ version: 'v1', auth: this.auth });

    // RFC 2047 encode subject for non-ASCII chars
    const encodedSubject = /[^\x00-\x7F]/.test(subject)
      ? `=?utf-8?B?${Buffer.from(subject, 'utf-8').toString('base64')}?=`
      : subject;

    // If a file path is provided, read it from disk
    let attachmentBase64 = imageBase64;
    let attachmentName = imageName || 'chart.png';
    let attachmentMime = 'image/png';
    if (imagePath && fs.existsSync(imagePath)) {
      const fileBuf = fs.readFileSync(imagePath);
      attachmentBase64 = fileBuf.toString('base64');
      attachmentName = path.basename(imagePath);
      const ext = path.extname(imagePath).toLowerCase();
      if (ext === '.jpg' || ext === '.jpeg') attachmentMime = 'image/jpeg';
      else if (ext === '.gif') attachmentMime = 'image/gif';
      else if (ext === '.pdf') attachmentMime = 'application/pdf';
      console.log(`[GoogleWorkspace] Attachment loaded from ${imagePath} (${Math.round(fileBuf.length / 1024)}KB)`);
    } else if (imagePath) {
      console.warn(`[GoogleWorkspace] Attachment path not found: ${imagePath}`);
    }

    // Append signature
    const signedBody = body + '\n\n—\nAgente HuaweiClaw';

    // Build MIME message
    const boundary = `==huaweiclaw_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const parts: string[] = [];

    // Headers
    parts.push(`To: ${to}`);
    parts.push(`Subject: ${encodedSubject}`);
    parts.push('MIME-Version: 1.0');
    parts.push(`Content-Type: multipart/mixed; boundary="${boundary}"`);
    parts.push('');

    // Text body part
    const bodyBase64 = Buffer.from(signedBody, 'utf-8').toString('base64');
    parts.push(`--${boundary}`);
    parts.push('Content-Type: text/plain; charset=utf-8');
    parts.push('Content-Transfer-Encoding: base64');
    parts.push('');
    // Split body base64 into 76-char lines
    for (let i = 0; i < bodyBase64.length; i += 76) {
      parts.push(bodyBase64.substring(i, i + 76));
    }

    // Attachment part
    if (attachmentBase64) {
      parts.push('');
      parts.push(`--${boundary}`);
      parts.push(`Content-Type: ${attachmentMime}; name="${attachmentName}"`);
      parts.push('Content-Transfer-Encoding: base64');
      parts.push(`Content-Disposition: attachment; filename="${attachmentName}"`);
      parts.push('');
      // Split attachment base64 into 76-char lines (MIME requirement)
      for (let i = 0; i < attachmentBase64.length; i += 76) {
        parts.push(attachmentBase64.substring(i, i + 76));
      }
    }

    parts.push('');
    parts.push(`--${boundary}--`);

    const mimeMessage = parts.join('\r\n');
    const raw = Buffer.from(mimeMessage, 'utf-8').toString('base64url');
    const res = await gmail.users.messages.send({ userId: 'me', requestBody: { raw } });
    return { id: res.data.id };
  }

  // ── Calendar ───────────────────────────────────────────────────────

  static async calendarList(calendarId: string = 'primary', timeMin?: string, timeMax?: string): Promise<any[]> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const calendar = google.calendar({ version: 'v3', auth: this.auth });

    const res = await calendar.events.list({
      calendarId,
      timeMin: timeMin || new Date().toISOString(),
      timeMax: timeMax || new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
      singleEvents: true,
      orderBy: 'startTime',
      maxResults: 20
    });

    return (res.data.items || []).map(event => ({
      id: event.id,
      summary: event.summary,
      start: event.start?.dateTime || event.start?.date,
      end: event.end?.dateTime || event.end?.date,
      location: event.location,
      attendees: event.attendees?.map(a => a.email)
    }));
  }

  static async calendarCreate(calendarId: string, summary: string, start: string, end: string, description?: string): Promise<any> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const calendar = google.calendar({ version: 'v3', auth: this.auth });

    const res = await calendar.events.insert({
      calendarId,
      requestBody: {
        summary,
        description,
        start: { dateTime: start },
        end: { dateTime: end }
      }
    });

    return { id: res.data.id, summary: res.data.summary, start: res.data.start?.dateTime, end: res.data.end?.dateTime };
  }

  // ── Drive ──────────────────────────────────────────────────────────

  static async driveSearch(query: string, pageSize: number = 10): Promise<any[]> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const drive = google.drive({ version: 'v3', auth: this.auth });

    const res = await drive.files.list({
      q: query,
      pageSize,
      fields: 'files(id,name,mimeType,modifiedTime,size,webViewLink)'
    });

    return res.data.files || [];
  }

  static async driveGet(fileId: string): Promise<any> {
    if (!this.auth) throw new Error('Google Workspace not authenticated');
    const drive = google.drive({ version: 'v3', auth: this.auth });

    const res = await drive.files.get({
      fileId,
      fields: 'id,name,mimeType,modifiedTime,size,webViewLink,description'
    });

    return res.data;
  }

  /** Generate the OAuth2 authorization URL for initial setup */
  static getAuthUrl(): string {
    if (!this.auth) throw new Error('OAuth2 client not initialized');
    return this.auth.generateAuthUrl({
      access_type: 'offline',
      scope: [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/drive.readonly'
      ],
      prompt: 'consent'
    });
  }

  /** Exchange authorization code for tokens */
  static async exchangeCode(code: string): Promise<any> {
    if (!this.auth) throw new Error('OAuth2 client not initialized');
    const { tokens } = await this.auth.getToken(code);
    this.auth.setCredentials(tokens);
    return tokens;
  }
}
