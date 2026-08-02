# Mia Agent Documentation Index

Welcome to the Mia Agent documentation. This directory contains detailed guides on the architecture, skills, and deployment of the system.

## 📖 Architecture Guides

- **[Architecture Overview](architecture/OVERVIEW.md)**: Main request flow, component architecture, and design patterns.
- **[Agent Graph](architecture/AGENT_GRAPH.md)**: Detailed description of the LangGraph state machine, nodes, and transition logic.
- **[Skill Registry](architecture/SKILL_REGISTRY.md)**: Capability mappings, gateway schema payload contracts, and how to create new tools.
- **[Execution Layer](architecture/EXECUTION_LAYER.md)**: The role of n8n, Tool Gateway webhook structure, and workflow design guidelines.

## 🛠️ Skills & API Schemas

- **[Capability Map](skills/CAPABILITY_MAP.md)**: Complete list of all capability codes and their corresponding leaf workflows.
- **[Tool I/O Schema](skills/TOOL_IO_SCHEMA.md)**: Input/Output JSON schema examples for each execution capability.
- **[Adding Tools & Skills](skills/ADDING_TOOLS_AND_SKILLS.md)**: How to add a tool, a reusable skill, or an MCP server.

## 🔒 Security

- **[Security Model](security/SECURITY_MODEL.md)**: Trust boundaries, approvals, SSRF/content controls, and operational recommendations.

## 🚀 Deployment & Operations

- **[Setup & Deployment](deployment/SETUP.md)**: Deployment steps with docker compose, Postgres setup, and Telegram variables.
- **[LangChain Migration Notes](deployment/MIGRATION.md)**: Architectural changes and history of the migration from legacy workflows.
- **[Code Agent Setup](deployment/CODE_AGENT_SETUP.md)**: OpenCode workspaces, dev tools, and publish controls.
- **[Home Assistant Setup](deployment/HOME_ASSISTANT_SETUP.md)**: Smart-home rollout and device labeling.
- **[Memory RAG Upgrade](deployment/MEMORY_RAG_UPGRADE.md)**: Hybrid memory RAG architecture and acceptance checks.
- **[Platform Upgrade](deployment/UPGRADE_MIA_PLATFORM.md)**: Migration and rollout checklist.
