import axios from 'axios';
import dotenv from 'dotenv';
import { orchestrator } from '../core/Orchestrator.js';
import { app } from './WebServer.js';

dotenv.config();

const WHATSAPP_TOKEN = process.env.WHATSAPP_TOKEN || '';
const WHATSAPP_PHONE_NUMBER_ID = process.env.WHATSAPP_PHONE_NUMBER_ID || '';
const WHATSAPP_VERIFY_TOKEN = process.env.WHATSAPP_VERIFY_TOKEN || 'huaweiclaw_verify';
const WHATSAPP_ALLOWED_NUMBERS = (process.env.WHATSAPP_ALLOWED_NUMBERS || '').split(',').filter(Boolean);

const GRAPH_API = 'https://graph.facebook.com/v21.0';

/**
 * Send an image message via WhatsApp Business Cloud API using a media upload.
 */
async function sendWhatsAppImage(to: string, pngBuffer: Buffer, caption?: string): Promise<void> {
  if (!WHATSAPP_TOKEN || !WHATSAPP_PHONE_NUMBER_ID) return;

  try {
    // Upload media to WhatsApp using multipart form
    const boundary = '----FormBoundary' + Math.random().toString(36).substr(2);
    const header = Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n\r\nwhatsapp\r\n` +
      `--${boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\nimage/png\r\n` +
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="chart.png"\r\nContent-Type: image/png\r\n\r\n`
    );
    const footer = Buffer.from(`\r\n--${boundary}--\r\n`);
    const body = Buffer.concat([header, pngBuffer, footer]);

    const uploadRes = await axios.post(
      `${GRAPH_API}/${WHATSAPP_PHONE_NUMBER_ID}/media`,
      body,
      { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` }, timeout: 30_000 }
    );
    const mediaId = uploadRes.data.id;

    // Send image message
    await axios.post(
      `${GRAPH_API}/${WHATSAPP_PHONE_NUMBER_ID}/messages`,
      {
        messaging_product: 'whatsapp',
        recipient_type: 'individual',
        to,
        type: 'image',
        image: { id: mediaId, caption: (caption || '').substring(0, 1024) }
      },
      { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` }, timeout: 10_000 }
    );
  } catch (error: any) {
    console.error('[WhatsApp] Image send error:', error.response?.data || error.message);
  }
}

/**
 * Send an audio message via WhatsApp Business Cloud API.
 */
async function sendWhatsAppAudio(to: string, audioBuffer: Buffer, mimetype: string = 'audio/mpeg'): Promise<void> {
  if (!WHATSAPP_TOKEN || !WHATSAPP_PHONE_NUMBER_ID) return;

  try {
    const boundary = '----FormBoundary' + Math.random().toString(36).substr(2);
    const header = Buffer.from(
      `--${boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n\r\nwhatsapp\r\n` +
      `--${boundary}\r\nContent-Disposition: form-data; name="type"\r\n\r\n${mimetype}\r\n` +
      `--${boundary}\r\nContent-Disposition: form-data; name="file"; filename="voice.mp3"\r\nContent-Type: ${mimetype}\r\n\r\n`
    );
    const footer = Buffer.from(`\r\n--${boundary}--\r\n`);
    const body = Buffer.concat([header, audioBuffer, footer]);

    const uploadRes = await axios.post(
      `${GRAPH_API}/${WHATSAPP_PHONE_NUMBER_ID}/media`,
      body,
      { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}`, 'Content-Type': `multipart/form-data; boundary=${boundary}` }, timeout: 30_000 }
    );
    const mediaId = uploadRes.data.id;

    await axios.post(
      `${GRAPH_API}/${WHATSAPP_PHONE_NUMBER_ID}/messages`,
      {
        messaging_product: 'whatsapp',
        recipient_type: 'individual',
        to,
        type: 'audio',
        audio: { id: mediaId }
      },
      { headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` }, timeout: 10_000 }
    );
  } catch (error: any) {
    console.error('[WhatsApp] Audio send error:', error.response?.data || error.message);
  }
}

