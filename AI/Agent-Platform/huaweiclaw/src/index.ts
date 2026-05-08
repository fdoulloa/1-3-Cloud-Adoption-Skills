import dotenv from 'dotenv';
dotenv.config();

import { registry } from './core/Registry.js';
import { memory } from './core/Memory.js';
import { startTelegramBot } from './interfaces/TelegramBot.js';
import { startWebServer } from './interfaces/WebServer.js';
import { setupWhatsAppWebhook } from './interfaces/WhatsAppBot.js';
import { SandboxService } from './services/SandboxService.js';

// Import Agents
import { HuaweiCloudAgent } from './agents/HuaweiCloudAgent.js';
import { CodeAgent } from './agents/CodeAgent.js';
import { KnowledgeAgent, DataAgent, CommunicationAgent, BusinessAgent, OrchestratorAgent } from './agents/MiscellaneousAgents.js';

// Global error handlers to prevent silent crashes
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

async function main() {
  console.log('--- Starting HuaweiClaw System ---');

  // 1. Connect to Memory (Database)
  await memory.connect();

  // 2. Pre-pull Docker sandbox image (async, non-blocking)
  SandboxService.pullImage().catch(e =>
    console.warn('[Sandbox] Docker image pull skipped:', e.message)
  );

  // 3. Instantiate and Register ALL 7 Agents
  const huaweiAgent = new HuaweiCloudAgent();
  await huaweiAgent.initialize();

  registry.register(new OrchestratorAgent());
  registry.register(huaweiAgent);
  registry.register(new CodeAgent());
  registry.register(new KnowledgeAgent());
  registry.register(new DataAgent());
  registry.register(new CommunicationAgent());
  registry.register(new BusinessAgent());

  console.log(`Registered ${registry.getAllAgents().length} agents: ${registry.getAllAgents().map(a => a.role).join(', ')}`);

  // 4. Start Interfaces
  startTelegramBot();
  startWebServer();

  // 5. Setup WhatsApp webhook (if configured)
  if (process.env.WHATSAPP_TOKEN) {
    setupWhatsAppWebhook();
  }

  console.log('--- HuaweiClaw is now active ---');
}

main().catch(err => {
  console.error('Failed to start system:', err);
});
