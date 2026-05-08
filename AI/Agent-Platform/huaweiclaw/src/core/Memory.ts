import { MongoClient, Db } from 'mongodb';
import dotenv from 'dotenv';

dotenv.config();

const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/huaweiclaw';

export class Memory {
  private client: MongoClient;
  private db?: Db;

  constructor() {
    this.client = new MongoClient(uri);
  }

  async connect() {
    const maxRetries = 3;
    const retryDelay = 2000;
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        console.log(`Connecting to MongoDB at ${uri.replace(/:([^:@]+)@/, ':****@')}... (attempt ${attempt}/${maxRetries})`);
        await this.client.connect();
        this.db = this.client.db();
        console.log('Successfully connected to MongoDB.');
        return;
      } catch (error: any) {
        console.error(`MongoDB connection attempt ${attempt} failed: ${error.message}`);
        if (attempt < maxRetries) {
          await new Promise(r => setTimeout(r, retryDelay));
        } else {
          console.error('CRITICAL: MongoDB connection failed after all retries. Running without persistent memory.');
        }
      }
    }
  }

  getDb(): Db {
    if (!this.db) throw new Error('Database not connected. Call connect() first.');
    return this.db;
  }

  async storeMessage(sessionId: string, sender: string, content: string) {
    if (!this.db) return;
    await this.db.collection('messages').insertOne({
      sessionId,
      sender,
      content,
      timestamp: new Date()
    });
  }

  async getHistory(sessionId: string, limit: number = 20) {
    if (!this.db) return [];
    return await this.db.collection('messages')
      .find({ sessionId })
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();
  }

  async clearHistory(sessionId: string) {
    if (!this.db) return;
    await this.db.collection('messages').deleteMany({ sessionId });
    await this.db.collection('session_states').deleteOne({ sessionId });
    console.log(`Memory cleared for session ${sessionId}`);
  }

  async storeAgentMemory(agentId: string, key: string, value: any) {
    if (!this.db) return;
    await this.db.collection('agent_memories').updateOne(
      { agentId, key },
      { $set: { value, updatedAt: new Date() } },
      { upsert: true }
    );
  }

  async getAgentMemory(agentId: string, key: string) {
    if (!this.db) return null;
    const result = await this.db.collection('agent_memories').findOne({ agentId, key });
    return result ? result.value : null;
  }

  async setSessionState(sessionId: string, state: any) {
    if (!this.db) return;
    await this.db.collection('session_states').updateOne(
      { sessionId },
      { $set: { state, updatedAt: new Date() } },
      { upsert: true }
    );
  }

  async getSessionState(sessionId: string) {
    if (!this.db) return null;
    const result = await this.db.collection('session_states').findOne({ sessionId });
    return result ? result.state : null;
  }

  async clearSessionState(sessionId: string) {
    if (!this.db) return;
    await this.db.collection('session_states').deleteOne({ sessionId });
  }
}

export const memory = new Memory();
