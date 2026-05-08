# HuaweiClaw

Personal Multi-Agent AI System for Huawei Cloud infrastructure management, code execution, data analysis, and communication automation.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Interface Layer                       │
│   Telegram Bot  │  Web Cockpit (HTTPS)  │  WhatsApp     │
└────────┬────────┴──────────┬────────────┴───────────────┘
         │                   │
┌────────▼───────────────────▼────────────────────────────┐
│                     Core Layer                           │
│  Orchestrator → Registry → Agent (base)                 │
│  Memory (MongoDB)  │  Audit (Winston)  │  VectorStore   │
└────────┬──────────────────┬─────────────────────────────┘
         │                  │
┌────────▼──────────────────▼────────────────────────────┐
│                   Service Layer                          │
│  LLM │ MCP │ HuaweiCloud │ Deepgram │ Google │ Sandbox  │
└─────────────────────────────────────────────────────────┘
```

### Agents

| Agent | Role | Capabilities |
|-------|------|-------------|
| **Orchestrator** | `orchestrator` | Classifies tasks, routes to specialist agents, synthesizes responses |
| **Huawei Cloud** | `huaweicloud` | ECS, VPC, OBS, RDS, IAM, EVS management across 20+ regions via MCP |
| **Code** | `code` | Software engineering, code execution in Docker sandbox, Superpowers skills |
| **Knowledge** | `knowledge` | General knowledge, internet research, RAG over vector store |
| **Data** | `data` | SQL/NoSQL queries, data analysis, ECharts visualization, Zaturn BI |
| **Communication** | `communication` | Telegram messaging, Google Workspace (Gmail, Calendar, Drive) |
| **Business** | `business` | Process optimization, CRM, KPI tracking, workflow logic |

Each agent has its own LLM model, tool set, and system prompt. Agents communicate via an A2A (Agent-to-Agent) bus through the Registry.

### Huawei Cloud Integration

The Huawei Cloud agent connects to 6 MCP servers providing **775+ tools**:

| Service | MCP Server | Tools | Scope |
|---------|-----------|-------|-------|
| ECS | `mcp-server-ecs` | 104 | Elastic Cloud Servers |
| VPC | `mcp-server-vpc` | 182 | Virtual Private Cloud |
| IAM | `mcp-server-iam` | 145 | Identity & Access Management |
| OBS | `mcp-server-obs` | 77 | Object Storage Service |
| EVS | `mcp-server-evs` | 30 | Elastic Volume Service |
| RDS | `mcp-server-rds` | 232 | Relational Database Service |

**Global search tools** (`global_search_servers`, `global_search_rds`) query all regions in parallel via direct REST calls for fast cross-region discovery.

**Region auto-resolution**: The agent validates all available regions at startup, caches project IDs, and auto-injects `region_id` and `project_id` for MCP calls. Common region mappings:

| City | Region ID |
|------|-----------|
| Hong Kong | `ap-southeast-1` |
| Singapore | `ap-southeast-3` |
| Santiago | `la-south-2` |
| Mexico City | `la-north-2` |
| São Paulo | `sa-brazil-1` |

**Safety**: Destructive operations (start/stop/reboot/delete) require explicit user intent. The agent never takes mutating actions when the user only asks to list or view.

### MCP Servers

External MCP servers connected via JSON-RPC over stdio:

| Server | Purpose |
|--------|---------|
| `mcp-server-{ecs,vpc,iam,evs,obs,rds}` | Huawei Cloud service APIs |
| `mcp-echarts` | Apache ECharts chart rendering |
| `mcp-zaturn` | AI-powered SQL queries and BI |
| `mcp-superpowers` | Software engineering skills |
| `mcp-google` | Google Workspace CLI |

## Interfaces

### Web Cockpit

HTTPS web dashboard at `https://localhost:3001` with a dark-themed glass-morphism UI.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/chat` | POST | Chat with the system (supports SSE streaming) |
| `/api/health` | GET | Health check (agents, memory, uptime) |
| `/api/memory/clear` | POST | Clear session history |
| `/api/stt` | POST | Speech-to-text (audio upload) |
| `/api/tts` | POST | Text-to-speech |
| `/api/parse` | POST | File parsing (PDF, Word, Excel) |
| `/api/google/auth` | GET | Google OAuth2 redirect |
| `/api/google/callback` | GET | Google OAuth2 callback |

