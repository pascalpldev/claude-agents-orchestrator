---
name: maintain-context
description: This skill provides guidance when a developer asks how to maintain CLAUDE.md, memory files, or project context. Use when the user asks "what should I update?", "how do I maintain context?", "is my CLAUDE.md up to date?", or wants to audit the current state of their project context files.
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

# maintain-context — Audit and maintain project context

This skill audits and guides the maintenance of CLAUDE.md and memory files so that future Claude sessions always have accurate context.

## When to invoke

- After completing a significant feature
- When onboarding a new developer to the project
- When Claude seems to be missing context or making wrong assumptions
- When explicitly asked to audit project context

## What to audit

### 1. CLAUDE.md — project source of truth

Read the current CLAUDE.md and check:

```
✓ Objective still accurate?
✓ Architecture reflects current state?
✓ Stack table up to date (new dependencies)?
✓ Critical files list still valid?
✓ Phases status correct (✅/⏳)?
✓ Startup commands still work?
✓ Constraints and patterns still apply?
```

**Update if**: anything is stale, missing, or wrong.
**Do not add**: secrets, personal info, per-developer paths, team configs.

### 2. Memory files — personal context

Located at `~/.claude/projects/*/memory/MEMORY.md` for the current project.

Check:
```
✓ MEMORY.md index points to existing files?
✓ Project memories reflect current decisions?
✓ Feedback memories still apply?
✓ No stale or contradictory entries?
```

Memory file types and what goes in them:

| Type | Content | Update when |
|------|---------|-------------|
| `project` | Decisions, phases, objectives, deadlines | Something significant changed |
| `feedback` | How Claude should/shouldn't behave | Claude made a mistake you corrected |
| `user` | Developer role, preferences, expertise | You learned something about how they work |
| `reference` | External systems (Linear, Notion, etc.) | A new system was mentioned as source of truth |

### 3. What should NOT be in these files

- API keys, tokens, passwords → use `.env` (gitignored)
- Hardcoded absolute paths → use relative paths
- Current branch names or in-progress work → this is ephemeral
- Debugging notes or temporary decisions → these belong in commits

## How to audit

1. Read `CLAUDE.md` from the project root
2. Read `~/.claude/projects/<project>/memory/MEMORY.md`
3. Read each referenced memory file
4. Compare against recent conversation and git log
5. Report what is stale, missing, or inaccurate
6. Propose updates with clear justification for each change
7. Apply updates only after the developer confirms

## Output format

```
## Context Audit

### CLAUDE.md
- ✅ Objective: accurate
- ⚠️ Architecture: missing new `storage/` module added last week
- ⚠️ Phases: Phase 3 now complete, should be marked ✅

### Memory files
- ✅ user_preferences.md: still accurate
- ⚠️ project_apis.md: ElevenLabs endpoint changed
- ❌ feedback_testing.md: references a pattern that was removed

### Proposed updates
1. CLAUDE.md: mark Phase 3 as ✅, add storage/ to architecture
2. project_apis.md: update ElevenLabs endpoint
3. feedback_testing.md: remove stale entry

Shall I apply these?
```
