---
name: cao-watch
description: |
  Real-time view of running agents — refreshes automatically without changing the interface.
  Displays: active agents (ticket, duration, phase, last milestone), waiting tickets, recent activity.

  Usage:
  - /cao-watch              → refresh every 30s
  - /cao-watch --interval 10 → refresh every 10s
argument-hint: "[--interval <seconds>]"
allowed-tools: [Bash]
---

# /cao-watch — Real-time view

Runs the watcher continuously in the current terminal. Rewrites in place (no scrolling).

## Parse arguments

```
INTERVAL = 30  # default

For each token in $ARGUMENTS:
  "--interval <n>" → INTERVAL = n
```

## Launch

```bash
_REPO_ROOT="$(git rev-parse --show-toplevel)"

python3 "${_REPO_ROOT}/lib/status_watcher.py" --interval {INTERVAL}
```

The script runs until Ctrl+C. It displays and refreshes in place:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CAO Watch — owner/repo  ⟳ 30s  Ctrl+C to quit
 Last update: 14:32:05
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 ACTIVE AGENTS
────────────────────────────────────────────────────
  #42   proud-falcon         12min   Build — Tests          milestone #3
  #17   swift-eagle           3min   Enrichment             milestone #1

 WAITING
────────────────────────────────────────────────────
  ⏳ to-dev              #38    Fix: Auth timeout
  ⏳ to-enrich           #41    Feature: Dark mode

 RECENT ACTIVITY
────────────────────────────────────────────────────
  14:31:42  dev           #42    milestone           Build — Tests  milestone #3
  14:28:10  chief-builder #17    start               ticket #17 — Feature…
  14:25:00  dev           #42    implement_complete  implementation done

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Next update in 30s…
```

## Notes

- Active agents = read from `.locks/*.lock` (local)
- Tickets = read from GitHub via `gh issue list` (network)
- Logs = read from `~/.claude/projects/logs/<repo>/<date>.jsonl`
- An agent marked `⚠ GHOST?` has not updated its heartbeat in > 20min
- To stop: Ctrl+C in the terminal, or close the Claude Code tab
