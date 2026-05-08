import { Bot, Context, InputFile } from 'grammy';
import dotenv from 'dotenv';
import fs from 'fs';
import { orchestrator } from '../core/Orchestrator.js';
import { DeepgramService } from '../services/DeepgramService.js';
import { FileService } from '../services/FileService.js';
import axios from 'axios';

dotenv.config();

const botToken = process.env.TELEGRAM_BOT_TOKEN || '';
const whitelist = (process.env.TELEGRAM_ALLOWED_USER_IDS || '').split(',');

// Escape text for Telegram HTML parse_mode (only <b>, <i>, <u>, <s>, <code>, <pre>, <a> are allowed)
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Re-enable allowed tags that we intentionally use
    .replace(/&lt;(\/?)(b|i|u|s|code|pre|a)(\s[^&]*?)?&gt;/gi, '<$1$2$3>');
}

async function safeReply(ctx: Context, text: string, extra: any = {}) {
  try {
    await ctx.reply(text, { ...extra, parse_mode: 'HTML' });
  } catch {
    // HTML parse failed — send without parse_mode
    try {
      await ctx.reply(text, {});
    } catch (e2: any) {
      console.error('[Telegram] Reply failed completely:', e2.message);
    }
  }
}

export const telegramBot = new Bot(botToken);

// Middleware for whitelist
telegramBot.use(async (ctx, next) => {
  const userId = ctx.from?.id.toString();
  if (userId && whitelist.includes(userId)) {
    await next();
  } else {
    console.warn(`Unauthorized access attempt from ID: ${userId}`);
    // await ctx.reply('No tienes permiso para usar este bot.');
  }
});

// Handle text messages
telegramBot.on('message:text', async (ctx) => {
  const sessionId = ctx.from.id.toString();
  let text = ctx.message.text;
  console.log(`[Telegram] Received text from ${ctx.from.username || ctx.from.id}: "${text}"`);

  // Immediate feedback — show the bot is working
  const statusMsg = await ctx.reply('⏳ Procesando...');

  // Check for pending file attachment
  const state = await orchestrator.getPendingFile(sessionId);
  if (state) {
    console.log(`[Telegram] Processing text with pending file: ${state.fileName}`);
    text = `[Archivo adjunto: ${state.fileName}]\nContenido:\n${state.content}\n\nInstrucción: ${text}`;
    await orchestrator.clearPendingFile(sessionId);
  }

  const response = await orchestrator.processRequest(sessionId, text);

  // Delete the "processing" status message
  try { await ctx.api.deleteMessage(ctx.chat.id, statusMsg.message_id); } catch { /* ok if already gone */ }
  
  // Bold the [CODE] part
  let formatted = response.replace(/^\[(.*?)\]/, '<b>[$1]</b>');

  // Strip LLM "Thought:" / "Data:" prefixes that leak into output
  formatted = formatted.replace(/^(?:\[data\]\s*)?Thought:\s*/i, '');

  // Send chart images as photos instead of text
  const pngMatch = formatted.match(/!\[.*?\]\(data:image\/png;base64,([^\)]+)\)/);
  const echartsMatch = formatted.includes('data:image/echarts;');
  const textWithoutChart = formatted.replace(/!\[.*?\]\(data:image\/(png|echarts);base64,[^\)]+\)/g, '').trim();

  if (pngMatch) {
    const pngBuffer = Buffer.from(pngMatch[1], 'base64');
    try {
      const caption = escapeHtml(textWithoutChart.substring(0, 1024) || 'Gráfico');
      await ctx.replyWithPhoto(new InputFile(pngBuffer, 'chart.png'), { caption, parse_mode: 'HTML' });
    } catch {
      await safeReply(ctx, textWithoutChart || 'Gráfico generado');
    }
  } else if (echartsMatch) {
    // ECharts JSON — try to send PNG from session state instead of placeholder text
    const { memory } = await import('../core/Memory.js');
    const sessionState = await memory.getSessionState(sessionId);
    const chartPath = sessionState?.lastChartPath;
    if (chartPath && fs.existsSync(chartPath)) {
      try {
        const caption = escapeHtml(textWithoutChart.substring(0, 1024) || 'Gráfico');
        await ctx.replyWithPhoto(new InputFile(chartPath), { caption, parse_mode: 'HTML' });
      } catch {
        await safeReply(ctx, textWithoutChart || 'Gráfico generado');
      }
    } else {
      formatted = textWithoutChart + '\n<i>[Gráfico generado. Visita la Plataforma Web para visualización interactiva.]</i>';
      await safeReply(ctx, escapeHtml(formatted));
    }
  } else {
    await safeReply(ctx, escapeHtml(formatted));
  }
});

