import weaviate, { WeaviateClient } from 'weaviate-client';
import { VectorStore, VectorDocument } from '../core/VectorStore.js';
import { EmbeddingService } from './EmbeddingService.js';
import dotenv from 'dotenv';

dotenv.config();

export class WeaviateService implements VectorStore {
  private static sharedClient: WeaviateClient | null = null;
  private static initPromise: Promise<void> | null = null;
  private className = 'Knowledge';

  constructor(private embeddingService: EmbeddingService) {}

  async initialize() {
    if (!WeaviateService.initPromise) {
      WeaviateService.initPromise = this._initialize();
    }
    await WeaviateService.initPromise;
  }

  private async _initialize() {
    try {
      const urlStr = process.env.WEAVIATE_URL || 'http://localhost:8080';
      const parsed = new URL(urlStr);

      const apiKey = process.env.WEAVIATE_API_KEY;

      WeaviateService.sharedClient = await weaviate.connectToCustom({
        httpHost: parsed.hostname,
        httpPort: parseInt(parsed.port) || 8080,
        httpSecure: parsed.protocol === 'https:',
        grpcHost: parsed.hostname,
        grpcPort: 50051,
        grpcSecure: false,
        authCredentials: apiKey
          ? new weaviate.ApiKey(apiKey)
          : undefined,
      });

      const collections = await WeaviateService.sharedClient.collections.listAll();
      const exists = collections.some(c => c.name === this.className);

      if (!exists) {
        await WeaviateService.sharedClient.collections.create({
          name: this.className,
          vectorizers: weaviate.configure.vectorizer.none(),
          properties: [
            { name: 'text', dataType: 'text' },
            { name: 'metadata', dataType: 'text' }
          ]
        });
        console.log(`Weaviate collection '${this.className}' created.`);
      }
    } catch (error: any) {
      console.error('Weaviate Initialization Error:', error.message);
      WeaviateService.initPromise = null;
    }
  }

  async addDocument(doc: VectorDocument): Promise<void> {
    const client = WeaviateService.sharedClient;
    if (!client) throw new Error('Weaviate client not initialized');

    const vector = doc.vector || await this.embeddingService.getEmbeddings(doc.text);
    const collection = client.collections.get<any>(this.className);
    await (collection.data as any).insert({
      properties: {
        text: doc.text,
        metadata: JSON.stringify(doc.metadata || {})
      },
      vectors: vector
    });
  }

  async search(query: string, limit: number = 3): Promise<VectorDocument[]> {
    const client = WeaviateService.sharedClient;
    if (!client) return [];

    try {
      const vector = await this.embeddingService.getEmbeddings(query);
      const collection = client.collections.get(this.className);

      const result = await collection.query.nearVector(vector, {
        limit: limit,
        returnProperties: ['text', 'metadata']
      });

      return result.objects.map(obj => ({
        text: obj.properties.text as string,
        metadata: JSON.parse((obj.properties.metadata as string) || '{}')
      }));
    } catch (error: any) {
      console.error('Weaviate Search Error:', error.message);
      return [];
    }
  }
}
