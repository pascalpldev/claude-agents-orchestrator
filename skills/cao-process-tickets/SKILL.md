---
name: cao-process-tickets
description: |
  Poll GitHub tickets and process them through the enrichment and dev workflows.

  Accepts an optional role filter and loop mode:
  - /cao-process-tickets                    → process all workflows, once
  - /cao-process-tickets chief-builder      → enrichment only (to-enrich → enriched)
  - /cao-process-tickets dev                → dev + merge only (to-dev → to-test, godeploy → deployed)
  - /cao-process-tickets --loop             → process all, then schedule every 5 minutes
  - /cao-process-tickets dev --loop         → dev only, looping every 5 minutes
  - /cao-process-tickets --ghost-buster     → clean up dead agents first, then process
argument-hint: "[chief-builder|dev|all] [--loop] [--interval <minutes>] [--ghost-buster]"
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# /cao-process-tickets — Poll and process GitHub tickets

Core automation workflow. Detects tickets in various states and launches the appropriate agent.

## Parse arguments

Parse `$ARGUMENTS` before doing anything:

```
ROLE         = "all"    # default
LOOP         = false
INTERVAL     = 5        # minutes, default
GHOST_BUSTER = false

For each token in $ARGUMENTS:
  "chief-builder"    → ROLE = "chief-builder"
  "dev"              → ROLE = "dev"
  "all"              → ROLE = "all"
  "--loop"           → LOOP = true
  "--interval <n>"   → INTERVAL = n
  "--ghost-buster"   → GHOST_BUSTER = true
```

If `--loop` is set: announce it at the start.
```
🔄 Loop mode active — role: {ROLE}, interval: {INTERVAL}min
```

## Phase 0 — Ghost buster (if --ghost-buster)

If GHOST_BUSTER = true, execute **before any ticket processing**:

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
python3 "${REPO_ROOT}/lib/ghost_buster.py" \
  --repo "$OWNER/$REPO" \
  --locks-dir "${REPO_ROOT}/.locks"
```

Processes all detected ghosts (local + remote) sequentially, displays a summary,
then continues to normal ticket processing.

If no ghost found → displays `👻 Ghost buster — no ghost detected.` and continues.

## Context detection

Before processing:
1. Run `git remote get-url origin` to extract OWNER and REPO
2. Read the project's `CLAUDE.md` for architecture context
3. Fetch open issues: `gh issue list --repo $OWNER/$REPO --state open --json number,title,labels,assignees`

## Workflows to execute

Run only the workflows matching ROLE:

| ROLE | Workflows to run |
|------|-----------------|
| `all` | 1 + 2 + 3 + 4 |
| `chief-builder` | 1 only |
| `dev` | 2 + 3 + 4 |

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

**If challenged or escalated by dev**: `to-enrich` is reused for all chief-builder re-entries.
Chief-builder detects the context from the last comment:
- Last comment is human feedback → re-enrich with feedback
- Last comment starts with `@architect-needed:` → targeted response (see Dev ↔ Chief-Builder protocol in agent.md)

```
a. Lock: gh issue edit N --add-label "enriching" --remove-label "to-enrich"
b. Chief-builder reads the last comment only — fresh eye, targeted
c. Posts a focused response (not a full re-enrichment)
d. Changes label:
   - Human feedback → enriching → enriched (human gate as usual)
   - Dev escalation (`@architect-needed:`) + context clear → enriching → to-dev (no gate)
   - Dev escalation + human decision required → enriching → to-enrich (waits for human)
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

### 4. Copilot review workflow (dev)

Skip if ROLE = "chief-builder".

**Detects**: `copilot-review-pending` label + no assignee

```bash
# Find the PR for this ticket
PR_NUMBER=$(gh pr list \
  --repo "$OWNER/$REPO" \
  --search "Closes #${TICKET_N}" \
  --state open \
  --json number \
  --jq '.[0].number // empty')

# Fetch latest Copilot review state
REVIEW_STATE=$(gh api repos/$OWNER/$REPO/pulls/$PR_NUMBER/reviews \
  --jq '[.[] | select(.user.login == "copilot-pull-request-reviewer")] | last | .state // "PENDING"')
```

**Decision table:**

| `REVIEW_STATE` | Action |
|----------------|--------|
| `APPROVED` | Remove `copilot-review-pending`, add `to-test` |
| `CHANGES_REQUESTED` | Check iteration count → if ≤ 3: remove `copilot-review-pending`, add `to-dev` (dev picks up in feedback-iteration mode) |
| `CHANGES_REQUESTED` + iteration > 3 | Remove `copilot-review-pending`, add `to-test`, post warning comment |
| `PENDING` / `COMMENTED` / null | Skip — poll again next cycle |

**Iteration count**: count existing "Copilot review requested" log entries on the ticket comments. Each dev session in feedback-iteration mode increments this when it re-requests the review.