// Handle voice messages
telegramBot.on('message:voice', async (ctx) => {
  const sessionId = ctx.from.id.toString();
  
  try {
    console.log(`[Telegram] Processing voice from session ${sessionId}...`);
    await ctx.reply('Procesando audio...');
    
    const file = await ctx.getFile();
    const url = `https://api.telegram.org/file/bot${botToken}/${file.file_path}`;
    
    console.log(`[Telegram] Downloading file: ${file.file_path}`);
    const responseAudio = await axios.get(url, { responseType: 'arraybuffer' });
    const audioBuffer = Buffer.from(responseAudio.data);
    
    console.log(`[Telegram] Sending to Deepgram STT (mimetype: audio/ogg)...`);
    const transcript = await DeepgramService.stt(audioBuffer, 'audio/ogg');
    
    if (!transcript) {
      console.warn(`[Telegram] Failed to transcribe audio from session ${sessionId}`);
      return await ctx.reply('No pude entender el audio o el servicio de transcripción falló.');
    }
    
    console.log(`[Telegram] Transcription successful: "${transcript}"`);
    await ctx.reply(`Dijiste: "${transcript}"\nGenerando respuesta...`);
    
    console.log(`[Telegram] Processing via Orchestrator...`);
    const responseText = await orchestrator.processRequest(sessionId, transcript);

    // Strip LLM prefixes
    let formatted = responseText.replace(/^\[(.*?)\]/, '<b>[$1]</b>');
    formatted = formatted.replace(/^(?:\[data\]\s*)?Thought:\s*/i, '');

    // Handle chart images — send as photo, not as text with base64
    const pngMatch = responseText.match(/!\[.*?\]\(data:image\/png;base64,([^\)]+)\)/);
    const echartsMatch = responseText.includes('data:image/echarts;');
    const textWithoutChart = responseText.replace(/!\[.*?\]\(data:image\/(png|echarts);base64,[^\)]+\)/g, '').trim();
    const cleanFormatted = textWithoutChart.replace(/^\[(.*?)\]/, '<b>[$1]</b>');

    if (pngMatch) {
      const pngBuffer = Buffer.from(pngMatch[1], 'base64');
      try {
        const caption = escapeHtml(cleanFormatted.substring(0, 1024) || 'Gráfico');
        await ctx.replyWithPhoto(new InputFile(pngBuffer, 'chart.png'), { caption, parse_mode: 'HTML' });
      } catch {
        await safeReply(ctx, cleanFormatted || 'Gráfico generado');
      }
      // TTS for the analysis text (not the image)
      if (textWithoutChart.trim()) {
        try {
          const ttsBuffer = await DeepgramService.tts(textWithoutChart);
          await ctx.replyWithVoice(new InputFile(ttsBuffer));
        } catch { /* TTS optional */ }
      }
    } else if (echartsMatch) {
      // ECharts JSON — send PNG from session state
      const { memory } = await import('../core/Memory.js');
      const sessionState = await memory.getSessionState(sessionId);
      const chartPath = sessionState?.lastChartPath;
      if (chartPath && fs.existsSync(chartPath)) {
        try {
          const caption = escapeHtml(cleanFormatted.substring(0, 1024) || 'Gráfico');
          await ctx.replyWithPhoto(new InputFile(chartPath), { caption, parse_mode: 'HTML' });
        } catch {
          await safeReply(ctx, cleanFormatted || 'Gráfico generado');
        }
      } else {
        await safeReply(ctx, escapeHtml(cleanFormatted + '\n<i>[Gráfico generado. Visita la Plataforma Web para visualización interactiva.]</i>'));
      }
      // TTS for the analysis text (not the image)
      if (textWithoutChart.trim()) {
        try {
          const ttsBuffer = await DeepgramService.tts(textWithoutChart);
          await ctx.replyWithVoice(new InputFile(ttsBuffer));
        } catch { /* TTS optional */ }
      }
    } else {
      // No chart — send text + TTS voice response
      console.log(`[Telegram] Generating TTS...`);
      try {
        const ttsBuffer = await DeepgramService.tts(responseText);
        if (formatted.length > 1024) {
          const truncatedCaption = responseText.substring(0, 500) + '...';
          await ctx.replyWithVoice(new InputFile(ttsBuffer), { caption: truncatedCaption, parse_mode: 'HTML' });
          await safeReply(ctx, escapeHtml(formatted));
        } else {
          await ctx.replyWithVoice(new InputFile(ttsBuffer), { caption: formatted, parse_mode: 'HTML' });
        }
      } catch {
        await safeReply(ctx, escapeHtml(formatted));
      }
    }
    console.log(`[Telegram] Voice processing complete for ${sessionId}`);
    
  } catch (error: any) {
    console.error('CRITICAL: Telegram Voice processing error:', error.message, error.stack);
    await ctx.reply('Lo siento, hubo un error procesando tu mensaje de voz. Por favor, intenta de nuevo o usa texto.');
  }
});

