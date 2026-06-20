# Mia: Advanced AI Agent Architecture & Portfolio Showcase

Welcome to the technical overview of **Mia**, an advanced, locale-aware AI agent designed to act as a personal command dispatching and workflow automation assistant. 

This repository showcases state-of-the-art AI engineering practices, demonstrating how LLM reasoning can be structured, validated, and internationalized for production-grade reliability.

---

## Key Capabilities

Mia connects to private tools and Google Workspace services to handle complex, multi-step requests:

- **Google Workspace Integration**: Reads, writes, creates, and updates events on Google Calendar; searches and drafts/replies to emails on Gmail; lists, shares, and copies files on Google Drive; creates and appends content on Google Docs/Sheets.
- **Dynamic Web Scraping & Q&A**: Dynamically fetches webpage contents, summarizes long articles, extracts metadata, and answers questions about specific URLs.
- **Media Processing**: Summarizes video/audio transcripts, performs text-to-speech (TTS), and handles document Q&A.
- **Shortlink Routing**: Integrates with a Cloudflare Worker & Postgres database to create short redirect URLs (e.g., `https://go.example.com/<id>`) on-the-fly.
- **System Memory**: Maintains a long-term vector database memory (semantic search, write, recent lists) to persist context across conversations.

---

## Architectural Highlights & Design Patterns

### 1. Command Dispatching & Direct Tool Mapping
Instead of relying on slow, expensive LLM function calling for every single query, Mia uses a hybrid execution approach. The parsing layer ([planner.py](./agent/brain/planner.py)) employs lightweight deterministic regex matching combined with context-aware NLP to instantly route queries (like *"weather in Hanoi"* or *"search files matching invoices"*) directly to target workflows:
- **Low Latency**: Bypasses LLM planning when intent is clear.
- **Structured Payload Resolution**: Resolves arguments like dates, senders, and locations before hitting the API.

### 2. Guarded Mutations & LLM Validation
To ensure security and reliability, all destructive or high-risk mutations (e.g., deleting events, appending documents, sharing folders) are strictly guarded. 
- Workflows verify that specific IDs are targeted rather than executing operations on the first search result.
- The approval layer ([approval.py](./agent/approval.py)) generates a secure confirmation flow, requesting explicit user verification before dispatching destructive commands.

### 3. Dynamic Internationalization (i18n) Layer
To support global utility while keeping personal configurations private, Mia features a dynamic internationalization system:
- The localization helper ([__init__.py](./agent/i18n/__init__.py)) reads configuration variables (`MIA_LOCALE`) at runtime.
- Catalogs for English ([en.json](./agent/i18n/locales/en.json)) and Vietnamese ([vi.json](./agent/i18n/locales/vi.json)) completely decouple system prompts, error templates, and keyword matchers from the Python source files.
- Decoupled templates support clean code reviews in English by default, while live deployments run in Vietnamese with customized owner tokens (`OWNER_DISPLAY_NAME=anh Minh`).

### 4. Resilient Error Classification & Self-Healing
The workflow execution error monitor ([workflow_error_monitor.json](./execution/monitors/workflow_error_monitor.json)) acts as a self-healing diagnostic layer:
- Evaluates API issues, network failures, and syntax exceptions.
- Classifies severity and suggests actionable fixes based on execution state.
- Dispatches alert payloads directly to Telegram.

---

## Code References (Engineering Quality Showcase)

Feel free to browse these core modules to evaluate the codebase's construction:

- **Core API Gateway**: [api.py](./agent/api.py) — Handles HTTP request routing and orchestrates prompt compilation.
- **Service Orchestration**: [service.py](./agent/service.py) — Manages session memory, evaluates command routing, and calls the appropriate integration nodes.
- **LLM Prompt Context**: [system_prompt.py](./agent/persona/system_prompt.py) — Declares system prompts compiled dynamically using the i18n engine.
- **Configuration & Security Settings**: [config.py](./agent/config.py) — Aggregates and validates environment settings safely.
- **Integration Engine Client**: [execution_client.py](./agent/execution_client.py) — Dispatches execution payloads to n8n sub-workflows.

---

## License & Copyright Notice

**Copyright (c) 2026. All rights reserved.**

This software is **proprietary** and confidential. It is created as a showcase portfolio for recruiters. 
No part of this codebase may be copied, redistributed, hosted, or used for commercial/non-commercial deployment without explicit written permission from the copyright owner.
