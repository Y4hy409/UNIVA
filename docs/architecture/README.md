# CLARIUS Architecture Documentation

**Product:** CLARIUS – Privacy-Centric, On-Premises AI Business Intelligence Platform for MSMEs  
**Status:** Living Architecture (v0.2)  
**Last Updated:** 2026-07-19

---

## Purpose

This directory contains Architecture Decision Records (ADRs) for CLARIUS. Every significant architectural choice is documented here before implementation. ADRs are immutable once accepted; superseded decisions receive a new ADR that references the old one.

---

## ADR Index

| ID | Title | Status | Priority for MVP |
|----|-------|--------|------------------|
| [ADR-000](./ADR-000-master-architecture.md) | Master System Architecture | Accepted rev.2 | Foundation |
| [ADR-001](./ADR-001-monorepo-and-deployment.md) | Monorepo & On-Premises Deployment | Accepted rev.2 | Foundation |
| [ADR-002](./ADR-002-offline-licensing.md) | Offline Licensing System | Accepted | P0 |
| [ADR-003](./ADR-003-rbac-authorization.md) | RBAC Authorization Model | Accepted | P0 |
| [ADR-004](./ADR-004-agent-pipeline.md) | AI Agent Pipeline (LangGraph) | Accepted rev.2 | P0 |
| [ADR-005](./ADR-005-data-layer.md) | Data Layer & Knowledge Layer | Accepted rev.2 | P0 |
| [ADR-006](./ADR-006-mvp-delivery-plan.md) | MVP Delivery Plan (Aug 15, Team of 4) | Accepted | Planning |
| [ADR-007](./ADR-007-domain-event-bus.md) | Domain Event Bus | Accepted | P0 |
| [ADR-008](./ADR-008-background-jobs.md) | Background Jobs Layer | Accepted | P0 |
| [ADR-009](./ADR-009-migration-service.md) | Migration Service | Accepted | P0 |
| [ADR-010](./ADR-010-hierarchical-settings.md) | Hierarchical Settings | Accepted | P0 |
| [ADR-011](./ADR-011-plugin-architecture.md) | Plugin Architecture | Accepted | P0 |

---

## Architecture at a Glance (v0.2)

```
CLARIUS/
├── apps/desktop/src/features/     ← Frontend features (React)
├── apps/api/                      ← FastAPI entry
├── modules/                       ← Backend features (Python)
├── ai/                            ← LLM, agents, memory, OCR, prompts, guardrails
├── plugins/                       ← ERP, data, AI, automation, export plugins
├── infrastructure/
│   ├── database/                  ← DuckDB (Data Layer)
│   ├── knowledge/                 ← ChromaDB (Knowledge Layer)
│   ├── jobs/                      ← Background job queue + workers
│   ├── events/                    ← Domain event bus
│   ├── settings/                  ← Hierarchical settings
│   ├── security/                  ← Crypto, vault
│   ├── licensing/                 ← License verification
│   └── migrations/                ← Cross-store migration service
└── packages/                      ← ui, shared-types, shared-kernel
```

---

## Reading Order

1. **ADR-000** — System context, layer boundaries, edition model
2. **ADR-001** — Deployment, startup sequence, browser-ready API
3. **ADR-005** — Data Layer vs Knowledge Layer
4. **ADR-011** — Plugin architecture
5. **ADR-003** — RBAC
6. **ADR-002** — Licensing
7. **ADR-010** — Settings hierarchy
8. **ADR-004** — AI agent pipeline
9. **ADR-007** — Domain event bus
10. **ADR-008** — Background jobs
11. **ADR-009** — Migration service
12. **ADR-006** — What ships by August 15

---

## ADR Template

New ADRs follow this structure:

```
# ADR-NNN: Title
## Status
## Context
## Decision
## Consequences
## Alternatives Considered
## References
```

---

## Governance

- **Author:** Architecture Lead (with team review)
- **Reviewers:** All 4 team members before `Accepted`
- **Supersession:** Create ADR-NNN+1; mark old ADR `Superseded by ADR-NNN+1`
- **Revision:** Incremental refinements noted as `Accepted (rev. N)` on same ADR
