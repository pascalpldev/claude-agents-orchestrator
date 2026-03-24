---
name: cao-process-tickets
description: |
  Poll GitHub tickets and process them through the enrichment and dev workflows.

  Accepts an optional role filter and loop mode:
  - /cao-process-tickets             → process all workflows, once
  - /cao-process-tickets chief-builder   → enrichment only (to-enrich → enriched)
  - /cao-process-tickets dev         → dev + merge only (to-dev → to-test, godeploy → deployed)
  - /cao-process-tickets --loop      → process all, then schedule every 5 minutes
  - /cao-process-tickets dev --loop  → dev only, looping every 5 minutes
argument-hint: "[chief-builder|dev|all] [--loop] [--interval <minutes>]"
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# /cao-process-tickets — Poll and process GitHub tickets

Core automation workflow. Detects tickets in various states and launches the appropriate agent.

## Parse arguments

Parse `$ARGUMENTS` before doing anything:

```
ROLE = "all"          # default
LOOP = false
INTERVAL = 5          # minutes, default

For each token in $ARGUMENTS:
  "chief-builder"           → ROLE = "chief-builder"
  "dev"                 → ROLE = "dev"
  "all"                 → ROLE = "all"
  "--loop"              → LOOP = true
  "--interval <n>"      → INTERVAL = n
```

If `--loop` is set: announce it at the start.
```
🔄 Loop mode active — role: {ROLE}, interval: {INTERVAL}min
```

## Context detection

Before processing:
1. Run `git remote get-url origin` to extract OWNER and REPO
2. Read the project's `CLAUDE.md` for architecture context
3. Fetch open issues: `gh issue list --repo $OWNER/$REPO --state open --json number,title,labels,assignees`

## Workflows to execute

Run only the workflows matching ROLE:

| ROLE | Workflows to run |
|------|-----------------|
| `all` | 1 + 2 + 3 |
| `chief-builder` | 1 only |
| `dev` | 2 + 3 |

### 1. Enrichment workflow (chief-builder)

Skip if ROLE = "dev".

**Detects**: `to-enrich` label + no assignee

```
a. Lock: gh issue edit N --add-label "enriching" --remove-label "to-enrich"
b. Launch chief-builder agent:
   - Reads ticket via gh issue view
   - Writes enrichment plan
   - Posts as comment via gh issue comment
   - Changes label enriching → enriched
```

**If challenged**: `to-enrich` + feedback comment
```
a. chief-builder agent re-reads comments
b. Responds to feedback
c. Changes label to-enrich → enriched
```

### 2. Dev workflow (dev)

Skip if ROLE = "chief-builder".

**Detects**: `to-dev` label + no assignee

```
a. Lock: gh issue edit N --add-label "dev-in-progress" --remove-label "to-dev"
b. Launch dev agent:
   - Reads full ticket + plan
   - Creates branch, implements, pushes
   - Creates PR via gh pr create
   - Changes label dev-in-progress → to-test
```

**If feedback**: `to-dev` + feedback comment
```
a. dev agent detects change + feedback
b. Fixes, commits, changes label → to-test
```

### 3. Merge workflow (dev)

Skip if ROLE = "chief-builder".

**Detects**: `godeploy` label on `to-test` ticket

```
a. Lock: gh issue edit N --add-label "dev-in-progress" --remove-label "to-test"
b. Launch dev agent (godeploy mode):
   - Finds PR via gh pr list
   - Verifies mergeable via gh pr view
   - Merges via gh pr merge
   - Changes label → deployed
```

## After processing

### Summary

Always output a brief summary:
```
✅ Processed: [list of tickets handled, or "nothing to process"]
⏭️  Skipped (locked): [tickets in enriching/dev-in-progress, if any]
```

### Loop scheduling

If LOOP = true, after the summary use `CronCreate` to schedule the next run:

```
CronCreate(
  taskId: "cao-process-{ROLE}",
  cronExpression: "*/{INTERVAL} * * * *",
  prompt: "/cao-process-tickets {ROLE} --loop --interval {INTERVAL}"
)
```

After CronCreate:
- If CronCreate succeeds, log the worker_start event:
  ```
  RUN_ID = current timestamp in format YYYYMMDD_HHMMSS_loop
  Run: python3 lib/logger.py "{RUN_ID}" "worker" "null" "worker_start" "ok" "loop started" '{"role":"{ROLE}","interval":{INTERVAL},"loop":true}'
  ```
- If CronCreate fails, log a schedule_error:
  ```
  Run: python3 lib/logger.py "{RUN_ID}" "worker" "null" "schedule_error" "error" "CronCreate failed" '{"role":"{ROLE}"}'
  ```

Then output:
```
⏱️  Next run in {INTERVAL} min (cron: cao-process-{ROLE})
   Stop with: /cancel-cao or ask Claude to delete cron "cao-process-{ROLE}"
```

## Example sessions

**One-shot, all roles:**
```
/cao-process-tickets
→ Enriches #5, implements #3, merges #1
→ Done.
```

**Team-lead only, looping every 5 min:**
```
/cao-process-tickets chief-builder --loop
→ 🔄 Loop mode — role: chief-builder, interval: 5min
→ Enriches #5
→ ✅ Processed: #5
→ ⏱️ Next run in 5 min (cron: cao-process-chief-builder)
```

**Dev only, custom interval:**
```
/cao-process-tickets dev --loop --interval 10
→ 🔄 Loop mode — role: dev, interval: 10min
→ Nothing to process
→ ⏱️ Next run in 10 min (cron: cao-process-dev)
```

## Implementation notes

- Each run is atomic (one ticket processed per state)
- Locked states (enriching, dev-in-progress) prevent collisions between roles running in parallel
- GitHub operations use `gh` CLI; GitHub MCP for `search_code` and CI `actions_*`
- Git operations (checkout, commit, push) remain bash
- OWNER/REPO auto-detected from git remote
