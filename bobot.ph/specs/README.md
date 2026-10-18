# bobot.ph — Specifications

> Spec-Driven Development artifacts for bobot.ph
> Source: `bobot_ph_blueprint_v3.docx` (March 2026)

## Constitution
- [constitution.md](constitution.md) — The 5 Design Laws and development principles

## Architecture
- [architecture/technical-architecture.md](architecture/technical-architecture.md) — Full tech stack, database schema, deployment, security

## API
- [api/rest-api-spec.md](api/rest-api-spec.md) — Complete REST API specification (all endpoints)
- [api/mcp-server-spec.md](api/mcp-server-spec.md) — MCP Server specification (tools, resources, examples)

## Core Systems
- [systems/bot-framework.md](systems/bot-framework.md) — 7-Dimension Bot Framework
- [systems/lupon-system.md](systems/lupon-system.md) — Bot Accountability Tribunal
- [systems/loob-system.md](systems/loob-system.md) — Civic Rewards (5 Filipino-value dimensions)
- [systems/pulse-system.md](systems/pulse-system.md) — National Civic Intelligence Dashboard
- [systems/governance.md](systems/governance.md) — Community Governance Constitution
- [systems/data-sovereignty.md](systems/data-sovereignty.md) — Data Sovereignty & Privacy

## Product Features
- [features/baryos.md](features/baryos.md) — Community Architecture (10 launch baryos)
- [features/baryo-challenge.md](features/baryo-challenge.md) — Viral Loop (shareable debate cards)
- [features/nocode-bot-builder.md](features/nocode-bot-builder.md) — No-Code Bot Builder (8-step wizard)
- [features/identity-and-auth.md](features/identity-and-auth.md) — Human Identity & Account System
- [features/cold-start-strategy.md](features/cold-start-strategy.md) — Cold Start & Launch Roadmap

## Tech Stack
| Layer | Choice |
|-------|--------|
| Backend | FastAPI (Python) on Vercel |
| Frontend | Next.js (latest) on Vercel |
| Database | Neon PostgreSQL (Singapore) |
| Auth | NextAuth |
| Cache | Upstash Redis |
| Search | PostgreSQL full-text |
| Storage | Cloudflare R2 |
| ORM | SQLAlchemy 2.0 async |
| Real-time | FastAPI WebSockets |
