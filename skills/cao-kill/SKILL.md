---
name: cao-kill
description: |
  Graceful shutdown of a running agent on a specific ticket.
  The agent detects the signal at its next milestone and resets the ticket to its initial state.

  Usage:
  - /cao-kill #42     → graceful shutdown of the agent working on ticket #42
  - /cao-kill --all   → graceful shutdown of all active agents
argument-hint: "<#N | --all>"
allowed-tools: [Bash]
---

# /cao-kill — Graceful agent shutdown

Drops a sentinel file that the agent detects at its next checkpoint (within 5 minutes at most).
The agent handles its own cleanup: resets the label, posts a comment, removes its lock.

## Parse arguments

```
TICKET = ""
ALL    = false

For each token in $ARGUMENTS:
  "--all"     → ALL = true
  "#<N>" / "<N>" → TICKET = N (strip "#")
```

If neither TICKET nor ALL provided → display help and list active agents.

## Context

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
LOCKS_DIR="${REPO_ROOT}/.locks"
```

## Execution

### Kill a specific ticket

```bash
SENTINEL="${LOCKS_DIR}/kill-ticket-${TICKET}"

if [ ! -f "${LOCKS_DIR}/ticket-${TICKET}.lock" ]; then
  echo "⚠  No active agent on ticket #${TICKET} (.lock missing)"
  echo "   Use /cao-status to see running agents."
  exit 0
fi

touch "$SENTINEL"
echo "✅ Kill signal dropped for ticket #${TICKET}"
echo "   The agent will stop gracefully at its next checkpoint (≤ 5min)."
echo "   Monitor with: /cao-watch"
```

### Kill all agents (--all)

```bash
LOCKS=$(ls "${LOCKS_DIR}"/ticket-*.lock 2>/dev/null)

if [ -z "$LOCKS" ]; then
  echo "No active agents."
  exit 0
fi

COUNT=0
for LOCK in $LOCKS; do
  TICKET_N=$(basename "$LOCK" .lock | sed 's/ticket-//')
  touch "${LOCKS_DIR}/kill-ticket-${TICKET_N}"
  echo "  Signal dropped → ticket #${TICKET_N}"
  COUNT=$((COUNT + 1))
done

echo ""
echo "✅ ${COUNT} kill signal(s) dropped."
echo "   Agents will stop at their next checkpoint (≤ 5min)."
```

## Notes

- The kill is **cooperative**: the agent runs its own cleanup before stopping
  - Resets the ticket to `to-dev` (or `to-enrich` depending on the agent)
  - Posts a GitHub comment
  - Removes its `.lock` file
- If the agent is a ghost (heartbeat > 20min), the sentinel will never be read —
  use `/cao-status` to identify ghosts and manually reset labels
- Maximum delay before shutdown: 5 minutes (interval between two `_milestone_if_due` calls)