### Telegram Bot

Whitelist-secured bot supporting text, voice (STT/TTS via Deepgram), images, documents, and ECharts chart rendering.

### WhatsApp Bot

Webhook-based integration (configured via `WHATSAPP_TOKEN`).

## Services

| Service | Description |
|---------|-------------|
| **LLMService** | OpenAI-compatible chat API with 3-tier truncation (40k system, 30k message, 400k total) |
| **McpProcessService** | Spawns MCP server processes, manages JSON-RPC lifecycle and persistent sessions |
| **HuaweiCloudMcpManager** | Caches MCP tool definitions in SQLite, dispatches tool calls to MCP servers |
| **HuaweiCloudService** | Direct Huawei Cloud REST API with AKSK signing (parallel region queries) |
| **HuaweiSigner** | AKSK request signing — SDK-based for standard services, S3-compatible V2 for OBS |
| **Memory** | MongoDB-backed conversation history, agent memories, session states |
| **Audit** | Winston structured logging to console + `audit.log` |
| **SandboxService** | Docker-based Python code execution sandbox |
| **DeepgramService** | Speech-to-text (nova-2) and text-to-speech (aura-asteria-es) |
| **GoogleWorkspaceService** | Gmail, Calendar, Drive via googleapis SDK |
| **WeaviateService** | Vector store for RAG knowledge retrieval |
| **FileService** | Parse PDF, Word (.docx), Excel (.xlsx) files |
| **ObsStorageService** | Huawei OBS upload with S3-compatible pre-signed URLs |

## Getting Started

### Prerequisites

- Node.js 23+
- Python 3.10+ (for Huawei Cloud MCP servers)
- MongoDB
- Docker (for sandbox and Weaviate)
- Huawei Cloud account with AK/SK credentials

### Install

```bash
# Clone the repository
git clone <repo-url> huaweiclaw
cd huaweiclaw

# Install Node.js dependencies
npm install

# Install Huawei Cloud MCP servers
pip install huaweicloud-mcp-server

# Start Weaviate vector store
docker compose up -d

# Start MongoDB (if not already running)
mongod --dbpath /data/db
```

### Configure

Copy `.env.example` to `.env` and fill in your credentials:

```bash
# LLM API (OpenAI-compatible endpoint)
OPENAI_BASE_URL=https://api-ap-southeast-1.modelarts-maas.com/openai/v1
OPENAI_API_KEY=your-api-key

# Huawei Cloud credentials
HUAWEI_ACCESS_KEY=your-ak
HUAWEI_SECRET_KEY=your-sk

# Telegram bot
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_ALLOWED_USER_IDS=your-telegram-user-id

# MongoDB
MONGODB_URI=mongodb://localhost:27017/huaweiclaw

# MCP server Python source (for editable installs)
PYTHONPATH=/path/to/huaweicloud-mcp-server
```

### Run

```bash
# Development (with hot reload via tsx)
npm run dev

# Production
npm run build
npm start
```

The web cockpit is available at `https://localhost:3001`.

## Project Structure

