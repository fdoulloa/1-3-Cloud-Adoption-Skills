import { EmbeddingService } from '../services/EmbeddingService.js';

export interface VectorDocument {
  id?: string;
  text: string;
  metadata?: Record<string, any>;
  vector?: number[];
}

export interface VectorStore {
  addDocument(doc: VectorDocument): Promise<void>;
  search(query: string, limit?: number): Promise<VectorDocument[]>;
  initialize(): Promise<void>;
}

export class VectorStoreFactory {
  static async create(type: string, embeddingService: EmbeddingService): Promise<VectorStore> {
    if (type === 'WEVIATE' || type === 'WEAVIATE') {
      const { WeaviateService } = await import('../services/WeaviateService.js');
      const service = new WeaviateService(embeddingService);
      await service.initialize();
      return service;
    }
    throw new Error(`Unsupported Vector Store type: ${type}`);
  }
}
