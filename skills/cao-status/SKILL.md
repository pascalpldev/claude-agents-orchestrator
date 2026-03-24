---
name: cao-status
description: |
  Instant project state snapshot — active tickets, running agents, latest logs.

  Usage:
  - /cao-status            → full view
  - /cao-status --tickets  → GitHub tickets only (labels)
  - /cao-status --agents   → active agents (.lock files) only
  - /cao-status --logs     → latest log events
argument-hint: "[--tickets|--agents|--logs]"
allowed-tools: [Read, Glob, Grep, Bash]
---

# /cao-status — State snapshot

Gives an instant view of what is happening: tickets in progress, active agents, latest activity.

## Parse arguments

```
MODE = "all"
For each token in $ARGUMENTS:
  "--tickets" → MODE = "tickets"
  "--agents"  → MODE = "agents"
  "--logs"    → MODE = "logs"
```

## Context

```bash
REMOTE=$(git remote get-url origin 2>/dev/null)
OWNER=$(echo "$REMOTE" | sed 's|.*github\.com[:/]||' | cut -d'/' -f1)
REPO=$(echo "$REMOTE" | sed 's|.*github\.com[:/]||' | cut -d'/' -f2 | sed 's|\.git$||')
REPO_ROOT=$(git rev-parse --show-toplevel)
```

## Section 1 — Active tickets (if MODE = all | tickets)

Fetch all open tickets with an active workflow label:

```bash
gh issue list --repo "$OWNER/$REPO" --state open \
  --json number,title,labels,assignees,updatedAt \
  --limit 50
```

Filter and display by state:

```
## Tickets in progress

| # | Title | State | Assigned | Updated |
|---|-------|-------|----------|---------|
| #N | ... | enriching | — | 3min ago |
| #N | ... | dev-in-progress | @user | 12min ago |

## Waiting

| # | Title | State |
|---|-------|-------|
| #N | ... | to-enrich |
| #N | ... | to-dev |
| #N | ... | to-test |

## Recently completed (deployed)
[last 3 deployed tickets, with date]
```

Tickets without a workflow label → ignore.

## Section 2 — Active agents (if MODE = all | agents)

Read `.lock` files in `.locks/`:

```bash
ls "$REPO_ROOT/.locks/"*.lock 2>/dev/null || echo "(no active agents)"
```

For each `.lock` file found, display:

```bash
python3 - <<'EOF'
import json, time, glob, os
from datetime import datetime
from pathlib import Path

locks_dir = Path(os.environ.get('REPO_ROOT', '.')) / '.locks'
now = time.time()

locks = list(locks_dir.glob('*.lock')) if locks_dir.exists() else []
if not locks:
    print("No active agents (.locks/ empty or missing)")
else:
    print(f"{'Ticket':<10} {'Agent':<20} {'Since':<12} {'Phase':<25} {'Milestones':<10} {'State'}")
    print("-" * 90)
    for lock_file in sorted(locks):
        try:
            d = json.loads(lock_file.read_text())
            elapsed = int(now - d['claimed_at'])
            hb_age = int(now - d['last_heartbeat'])
            mins = elapsed // 60
            phase = d.get('current_phase', '—')
            milestones = d.get('milestone_count', 0)
            # Ghost if heartbeat > 20min
            state = '⚠️  GHOST?' if hb_age > 1200 else '✅ active'
            ticket = lock_file.stem.replace('ticket-', '#')
            agent = d.get('agent', '?')[:18]
            print(f"{ticket:<10} {agent:<20} {mins:>3}min{'':<7} {phase:<25} {milestones:<10} {state}")
        except Exception as e:
            print(f"{lock_file.name}: read error ({e})")
EOF
```

## Section 3 — Latest logs (if MODE = all | logs)

```bash
LOG_DIR="$HOME/.claude/projects/logs/${OWNER}-${REPO}"
LOG_FILE=$(ls "$LOG_DIR"/*.jsonl 2>/dev/null | sort | tail -1)

if [ -z "$LOG_FILE" ]; then
  echo "No logs found in $LOG_DIR"
else
  # Last 20 events, formatted
  python3 - <<'PYEOF'
import json, sys
from pathlib import Path

log_file = Path(sys.argv[1])
lines = log_file.read_text().strip().split('\n')[-20:]

print(f"{'Time':<10} {'Agent':<14} {'Ticket':<8} {'Phase':<22} {'Status':<8} Message")
print("-" * 85)
for line in lines:
    try:
        e = json.loads(line)
        ts = e['ts'][11:19]  # HH:MM:SS
        agent = (e.get('agent') or '?')[:12]
        ticket = f"#{e['ticket']}" if e.get('ticket') else '—'
        phase = (e.get('phase') or '?')[:20]
        status = e.get('status', '?')[:7]
        msg = e.get('msg', '')[:40]
        icon = '✅' if status in ('ok','success','started') else '❌'
        print(f"{ts:<10} {agent:<14} {ticket:<8} {phase:<22} {icon} {status:<6} {msg}")
    except Exception:
        pass
PYEOF
  "$LOG_FILE"
fi
```

## Final output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CAO Status — {OWNER}/{REPO}
 {DATE} {TIME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Section 1 — Tickets]

[Section 2 — Active agents]

[Section 3 — Latest logs]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If all sections are empty: display `✅ Nothing in progress — project at rest.`