```
huaweiclaw/
├── src/
│   ├── index.ts                  # Entry point — bootstraps all agents and interfaces
│   ├── agents/
│   │   ├── HuaweiCloudAgent.ts   # Huawei Cloud expert with MCP tool routing
│   │   ├── CodeAgent.ts          # Software engineer with sandbox execution
│   │   └── MiscellaneousAgents.ts # Knowledge, Data, Communication, Business, Orchestrator
│   ├── core/
│   │   ├── Agent.ts              # Abstract base class, Tool interface, A2A bus
│   │   ├── Orchestrator.ts       # Task classification and agent routing
│   │   ├── Registry.ts           # Agent registry for lookup and A2A
│   │   ├── Memory.ts             # MongoDB conversation and state persistence
│   │   ├── Audit.ts              # Winston structured logging
│   │   └── VectorStore.ts        # Weaviate RAG interface
│   ├── interfaces/
│   │   ├── TelegramBot.ts        # grammy-based Telegram interface
│   │   ├── WebServer.ts          # Express HTTPS web server
│   │   └── WhatsAppBot.ts        # WhatsApp webhook interface
│   ├── services/
│   │   ├── LLMService.ts         # OpenAI-compatible LLM client
│   │   ├── McpProcessService.ts  # MCP server process manager (JSON-RPC)
│   │   ├── HuaweiCloudMcpManager.ts # MCP tool cache and dispatch
│   │   ├── HuaweiCloudService.ts # Direct Huawei Cloud REST API
│   │   ├── HuaweiSigner.ts       # AKSK signing (SDK + OBS S3-compatible)
│   │   ├── SandboxService.ts     # Docker code execution sandbox
│   │   ├── DeepgramService.ts    # STT/TTS
│   │   ├── GoogleWorkspaceService.ts # Gmail, Calendar, Drive
│   │   ├── WeaviateService.ts    # Vector store
│   │   ├── FileService.ts        # PDF/Word/Excel parsing
│   │   ├── ObsStorageService.ts  # OBS upload with pre-signed URLs
│   │   └── ...
│   └── mcp/
│       ├── definitions/          # OpenAPI spec JSON files for MCP tools
│       └── skills/               # Superpowers skill definitions
├── public/
│   └── index.html               # Digital Cockpit web UI
├── scripts/                      # Benchmark and utility scripts
├── docker-compose.yml            # Weaviate vector store
├── tsconfig.json
└── package.json
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_BASE_URL` | Yes | — | OpenAI-compatible LLM API endpoint |
| `OPENAI_API_KEY` | Yes | — | LLM API key |
| `HUAWEI_ACCESS_KEY` | Yes | — | Huawei Cloud AK |
| `HUAWEI_SECRET_KEY` | Yes | — | Huawei Cloud SK |
| `MONGODB_URI` | Yes | — | MongoDB connection string |
| `TELEGRAM_BOT_TOKEN` | No | — | Telegram bot token |
| `TELEGRAM_ALLOWED_USER_IDS` | No | — | Comma-separated Telegram user IDs |
| `MCP_WEB_PORT` | No | `3001` | Web server port |
| `MAX_ITERATIONS` | No | `10` | Max orchestrator routing iterations |
| `TIMEOUT_MS` | No | `120000` | Default tool timeout (ms) |
| `LOG_LEVEL` | No | `info` | Logging level |
| `DEEPGRAM_API_KEY` | No | — | Deepgram API key for STT/TTS |
| `WEAVIATE_URL` | No | `http://localhost:8080` | Weaviate endpoint |
| `WEAVIATE_API_KEY` | No | — | Weaviate API key |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama endpoint for embeddings |
| `OLLAMA_EMBED_MODEL` | No | `bge-m3` | Ollama embedding model |
| `ZATURN_SOURCES` | No | — | Database connection strings for Zaturn |
| `PYTHONPATH` | No | — | Python path for MCP server source |

Per-agent model overrides:

| Variable | Default | Agent |
|----------|---------|-------|
| `ORCHESTRATOR_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Orchestrator |
| `HUAWEI_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Huawei Cloud |
| `CODE_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Code |
| `DATA_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Data |
| `COMMUNICATION_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Communication |
| `KNOWLEDGE_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Knowledge |
| `BUSINESS_LLM_MODEL` | `DEFAULT_LLM_MODEL` | Business |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Node.js 23, TypeScript, ES Modules |
| LLM | OpenAI-compatible API (DeepSeek, Qwen, etc.) |
| Huawei Cloud | MCP servers (Python), AKSK signing, OBS S3-compatible signing |
| Memory | MongoDB (conversations), SQLite (MCP tool cache) |
| Vector Store | Weaviate + Ollama embeddings (bge-m3) |
| Web | Express + HTTPS (self-signed or custom cert) |
| Telegram | grammy |
| Voice | Deepgram (STT/TTS) |
| Google | googleapis SDK (OAuth2) |
| Sandbox | Docker |
| Logging | Winston |
| Dev | tsx (TypeScript execution), tsc (build) |

## License

Private — personal use only.
