import { MongoClient } from 'mongodb';
import weaviate from 'weaviate-client';
import dotenv from 'dotenv';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

dotenv.config();

async function wipe() {
  console.log("--- STARTING TOTAL DATA WIPE ---");

  // 1. MongoDB
  const mongoUri = process.env.MONGODB_URI || 'mongodb://localhost:27017/huaweiclaw';
  const mongoClient = new MongoClient(mongoUri);
  try {
    await mongoClient.connect();
    const db = mongoClient.db();
    const dbName = db.databaseName;
    console.log(`Wiping MongoDB database: ${dbName}...`);
    
    // Drop all collections in the DB
    const collections = await db.listCollections().toArray();
    for (const col of collections) {
      console.log(`Dropping MongoDB collection: ${col.name}`);
      await db.collection(col.name).drop();
    }
    
    console.log("✔ MongoDB wiped (collections dropped).");
  } catch (e) {
    console.error("✘ MongoDB wipe failed:", e.message);
  } finally {
    await mongoClient.close();
  }

  // 2. Weaviate
  if (process.env.VECTOR_STORE_TYPE === 'WEAVIATE') {
    const weaviateUrl = process.env.WEAVIATE_URL || 'http://localhost:8080';
    try {
      console.log(`Connecting to Weaviate at ${weaviateUrl}...`);
      // V3 client connection style
      const client = await weaviate.connectToLocal();
      const collections = await client.collections.listAll();
      for (const colName of Object.keys(collections)) {
         console.log(`Deleting Weaviate collection: ${colName}...`);
         await client.collections.delete(colName);
      }
      console.log("✔ Weaviate wiped.");
    } catch (e) {
      console.warn("✘ Weaviate wipe might have skipped (V3 client needs active connection):", e.message);
    }
  }

  console.log("--- WIPE COMPLETE ---");
  process.exit(0);
}

wipe();