/**
 * Send a text message via WhatsApp Business Cloud API.
 */
async function sendWhatsAppMessage(to: string, text: string): Promise<void> {
  if (!WHATSAPP_TOKEN || !WHATSAPP_PHONE_NUMBER_ID) {
    console.warn('[WhatsApp] Not configured. Set WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID.');
    return;
  }

  // WhatsApp message limit is 4096 chars
  const chunks: string[] = [];
  if (text.length <= 4096) {
    chunks.push(text);
  } else {
    let remaining = text;
    while (remaining.length > 0) {
      let cutAt = remaining.lastIndexOf('\n', 4096);
      if (cutAt === -1) cutAt = remaining.lastIndexOf('. ', 4096);
      if (cutAt === -1) cutAt = 4096;
      chunks.push(remaining.substring(0, cutAt + 1));
      remaining = remaining.substring(cutAt + 1);
    }
  }

  for (const chunk of chunks) {
    try {
      await axios.post(
        `${GRAPH_API}/${WHATSAPP_PHONE_NUMBER_ID}/messages`,
        {
          messaging_product: 'whatsapp',
          recipient_type: 'individual',
          to,
          type: 'text',
          text: { body: chunk.replace(/\*\*/g, '*').replace(/<\/?[^>]+>/g, '') }
        },
        {
          headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` },
          timeout: 10_000
        }
      );
    } catch (error: any) {
      console.error('[WhatsApp] Send error:', error.response?.data || error.message);
    }
  }
}

/**
 * Setup WhatsApp webhook endpoints on the existing Express app.
 */
export function setupWhatsAppWebhook(): void {
  // GET endpoint for webhook verification
  app.get('/webhook/whatsapp', (req, res) => {
    const mode = req.query['hub.mode'];
    const token = req.query['hub.verify_token'];
    const challenge = req.query['hub.challenge'];

    if (mode === 'subscribe' && token === WHATSAPP_VERIFY_TOKEN) {
      console.log('[WhatsApp] Webhook verified');
      res.status(200).send(challenge);
    } else {
      res.sendStatus(403);
    }
  });

  // POST endpoint for incoming messages
  app.post('/webhook/whatsapp', async (req, res) => {
    // Always acknowledge quickly
    res.sendStatus(200);

    try {
      const body = req.body;
      if (body.object !== 'whatsapp_business_account') return;

      for (const entry of body.entry || []) {
        for (const change of entry.changes || []) {
          const value = change.value;
          const messages = value.messages || [];

          for (const msg of messages) {
            const from = msg.from; // Phone number
            const type = msg.type;

            // Whitelist check
            if (WHATSAPP_ALLOWED_NUMBERS.length > 0 && !WHATSAPP_ALLOWED_NUMBERS.includes(from)) {
              console.warn(`[WhatsApp] Unauthorized number: ${from}`);
              continue;
            }

            const sessionId = `wa-${from}`;

            if (type === 'text') {
              const text = msg.text?.body || '';
              console.log(`[WhatsApp] Text from ${from}: "${text.substring(0, 50)}..."`);

              // Immediate feedback
              await sendWhatsAppMessage(from, '⏳ Procesando...');

              const response = await orchestrator.processRequest(sessionId, text);

              // Send chart as image if PNG is available
              const pngMatch = response.match(/!\[chart\]\(data:image\/png;base64,([^\)]+)\)/);
              const echartsMatch = response.includes('data:image/echarts;');
              const textWithoutChart = response.replace(/!\[.*?\]\(data:image\/(png|echarts);base64,[^\)]+\)/g, '').trim();

              if (pngMatch) {
                const pngBuffer = Buffer.from(pngMatch[1], 'base64');
                await sendWhatsAppImage(from, pngBuffer, textWithoutChart.substring(0, 1024));
                if (textWithoutChart.length > 1024) {
                  await sendWhatsAppMessage(from, textWithoutChart);
                }
              } else if (echartsMatch) {
                // ECharts JSON — try to send PNG from session state
                const { memory } = await import('../core/Memory.js');
                const sessionState = await memory.getSessionState(sessionId);
                const chartPath = sessionState?.lastChartPath;
                if (chartPath) {
                  const fs = await import('fs');
                  if (fs.default.existsSync(chartPath)) {
                    const pngBuffer = fs.default.readFileSync(chartPath);
                    await sendWhatsAppImage(from, pngBuffer, textWithoutChart.substring(0, 1024));
                  } else {
                    await sendWhatsAppMessage(from, textWithoutChart + '\n[Gráfico generado. Visita la Plataforma Web para visualización interactiva.]');
                  }
                } else {
                  await sendWhatsAppMessage(from, textWithoutChart + '\n[Gráfico generado. Visita la Plataforma Web para visualización interactiva.]');
                }
              } else {
                await sendWhatsAppMessage(from, response);
              }

              // Auto-TTS: send voice response alongside text
              try {
                const { DeepgramService } = await import('../services/DeepgramService.js');
                const ttsBuffer = await DeepgramService.tts(response.replace(/!\[.*?\]\(data:image\/[^\)]+\)/g, ''));
                await sendWhatsAppAudio(from, ttsBuffer);
              } catch (e: any) {
                // TTS is optional, don't block on failure
                console.warn('[WhatsApp] TTS failed:', e.message);
              }

            } else if (type === 'audio' || type === 'voice') {
              // Download and transcribe voice message
              const mediaId = msg.audio?.id || msg.voice?.id;
              if (mediaId) {
                try {
                  // Get media URL
                  const mediaRes = await axios.get(`${GRAPH_API}/${mediaId}`, {
                    headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` }
                  });
                  const mediaUrl = mediaRes.data.url;

                  // Download audio
                  const audioRes = await axios.get(mediaUrl, {
                    headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` },
                    responseType: 'arraybuffer'
                  });
                  const audioBuffer = Buffer.from(audioRes.data);

                  // Transcribe
                  const { DeepgramService } = await import('../services/DeepgramService.js');
                  const transcript = await DeepgramService.stt(audioBuffer, 'audio/ogg');

                  if (transcript) {
                    const response = await orchestrator.processRequest(sessionId, transcript);
                    await sendWhatsAppMessage(from, response);
                  } else {
                    await sendWhatsAppMessage(from, 'No pude entender el audio.');
                  }
                } catch (e: any) {
                  console.error('[WhatsApp] Voice processing error:', e.message);
                  await sendWhatsAppMessage(from, 'Error procesando el audio.');
                }
              }

            } else if (type === 'document') {
              // Download and parse document
              const mediaId = msg.document?.id;
              const filename = msg.document?.filename || 'document';
              const caption = msg.document?.caption || '';

              if (mediaId) {
                try {
                  const mediaRes = await axios.get(`${GRAPH_API}/${mediaId}`, {
                    headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` }
                  });
                  const audioRes = await axios.get(mediaRes.data.url, {
                    headers: { Authorization: `Bearer ${WHATSAPP_TOKEN}` },
                    responseType: 'arraybuffer'
                  });
                  const buffer = Buffer.from(audioRes.data);

                  const { FileService } = await import('../services/FileService.js');
                  const mimetype = msg.document?.mime_type || 'application/pdf';
                  const content = await FileService.parseFile(buffer, mimetype);

                  const prompt = caption
                    ? `[Archivo: ${filename}]\nContenido:\n${content}\n\nInstrucción: ${caption}`
                    : content;
                  const response = await orchestrator.processRequest(sessionId, prompt);
                  await sendWhatsAppMessage(from, response);
                } catch (e: any) {
                  console.error('[WhatsApp] Document error:', e.message);
                  await sendWhatsAppMessage(from, 'Error procesando el documento.');
                }
              }
            }
          }
        }
      }
    } catch (error: any) {
      console.error('[WhatsApp] Webhook processing error:', error.message);
    }
  });

  console.log('[WhatsApp] Webhook endpoints registered at /webhook/whatsapp');
}

export const sendWhatsApp = sendWhatsAppMessage;
