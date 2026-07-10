# Mia Agent

An autonomous AI agent for personal productivity, built on **LangChain + LangGraph** with **n8n** as the execution layer.

---

## What is Mia?

Mia is an AI agent that manages your digital life through natural conversation:

| Domain        | Capabilities                                    |
|---------------|-------------------------------------------------|
| Gmail         | Read, search, compose, reply emails             |
| Calendar      | Schedule, reschedule, check availability        |
| Tasks/Contacts| Manage tasks and safely resolve recipients      |
| Drive / Docs  | Full CRUD on Drive, Docs, and Sheets            |
| Web           | Search, read URLs, summarize pages              |
| GitHub        | Browse repos, issues, branches, files, and PRs  |
| Media         | OCR, document analysis, transcription, TTS      |
| Memory        | Long-term memory with semantic search (pgvector)|
| Automation    | Run reusable skills now or on cron schedules    |
| Utilities     | News, weather, gold prices, shortlinks, MCP     |

---

## Architecture

Mia follows a **Brain → Skills → Execution** architecture, cleanly separating
reasoning (Python) from tool execution (n8n workflows).

```text
                         ┌──────────────┐
                         │   Telegram   │
                         │    (User)    │
                         └──────┬───────┘
                                │
                                ▼
┌───────────────────────────────────────────────────────┐
│                   AGENT CORE  (Python)                │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  State Graph  (LangGraph)                       │  │
│  │                                                 │  │
│  │  Ingress ──▶ Router ──▶ Planner ──▶ Specialist  │  │
│  │                                     │           │  │
│  │              Composer ◀── Evaluator ◀┘          │  │
│  │                  │                              │  │
│  │                  ▼                              │  │
│  │           Memory Writer                         │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Persona    │  │   Memory     │  │  Learning   │ │
│  │  (prompts,   │  │  (Postgres + │  │  (feedback  │ │
│  │   guidance)  │  │   pgvector)  │  │   loop)     │ │
│  └──────────────┘  └──────────────┘  └─────────────┘ │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Capability Broker + ToolSpec + Skill Engine    │  │
│  │  Selects a small toolset and reusable workflow  │  │
│  └────────────────────────┬────────────────────────┘  │
└───────────────────────────┼───────────────────────────┘
                            │  HTTP / Webhook
                            ▼
┌───────────────────────────────────────────────────────┐
│              EXECUTION LAYER  (n8n)                   │
│                                                       │
│  Tool Gateway (/webhook/mia-tool)                     │
│      │                                                │
│      ├── Google Workspace  (Gmail, Calendar, Drive)   │
│      ├── GitHub Integration                           │
│      ├── Media Pipeline    (OCR, TTS, Transcription)  │
│      ├── Web Tools         (Search, Scrape, Summary)  │
│      └── Utilities         (Weather, News, Gold, URL) │
└───────────────────────────────────────────────────────┘
```

**Key design decisions:**
- The Agent Core handles all reasoning, planning, and memory — it never calls external APIs directly.
- The Execution Layer is stateless; each n8n workflow receives a request and returns a result.
- ToolSpec is the contract shared by Python tools, the gateway, and CI validation.
- External writes require exact confirmation and use a durable idempotency journal.
- The capability broker sends only relevant tools to each model call, reducing schema tokens and ambiguity.

---

## Project Structure

```text
mia-agent/
├── agent/              # AI core
│   ├── brain/          #   Router, planner, evaluator, composer
│   ├── memory/         #   Postgres + pgvector memory store
│   ├── skills/         #   Skill registry and tool definitions
│   ├── graph/          #   LangGraph state machine
│   ├── learning/       #   Feedback loop and insights
│   └── persona/        #   System prompts and guidance configs
├── execution/          # n8n workflows
│   ├── gateway/        #   Tool gateway webhook
│   ├── integrations/   #   Google, GitHub, media, web, utils
│   └── monitors/       #   Health checks and alerting
├── infra/              # Infrastructure
│   ├── docker/         #   Dockerfiles and compose
│   ├── sql/            #   Database schemas and migrations
│   └── embedder/       #   Embedding service
├── scripts/            # Dev and maintenance utilities
├── tests/              # Unit and integration tests
└── docs/               # Architecture and deployment docs
```

---

## Quick Start

```bash
cp .env.example .env
# Fill in API keys (OpenAI, Google OAuth, Telegram, etc.)
docker compose -f infra/docker-compose.yml up -d --build
curl http://localhost:8000/health
```

---

## Documentation

| Document                                              | Description                         |
|-------------------------------------------------------|-------------------------------------|
| [Architecture Overview](docs/architecture/OVERVIEW.md)| System design and component roles   |
| [Agent Graph](docs/architecture/AGENT_GRAPH.md)       | LangGraph state machine walkthrough |
| [Skill Registry](docs/architecture/SKILL_REGISTRY.md) | How skills map to n8n workflows     |
| [Execution Layer](docs/architecture/EXECUTION_LAYER.md)| n8n workflow design and gateway     |
| [Capability Map](docs/skills/CAPABILITY_MAP.md)       | Full list of Mia's abilities        |
| [Deployment](docs/deployment/SETUP.md)                | Production deployment guide         |
| [Platform upgrade](docs/deployment/UPGRADE_MIA_PLATFORM.md) | Migration and rollout checklist |
| [Security model](docs/security/SECURITY_MODEL.md)      | Auth, approval and network controls  |
| [Adding tools and skills](docs/skills/ADDING_TOOLS_AND_SKILLS.md) | Extension guide |

---

## License

**Proprietary** — All rights reserved © 2024-2026 Huynh Minh.

This is **not** open-source software. Unauthorized copying, distribution, or use
is strictly prohibited. See [LICENSE](LICENSE) for full terms.
