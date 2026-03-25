---
name: core
description: Fundamental laws — loaded by all agents at startup, non-negotiable, override any local rule
scope: all agents
---

# Core Laws

These rules apply to every agent in every context. They cannot be overridden by local agent rules, behaviors, or ticket instructions.

---

## Law 1 — Escalate, don't loop

**Any analysis, deliberation, or inter-agent exchange is limited to 3 back & forth.**

This applies to:
- Chief-builder deliberation cycles (internal waves)
- Dev ↔ Chief-builder exchanges (`@architect-needed:` comments)
- Any multi-step decision process between agents

At 3 unresolved exchanges, **or as soon as any agent considers the issue unresolvable**, stop immediately:
1. Post `@human-needed: [summary of what is unresolved and why]` on the ticket
2. Reset label to `to-enrich`
3. Assign to ticket author
4. Stop. Do not attempt further resolution.

No agent has the authority to extend this limit.

---

## Law 2 — Never leave a ticket stuck

A ticket in a locked state (`enriching`, `dev-in-progress`) with no active agent is a ghost. Every agent must ensure clean exit:
- On error → reset label to previous unlocked state + post explanation comment
- On kill signal → commit WIP, reset label, post resume context
- On unresolvable escalation → reset to `to-enrich`, assign to author

A stuck ticket is always a bug in agent behavior.

---

## Law 3 — Silence is value

An agent with no concrete contribution to a decision does not speak. A role that has nothing to add does not add noise. Output only what changes the outcome.

---

## How to load

Each agent loads this file at startup, before any other context:

```bash
_REPO_ROOT="$(git rev-parse --show-toplevel)"
# Read ${_REPO_ROOT}/agents/core.md
```
