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

## 🚀 Deployment & Operations

- **[Setup & Deployment](deployment/SETUP.md)**: Deployment steps with docker compose, Postgres setup, and Telegram variables.
- **[LangChain Migration Notes](deployment/MIGRATION.md)**: Architectural changes and history of the migration from legacy workflows.