```
a. Fetch REVIEW_STATE
b. If APPROVED:
   gh issue edit N --remove-label "copilot-review-pending" --add-label "to-test"
   → human testing gate

c. If CHANGES_REQUESTED + iterations ≤ 3:
   gh issue edit N --remove-label "copilot-review-pending" --add-label "to-dev"
   → dev agent auto-launches (feedback-iteration mode, reads PR review threads)

d. If CHANGES_REQUESTED + iterations > 3:
   gh issue edit N --remove-label "copilot-review-pending" --add-label "to-test"
   gh issue comment N --body "⚠️ Copilot review unresolved after 3 iterations — human review needed.\nPR: <url>"
   → human takes over

e. If PENDING/COMMENTED: skip this cycle
```

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
⏳ Awaiting Copilot review: [tickets in copilot-review-pending, if any]
```

### Loop scheduling — drain then sleep

If LOOP = true, apply the **drain then sleep** logic.

**Startup (once, before the first iteration):**

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
LOOP_PID=$$
LOOP_FILE="${REPO_ROOT}/.locks/loop-${ROLE}-${LOOP_PID}.json"
STOP_FILE="${REPO_ROOT}/.locks/loop-${ROLE}-${LOOP_PID}.stop"

python3 - <<PYEOF
import json, time
from pathlib import Path
Path("${REPO_ROOT}/.locks").mkdir(exist_ok=True)
Path("${LOOP_FILE}").write_text(json.dumps({
    "pid": ${LOOP_PID},
    "role": "${ROLE}",
    "interval": ${INTERVAL},
    "started_at": time.time(),
    "last_heartbeat_ts": time.time(),
    "current_ticket": None,
    "state": "idle"
}, indent=2))
PYEOF
```

**Start of each iteration:**

1. Update `last_heartbeat_ts` in `$LOOP_FILE`
2. Check if `$STOP_FILE` exists:
```bash
if [ -f "$STOP_FILE" ]; then
  rm -f "$LOOP_FILE" "$STOP_FILE"
  echo "🛑 Loop stopped gracefully (role: ${ROLE}, pid: ${LOOP_PID})"
  exit 0
fi
```

**Before spawning an agent** — update `$LOOP_FILE`:
```python
{ "current_ticket": N, "state": "waiting_agent" }
```

**Drain-then-sleep logic:**
```
ANY_PROCESSED = (at least one ticket was processed in this run)

If ANY_PROCESSED = true:
  → update LOOP_FILE: { "current_ticket": null, "state": "idle" }
  → loop immediately (no sleep)
  → Output: "🔁 Ticket processed — immediate re-poll"

If ANY_PROCESSED = false (queue empty):
  → update LOOP_FILE: { "state": "idle" }
  → sleep INTERVAL minutes
  → Output: "💤 Queue empty — next poll in {INTERVAL}min"
```

**Principle**: drain the queue as long as there is work, sleep only when idle.

**Graceful exit (stop signal or fatal error):**
```bash
rm -f "$LOOP_FILE" "$STOP_FILE"
```

**Logging:**
```bash
RUN_ID=$(date -u +"%Y%m%d_%H%M%S")_loop
python3 lib/logger.py "$RUN_ID" "worker" "null" "worker_start" "ok" "loop iteration" \
  "{\"role\":\"${ROLE}\",\"interval\":${INTERVAL},\"any_processed\":${ANY_PROCESSED}}"
```

**Output at end of each iteration:**
```
⏱️  Next run: [immediate | in {INTERVAL}min] (loop pid: {LOOP_PID})
   Stop with: /cao-cancel-loop [role]
```

## Example sessions

**One-shot, all roles:**
```
/cao-process-tickets
→ Enriches #5, implements #3, merges #1
→ Done.
```

**Loop — multiple tickets waiting (drain):**
```
/cao-process-tickets --loop
→ 🔄 Loop mode — role: all, interval: 5min (pid: 1234)

iter 1: processes #5 (to-enrich) → ✅ Processed: #5 → 🔁 immediate re-poll
iter 2: processes #3 (to-dev)    → ✅ Processed: #3 → 🔁 immediate re-poll
iter 3: processes #1 (godeploy)  → ✅ Processed: #1 → 🔁 immediate re-poll
iter 4: nothing                  → 💤 queue empty → ⏱️ next poll in 5min
```

**Loop — empty queue at startup:**
```
/cao-process-tickets --loop
→ 🔄 Loop mode — role: all, interval: 5min (pid: 1234)
→ Nothing to process
→ 💤 queue empty — ⏱️ next poll in 5min
```

**Loop — custom interval:**
```
/cao-process-tickets dev --loop --interval 10
→ 🔄 Loop mode — role: dev, interval: 10min (pid: 5678)
→ Nothing to process
→ 💤 queue empty — ⏱️ next poll in 10min
```

**Loop — graceful stop:**
```
[Terminal B] /cao-cancel-loop
→ ✅ Stop signal sent to loop all (pid: 1234)
→    The loop will stop after the current ticket finishes.

[Terminal A, after current ticket done]
→ 🛑 Loop stopped gracefully (role: all, pid: 1234)
```

## Implementation notes

- Each run is atomic (one ticket processed per state)
- Locked states (enriching, dev-in-progress) prevent collisions between roles running in parallel
- GitHub operations use `gh` CLI; GitHub MCP for `search_code` and CI `actions_*`
- Git operations (checkout, commit, push) remain bash
- OWNER/REPO auto-detected from git remote
