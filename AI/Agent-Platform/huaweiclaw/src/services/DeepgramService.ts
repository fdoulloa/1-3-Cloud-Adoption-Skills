import { createClient } from '@deepgram/sdk';
import dotenv from 'dotenv';
import fs from 'fs';

dotenv.config();

const key = process.env.DEEPGRAM_API_KEY || '';
if (key) {
  console.log(`DeepgramService: Initializing with key length: ${key.length}`);
} else {
  console.warn('DeepgramService: DEEPGRAM_API_KEY is missing or empty.');
}
const deepgram = createClient(key);

export class DeepgramService {
  static async stt(audioBuffer: Buffer, mimetype: string = 'audio/wav'): Promise<string> {
    try {
      const { result, error } = await deepgram.listen.prerecorded.transcribeFile(
        audioBuffer as any,
        {
          model: process.env.DEEPGRAM_STT_MODEL || 'nova-2',
          smart_format: true,
          language: 'es'
        }
      );

      if (error) throw error;
      return result.results.channels[0].alternatives[0].transcript;
    } catch (error) {
      console.error('STT Error:', error);
      return '';
    }
  }

  static async tts(text: string): Promise<Buffer> {
    const MAX_LENGTH = 1500; // Deepgram limit is 2000, 1500 is safer
    
    // Sanitize for a purely conversational experience
    const sanitizedText = this.sanitizeForTTS(text);
    
    // Split into chunks if necessary
    const chunks = this.splitTextIntoChunks(sanitizedText, MAX_LENGTH);
    
    if (chunks.length > 1) {
      console.log(`DeepgramService: Text is too long (${sanitizedText.length} chars sanitized). Splitting into ${chunks.length} chunks.`);
    }

    const audioBuffers: Buffer[] = [];
    
    for (let i = 0; i < chunks.length; i++) {
      const chunk = chunks[i];
      try {
        console.log(`DeepgramService: Sending chunk ${i + 1}/${chunks.length} (length: ${chunk.length} chars)...`);
        const response = await deepgram.speak.request(
          { text: chunk },
          { model: process.env.DEEPGRAM_TTS_MODEL || 'aura-asteria-es' }
        );

        const stream = await response.getStream();
        if (!stream) throw new Error('Failed to get TTS stream');

        const reader = stream.getReader();
        const chunkBuffers: Uint8Array[] = [];
        
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          chunkBuffers.push(value);
        }
        audioBuffers.push(Buffer.concat(chunkBuffers));
      } catch (error: any) {
        console.error('TTS Chunk Error:', error.message);
        // Continue with other chunks if possible
      }
    }

    if (audioBuffers.length === 0) throw new Error('Failed to generate any TTS audio.');
    return Buffer.concat(audioBuffers);
  }

  private static sanitizeForTTS(text: string): string {
    return text
      .replace(/\[.*?\]/g, '') // Remove [AGENT] tags
      .replace(/\*\*/g, '') // Remove bold markdown
      .replace(/\*/g, '') // Remove italic markdown
      .replace(/__/g, '') // Remove alternative bold
      .replace(/_/g, '') // Remove alternative italic
      .replace(/#[#]*/g, '') // Remove headers
      .replace(/[`>+\-\|]/g, '') // Remove miscellaneous markdown and pipe
      .replace(/[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E6}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}]/gu, '') // Basic Emoji removal
      .replace(/[✅⚠️🚀📊🤖🎯✨🔥🛠️💡📝🌐🔎📱💻📂📁📅🕒📧💬]/gu, '') // Explicit extra symbols
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();
  }

  private static splitTextIntoChunks(text: string, maxLength: number): string[] {
    const chunks: string[] = [];
    let current = text;
    
    while (current.length > maxLength) {
      // Try to find a good breaking point
      let cutAt = current.lastIndexOf('. ', maxLength);
      if (cutAt === -1) cutAt = current.lastIndexOf('\n', maxLength);
      if (cutAt === -1) cutAt = current.lastIndexOf(' ', maxLength);
      if (cutAt === -1) cutAt = maxLength;
      
      chunks.push(current.substring(0, cutAt + 1).trim());
      current = current.substring(cutAt + 1).trim();
    }
    
    if (current.length > 0) chunks.push(current);
    return chunks;
  }
}
