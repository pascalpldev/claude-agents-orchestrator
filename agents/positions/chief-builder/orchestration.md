---
name: orchestration
description: Full-lifecycle pipeline and global rules — reference only, not loaded at runtime
scope: chief-builder only
---

# Orchestration — Chief Builder

> This file is a documentation reference. The operational process is in `agent.md`.
> Do not load this file at runtime — everything necessary is in `agent.md`.

## Pipeline

```
Ticket to-enrich
  → chief-builder : enrichment + deliberation → plan → enriched
  → [human gate] → to-dev            (or auto-promote if scope S/M is clear)
  → dev persona  : implementation → PR → to-test
  → [human gate] → godeploy
  → dev persona  : merge → deployed
```

## Global rules

- Human gate blocks the transition to `to-dev` unless label `autonomous` or auto-promote score met
- 1 revision max per wave in the deliberation loop
- Silence is value — a role with no concrete contribution does not speak
- Never leave a ticket stuck in `enriching` or `dev-in-progress`
