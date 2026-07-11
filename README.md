# Mia Agent

An autonomous AI agent for personal productivity, built on **LangChain + LangGraph** with **n8n** as the execution layer.

---

## What is Mia?

Mia is an AI agent that manages your digital life through natural conversation:

| Domain        | Capabilities                                    |
|---------------|-------------------------------------------------|
| Gmail         | Read, search, compose, reply emails             |
| Calendar      | Schedule, reschedule, check availability        |
| Google Maps   | Geocode, reverse geocode, place search, routing |
| Tasks/Contacts| Manage tasks and safely resolve recipients      |
| Drive / Docs  | Full CRUD on Drive, Docs, and Sheets            |
| Web           | Search, read URLs, summarize pages              |
| GitHub        | Browse repos and perform confirmed write actions |
| Media         | OCR, document analysis, transcription, TTS      |
| Memory        | Long-term memory with semantic search (pgvector)|
| Automation    | Run reusable skills now or on cron schedules    |
| Utilities     | News, weather, gold prices, shortlinks, MCP     |

---

## Architecture

Mia follows a **Brain â†’ Skills â†’ Execution** architecture, cleanly separating
reasoning (Python) from tool execution (n8n workflows).

```text
                         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
                         â”‚   Telegram   â”‚
                         â”‚    (User)    â”‚
                         â””â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”˜
                                â”‚
                                â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚                   AGENT CORE  (Python)                â”‚
â”‚                                                       â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  State Graph  (LangGraph)                       â”‚  â”‚
â”‚  â”‚                                                 â”‚  â”‚
â”‚  â”‚  Ingress â”€â”€â–¶ Router â”€â”€â–¶ Planner â”€â”€â–¶ Specialist  â”‚  â”‚
â”‚  â”‚                                     â”‚           â”‚  â”‚
â”‚  â”‚              Composer â—€â”€â”€ Evaluator â—€â”˜          â”‚  â”‚
â”‚  â”‚                  â”‚                              â”‚  â”‚
â”‚  â”‚                  â–¼                              â”‚  â”‚
â”‚  â”‚           Memory Writer                         â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â”‚                                                       â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â” â”‚
â”‚  â”‚   Persona    â”‚  â”‚   Memory     â”‚  â”‚  Learning   â”‚ â”‚
â”‚  â”‚  (prompts,   â”‚  â”‚  (Postgres + â”‚  â”‚  (feedback  â”‚ â”‚
â”‚  â”‚   guidance)  â”‚  â”‚   pgvector)  â”‚  â”‚   loop)     â”‚ â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜ â”‚
â”‚                                                       â”‚
â”‚  â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”  â”‚
â”‚  â”‚  Capability Broker + ToolSpec + Skill Engine    â”‚  â”‚
â”‚  â”‚  Selects a small toolset and reusable workflow  â”‚  â”‚
â”‚  â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜  â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                            â”‚  HTTP / Webhook
                            â–¼
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              EXECUTION LAYER  (n8n)                   â”‚
â”‚                                                       â”‚
â”‚  Tool Gateway (/webhook/mia-tool)                     â”‚
â”‚      â”‚                                                â”‚
â”‚      â”œâ”€â”€ Google Workspace  (Gmail, Calendar, Drive)   â”‚
â”‚      â”œâ”€â”€ Google Maps       (Places, Geocoding, Routes) â”‚
â”‚      â”œâ”€â”€ GitHub Integration                           â”‚
â”‚      â”œâ”€â”€ Media Pipeline    (OCR, TTS, Transcription)  â”‚
â”‚      â”œâ”€â”€ Web Tools         (Search, Scrape, Summary)  â”‚
â”‚      â””â”€â”€ Utilities         (Weather, News, Gold, URL) â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
```

**Key design decisions:**
- The Agent Core handles all reasoning, planning, and memory â€” it never calls external APIs directly.
- The Execution Layer is stateless; each n8n workflow receives a request and returns a result.
- ToolSpec is the contract shared by Python tools, the gateway, and CI validation.
- External writes require exact confirmation and use a durable idempotency journal.
- The capability broker sends only relevant tools to each model call, reducing schema tokens and ambiguity.

---

## Project Structure

```text
mia-agent/
â”œâ”€â”€ agent/              # AI core
â”‚   â”œâ”€â”€ brain/          #   Router, planner, evaluator, composer
â”‚   â”œâ”€â”€ memory/         #   Postgres + pgvector memory store
â”‚   â”œâ”€â”€ skills/         #   Skill registry and tool definitions
â”‚   â”œâ”€â”€ graph/          #   LangGraph state machine
â”‚   â”œâ”€â”€ learning/       #   Feedback loop and insights
â”‚   â””â”€â”€ persona/        #   System prompts and guidance configs
â”œâ”€â”€ execution/          # n8n workflows
â”‚   â”œâ”€â”€ gateway/        #   Tool gateway webhook
â”‚   â”œâ”€â”€ integrations/   #   Google, GitHub, media, web, utils
â”‚   â””â”€â”€ monitors/       #   Health checks and alerting
â”œâ”€â”€ infra/              # Infrastructure
â”‚   â”œâ”€â”€ docker/         #   Dockerfiles and compose
â”‚   â”œâ”€â”€ sql/            #   Database schemas and migrations
â”‚   â””â”€â”€ embedder/       #   Embedding service
â”œâ”€â”€ scripts/            # Dev and maintenance utilities
â”œâ”€â”€ tests/              # Unit and integration tests
â””â”€â”€ docs/               # Architecture and deployment docs
```

---

## Quick Start

```bash
cp .env.example .env
# Fill in API keys (OpenAI, Google OAuth, Telegram, etc.)
docker compose -f infra/docker-compose.core.yml up -d --build
curl http://localhost:8000/health
```

Maps note:
- Set `GOOGLE_MAPS_API_KEY` and keep `MIA_MAPS_MAX_PLACE_RESULTS` low by default to control quota.
- Google Maps Platform pricing is now tracked by per-SKU monthly free usage caps instead of one shared monthly credit.

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

**Proprietary** â€” All rights reserved Â© 2024-2026 Huynh Minh.

This is **not** open-source software. Unauthorized copying, distribution, or use
is strictly prohibited. See [LICENSE](LICENSE) for full terms.