// Handle documents (PDF, Word, Excel)
telegramBot.on('message:document', async (ctx) => {
  const sessionId = ctx.from.id.toString();
  const document = ctx.message.document;
  
  if (!document) return;

  const validMimeTypes = [
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel'
  ];

  if (!validMimeTypes.includes(document.mime_type || '')) {
    return await ctx.reply('Lo siento, solo puedo procesar archivos PDF, Word o Excel.');
  }

  try {
    await ctx.reply(`Procesando archivo: ${document.file_name}...`);
    
    const file = await ctx.getFile();
    const url = `https://api.telegram.org/file/bot${botToken}/${file.file_path}`;
    
    const responseFile = await axios.get(url, { responseType: 'arraybuffer' });
    const buffer = Buffer.from(responseFile.data);
    
    const content = await FileService.parseFile(buffer, document.mime_type!);

    if (!content || content.trim().length === 0) {
      return await ctx.reply('El archivo parece estar vacío o no pude extraer texto de él.');
    }

    const caption = ctx.message.caption;
    const lowerCaption = (caption || '').toLowerCase();

    // Check if user wants to save to knowledge base - do it directly to avoid LLM truncation
    const knowledgeKeywords = ['base de conocimiento', 'knowledge base', 'guardar', 'subir', 'aprender', 'memorizar', 'save', 'store'];
    const isKnowledgeRequest = knowledgeKeywords.some(k => lowerCaption.includes(k));

    if (isKnowledgeRequest) {
      // Save directly to Weaviate, bypassing LLM to preserve full content
      try {
        const { VectorStoreFactory } = await import('../core/VectorStore.js');
        const { OllamaEmbeddingService } = await import('../services/OllamaEmbeddingService.js');

        const embeddingService = new OllamaEmbeddingService();
        const vectorStore = await VectorStoreFactory.create(process.env.VECTOR_STORE_TYPE || 'WEAVIATE', embeddingService);

        await vectorStore.addDocument({
          text: content,
          metadata: { fileName: document.file_name, source: 'telegram', date: new Date().toISOString() }
        });

        await ctx.reply(`✅ Documento guardado en la base de conocimiento.\n📊 Caracteres: ${content.length.toLocaleString()}\n📄 Archivo: ${document.file_name}`);
        return;
      } catch (error: any) {
        console.error('Error saving to knowledge base:', error);
        await ctx.reply(`❌ Error al guardar en la base de conocimiento: ${error.message}`);
        return;
      }
    }

    if (caption) {
      // Process immediately if there's a caption
      const prompt = `[Archivo adjunto: ${document.file_name}]\nContenido:\n${content}\n\nInstrucción: ${caption}`;
      const responseText = await orchestrator.processRequest(sessionId, prompt);
      const formatted = responseText.replace(/^\[(.*?)\]/, '<b>[$1]</b>');
      await safeReply(ctx, escapeHtml(formatted));
    } else {
      // Store and wait for instructions
      await orchestrator.setPendingFile(sessionId, { fileName: document.file_name || 'unknown', content });
      await ctx.reply(`📎 Archivo "${document.file_name}" recibido. ¿Qué te gustaría que haga con él?`);
    }

  } catch (error: any) {
    console.error('Error processing document:', error);
    await ctx.reply(`Hubo un error al procesar el archivo: ${error.message}`);
  }
});

export const startTelegramBot = () => {
  telegramBot.start();
  console.log('Telegram Bot started');
};
