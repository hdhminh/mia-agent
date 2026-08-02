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
| Smart Home    | Control Home Assistant devices, scenes, and room status |
| Tasks/Contacts| Manage tasks and safely resolve recipients      |
| Drive / Docs  | Full CRUD on Drive, Docs, and Sheets            |
| Web           | Search, read URLs, summarize pages              |
| GitHub        | Browse repos and perform confirmed write actions |
| Code Agent    | Create managed workspaces, import local repos, code through OpenCode, review/optimize/test/lint projects, fix issues, and publish with confirmation |
| Automation    | Run reusable skills now or on cron schedules; every scheduled run delivers its result back to the chat |
| Media         | OCR, document analysis, transcription, TTS      |
| Memory        | Automatic hybrid Memory RAG with pgvector, pg_textsearch/pg_trgm, owner scope, and approval proposals |
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
│  │  Ingress ──▶ Memory Retriever ──▶ Supervisor    │  │
│  │                                  └──▶ Specialist│  │
│  │                                      │          │  │
│  │              Composer ◀── Evaluator ◀┘          │  │
│  │                  │                              │  │
│  │                  ▼                              │  │
│  │           Memory Writer                         │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
│  │   Persona    │  │   Memory     │  │  Learning   │ │
│  │  (prompts,   │  │  (Postgres + │  │  (feedback  │ │
│  │   guidance)  │  │   pgvector + │  │   loop)     │ │
│  │              │  │ pg_textsearch│  │             │ │
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
│      ├── Google Maps       (Places, Geocoding, Routes) │
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
- Memory retrieval runs automatically before specialist routing, so relevant long-term context is injected without relying on the model to call a memory tool.
- Durable auto-detected memories are staged as proposals first; explicit user memory writes still save immediately.

---

## Current Status

- **Memory RAG:** upgraded from optional semantic search to automatic retrieval-augmented memory.
- **Hybrid retrieval:** combines dense `pgvector` search with lexical ranking and Reciprocal Rank Fusion.
- **Database:** production compose now targets PostgreSQL 17 with `pg_textsearch`; schema still falls back to `pg_trgm` if the extension is unavailable; schema applications are tracked in `mia_schema_migrations`.
- **Safety:** memory is owner-scoped by `owner_id`; automatic memory proposals require approval before becoming durable; `memory.write` rejects content that looks like a secret.
- **Code Agent:** OpenCode runs in managed workspaces under `mia-workspaces`, supports local repo import, diff review, apply/publish confirmation, and DeepSeek V4 Flash through the code gateway. The code toolset now also includes `code_review_project`, `code_optimize_project`, `code_run_test`, `code_run_lint`, and `code_fix_from_issue`. All external code writes (apply, publish, PR) go through the centralized approval flow — the model can no longer self-approve.
- **Dev-first routing:** natural-language dev requests ("review code", "sửa lỗi dòng 42 file service.py", "viết test cho hàm X") route to the code agent before the GitHub branch; generic "công việc" / "tự động hóa" no longer hijack questions into Tasks/Automation tools.
- **Streaming:** `/mia/chat/stream` emits SSE progress events while the graph runs, so long agent calls no longer wait silently.
- **Automation delivery:** every scheduled automation now sends its result to the originating Telegram chat (not just `remind_me`), suppressed during `MIA_REMINDER_QUIET_HOURS`.
- **Smart Home:** Home Assistant integration is label-gated with `MIA_HOME_ALLOWED_LABEL`.
- **Gateway hardening:** n8n Tool Gateway rejects private/local URLs for web fetch (SSRF), compares the gateway token in constant time, and every exported workflow carries a 60s HTTP timeout plus `continueRegularOutput` on fallible nodes.
- **Verification:** route eval currently passes `93/93`; unit and contract test suite passes `249/249`.

## Measured Verification

These numbers come from deterministic local checks and one live `/mia/chat` smoke run, not a rolling time-window metric.

| Check | Result | What It Measures |
|-------|--------|------------------|
| Unit and contract tests | `249/249` passed | Python contracts, tool payloads, workflow JSON expectations, routing regressions, api auth, SSRF guard, skills engine, follow-up handler |
| Route quality eval | `93/93` passed | Intent routing across general, Google Workspace, GitHub, multi-intent, media, and dev requests |
| Multi-intent route eval | `25/25` passed | Mixed requests such as Drive + Docs + Sheets without misrouting to Code |
| Memory RAG golden eval | `Recall@5 = 1.00`, `MRR = 0.90` | Whether the right memory appears in the top retrieved chunks |
| Live chat smoke | `8/8` passed | Real `/mia/chat` calls against the running Docker stack |

Latest live smoke latencies measured from the client side:

| Flow | Tool Evidence | Latency |
|------|---------------|---------|
| Basic chat | no tool required | `5.78s` |
| Memory write | `memory_write` | `3.64s` |
| Memory recall | automatic Memory RAG, no manual memory tool | `6.71s` |
| Calendar today | `calendar_list_today` | `0.15s` |
| Calendar tomorrow | `calendar_list_tomorrow` | `0.37s` |
| Smart home bedroom status | `smarthome_room_status` | `4.38s` |
| Code project status | `code_project_status` | `6.09s` |
| GitHub write approval | approval prompt before write | `7.79s` |

---

## Project Structure

```text
mia-agent/
├── agent/              # AI core
│   ├── brain/          #   Router, planner, evaluator, composer
│   ├── memory/         #   Hybrid Postgres memory RAG store
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
docker compose -f infra/docker-compose.core.yml up -d --build
curl http://localhost:8000/health
```

Maps note:
- Set `GOOGLE_MAPS_API_KEY` and keep `MIA_MAPS_MAX_PLACE_RESULTS` low by default to control quota.
- Google Maps Platform pricing is now tracked by per-SKU monthly free usage caps instead of one shared monthly credit.

Smart home note:
- The stack can now run a local Home Assistant container at `http://<LAN-IP>:8123`.
- Mia only controls entities carrying the Home Assistant label named by `MIA_HOME_ALLOWED_LABEL` (default `mia_allowed`).
- Recommended first setup: connect Tuya, Xiaomi, and Google Cast directly in Home Assistant, assign Areas, then label only the entities Mia is allowed to touch.

Memory note:
- `MIA_MEMORY_RAG_ENABLED=true` enables automatic memory retrieval before the supervisor.
- `MIA_MEMORY_RAG_LIMIT`, `MIA_MEMORY_RAG_THRESHOLD`, and `MIA_MEMORY_RAG_TOKEN_BUDGET` control how much retrieved context reaches the model.
- PostgreSQL remains the source of truth; memory chunks use 384-dimensional embeddings from the local embedder service.
- `python scripts/maintenance/consolidate_memory.py` marks duplicate memory items as superseded.

Model note:
- `MIA_MODEL_MAX_TOKENS` (default 1600) caps the answer length; the model itself is configured via `MIA_MODEL` / `MIA_DEEPSEEK_MODEL`.
- `MIA_REMINDER_QUIET_HOURS` (default `23-7`) suppresses scheduled reminders overnight.
- `/mia/chat/stream` returns SSE progress events; `MiaChatRequest.locale` (`vi`|`en`) overrides the global `MIA_LOCALE` per conversation.

Verification note:
- Run route quality checks with `python scripts/dev/eval_route_quality.py`.
- Run real chat smoke tests against the running service with `python scripts/maintenance/live_chat_smoke.py`.
- Hourly workflow validation is handled by `scripts/sync/sync_daemon.sh` (installed in the system cron).

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
| [Home Assistant setup](docs/deployment/HOME_ASSISTANT_SETUP.md) | Practical smart-home rollout |
| [Platform upgrade](docs/deployment/UPGRADE_MIA_PLATFORM.md) | Migration and rollout checklist |
| [Memory RAG upgrade](docs/deployment/MEMORY_RAG_UPGRADE.md) | Hybrid memory RAG architecture, PG17/pg_textsearch rollout, and acceptance checks |
| [Security model](docs/security/SECURITY_MODEL.md)      | Auth, approval and network controls  |
| [Code agent setup](docs/deployment/CODE_AGENT_SETUP.md) | OpenCode workspace flow and publish controls |
| [Adding tools and skills](docs/skills/ADDING_TOOLS_AND_SKILLS.md) | Extension guide |

---

## License

**Proprietary** — All rights reserved © 2024-2026 Huynh Minh.

This is **not** open-source software. Unauthorized copying, distribution, or use
is strictly prohibited. See [LICENSE](LICENSE) for full terms.
