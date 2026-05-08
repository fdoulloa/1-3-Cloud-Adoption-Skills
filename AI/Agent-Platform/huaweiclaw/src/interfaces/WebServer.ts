import express from 'express';
import path from 'path';
import multer from 'multer';
import { fileURLToPath } from 'url';
import https from 'https';
import fs from 'fs';
import { orchestrator } from '../core/Orchestrator.js';
import { memory } from '../core/Memory.js';
import { DeepgramService } from '../services/DeepgramService.js';
import { FileService } from '../services/FileService.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const upload = multer({ limits: { fileSize: 50 * 1024 * 1024 } }); // 50MB limit

export const app = express();
const port = process.env.MCP_WEB_PORT || 3001;

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));
app.use(express.static(path.join(__dirname, '../../public')));

app.post('/api/chat', async (req, res) => {
  const { sessionId, message, stream } = req.body;
  if (!message) return res.status(400).json({ error: 'Message is required' });

  try {
    const sid = sessionId || 'web-session';
    if (stream) {
      // Server-Sent Events streaming mode
      res.setHeader('Content-Type', 'text/event-stream');
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Connection', 'keep-alive');
      res.write(`data: ${JSON.stringify({ type: 'start' })}\n\n`);

      const response = await orchestrator.processRequest(sid, message);

      // Stream the response in chunks for progressive rendering
      const chunkSize = 50;
      for (let i = 0; i < response.length; i += chunkSize) {
        const chunk = response.substring(i, i + chunkSize);
        res.write(`data: ${JSON.stringify({ type: 'chunk', content: chunk })}\n\n`);
      }
      res.write(`data: ${JSON.stringify({ type: 'done' })}\n\n`);
      res.end();
    } else {
      const response = await orchestrator.processRequest(sid, message);
      res.json({ response });
    }
  } catch (error) {
    console.error('Web Chat Error:', error);
    if (!res.headersSent) {
      res.status(500).json({ error: 'Internal server error' });
    }
  }
});

app.post('/api/memory/clear', async (req, res) => {
  const { sessionId } = req.body;
  try {
    await memory.clearHistory(sessionId || 'web-session');
    res.json({ success: true, message: 'Memory cleared' });
  } catch (error) {
    console.error('Memory Clear Error:', error);
    res.status(500).json({ error: 'Failed to clear memory' });
  }
});

app.post('/api/stt', upload.single('audio'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'Audio file is required' });
  
  try {
    const text = await DeepgramService.stt(req.file.buffer);
    res.json({ text });
  } catch (error) {
    console.error('STT API Error:', error);
    res.status(500).json({ error: 'STT failed' });
  }
});

app.post('/api/tts', async (req, res) => {
  const { text } = req.body;
  if (!text) return res.status(400).json({ error: 'Text is required' });
  
  try {
    const audioBuffer = await DeepgramService.tts(text);
    res.set('Content-Type', 'audio/mpeg');
    res.send(audioBuffer);
  } catch (error) {
    console.error('TTS API Error:', error);
    res.status(500).json({ error: 'TTS failed' });
  }
});

// Health check endpoint for observability
app.get('/api/health', async (req, res) => {
  const { registry } = await import('../core/Registry.js');
  const agents = registry.getAllAgents();
  const dbStatus = memory.getDb() ? 'connected' : 'disconnected';
  res.json({
    status: 'ok',
    uptime: process.uptime(),
    agents: agents.map(a => ({ role: a.role, name: a.name, model: a.model, tools: a.tools.length })),
    memory: dbStatus,
    timestamp: new Date().toISOString()
  });
});

// Google OAuth2 flow endpoints
app.get('/api/google/auth', async (req, res) => {
  try {
    const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
    await GoogleWorkspaceService.initialize();
    const url = GoogleWorkspaceService.getAuthUrl();
    res.redirect(url);
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.get('/api/google/callback', async (req, res) => {
  try {
    const { GoogleWorkspaceService } = await import('../services/GoogleWorkspaceService.js');
    const tokens = await GoogleWorkspaceService.exchangeCode(req.query.code as string);
    res.json({
      message: 'Google Workspace authenticated! Add these to your .env:',
      GOOGLE_ACCESS_TOKEN: tokens.access_token,
      GOOGLE_REFRESH_TOKEN: tokens.refresh_token
    });
  } catch (e: any) {
    res.status(500).json({ error: e.message });
  }
});

app.post('/api/parse', upload.single('file'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'File is required' });
  
  try {
    const content = await FileService.parseFile(req.file.buffer, req.file.mimetype);
    
    if (!content || content.trim().length === 0) {
      return res.status(400).json({ error: 'File content is empty' });
    }

    res.json({ content, fileName: req.file.originalname });
  } catch (error: any) {
    console.error('File Parse API Error:', error);
    res.status(500).json({ error: error.message || 'File parsing failed' });
  }
});

export const startWebServer = async () => {
  // Start HTTPS server for microphone access (getUserMedia requires secure context)
  const certPath = process.env.SSL_CERT_PATH || '';
  const keyPath = process.env.SSL_KEY_PATH || '';

  if (certPath && keyPath && fs.existsSync(certPath) && fs.existsSync(keyPath)) {
    const cert = fs.readFileSync(certPath);
    const key = fs.readFileSync(keyPath);
    https.createServer({ cert, key }, app).listen(port, () => {
      console.log(`Web server listening at https://localhost:${port}`);
    });
  } else {
    // Try self-signed cert for development
    try {
      const { getSelfSignedCert } = await import('../services/SslService.js');
      const ssl = getSelfSignedCert();
      if (ssl) {
        https.createServer({ cert: ssl.cert, key: ssl.key }, app).listen(port, () => {
          console.log(`Web server listening at https://localhost:${port} (self-signed cert)`);
        });
      } else {
        app.listen(port, () => {
          console.log(`Web server listening at http://localhost:${port} (HTTP - microphone requires HTTPS or localhost)`);
        });
      }
    } catch {
      app.listen(port, () => {
        console.log(`Web server listening at http://localhost:${port} (HTTP - microphone requires HTTPS or localhost)`);
      });
    }
  }
};
