import axios from 'axios';
import { EmbeddingService } from './EmbeddingService.js';
import dotenv from 'dotenv';

dotenv.config();

export class OllamaEmbeddingService implements EmbeddingService {
  private baseUrl = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
  private model = process.env.OLLAMA_EMBED_MODEL || 'bge-m3';

  async getEmbeddings(text: string): Promise<number[]> {
    try {
      const response = await axios.post(`${this.baseUrl}/api/embeddings`, {
        model: this.model,
        prompt: text
      });

      if (response.data && response.data.embedding) {
        return response.data.embedding;
      }
      throw new Error('No embedding returned from Ollama');
    } catch (error: any) {
      console.error('Ollama Embedding Error:', error.message);
      throw new Error(`Failed to get embeddings from Ollama: ${error.message}`);
    }
  }
}
