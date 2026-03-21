---
name: show-logs
description: |
  Read and display agent run logs for the current project.

  Shows JSONL log entries written by team-lead and dev agents at each phase.
  Useful for tracking what agents did, how long they took, and diagnosing errors.

  Usage:
    /show-logs                    — today's runs, grouped by ticket
    /show-logs --last 10          — last 10 log entries across all tickets
    /show-logs --ticket 12        — full history for ticket #12
    /show-logs --agent team-lead  — runs by team-lead only
    /show-logs --errors           — only runs with error events
argument-hint: "[--errors] [--ticket N] [--last N] [--agent team-lead|dev]"
allowed-tools: [Bash, Read]
---

# /show-logs — Display agent run logs

## What it does

1. Detect the current project from `git remote get-url origin`
2. Locate logs at `~/.claude/projects/logs/<project-slug>/`
3. Parse JSONL entries and display as a human-readable markdown table
4. Apply filters from `$ARGUMENTS`

## Step 1 — Resolve project and log directory

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null)
PROJECT=$(echo "$REMOTE_URL" \
  | sed 's|^.*github\.com[:/]||' \
  | sed 's|\.git$||' \
  | sed 's|/|-|g')
LOG_DIR="${HOME}/.claude/projects/logs/${PROJECT}"
TODAY=$(date -u +"%Y-%m-%d")
```

If `LOG_DIR` does not exist or has no `.jsonl` files: print `No logs found for <project>. Have you run any agents?` and stop.

## Step 2 — Collect and filter entries

Use `python3` to parse, filter, and sort entries. If `python3` is unavailable, fall back to `cat` of the raw JSONL with a note.

```python
import sys, json, os, glob

log_dir = sys.argv[1]
args = sys.argv[2] if len(sys.argv) > 2 else ""

# Collect all .jsonl files (sorted by date)
files = sorted(glob.glob(os.path.join(log_dir, "*.jsonl")))
if "--last" not in args and "--errors" not in args and "--ticket" not in args and "--agent" not in args:
    # Default: today only
    today = __import__('datetime').date.today().isoformat()
    files = [f for f in files if today in f]

entries = []
for path in files:
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except:
                        pass

entries.sort(key=lambda x: x.get("ts", ""))

# Apply filters
if "--errors" in args:
    entries = [e for e in entries if e.get("status") == "error"]

if "--ticket" in args:
    import re
    m = re.search(r'--ticket\s+(\d+)', args)
    if m:
        n = int(m.group(1))
        entries = [e for e in entries if e.get("ticket") == n]

if "--agent" in args:
    import re
    m = re.search(r'--agent\s+(\S+)', args)
    if m:
        ag = m.group(1)
        entries = [e for e in entries if e.get("agent") == ag]

if "--last" in args:
    import re
    m = re.search(r'--last\s+(\d+)', args)
    if m:
        n = int(m.group(1))
        entries = entries[-n:]

for e in entries:
    print(json.dumps(e))
```

## Step 3 — Render as markdown

Group entries by `run_id`, then by `ticket`. For each group, compute duration (time between `start` and `end` phases).

**Display format:**

```
=== Logs: <project> — <date range> ===

## Ticket #5 — "Feature: User auth"
Run 20260321_142301_tl_5 | team-lead | 14:23:01

| Phase             | Status  | Durée | Message                            |
|-------------------|---------|-------|------------------------------------|
| start             | started |       | ticket #5 — Feature: User auth     |
| context_loaded    | ok      | +4s   | 4 fichiers lus                     |
| analysis_complete | ok      | +12s  | 2 risques, complexity=M            |
| plan_posted       | ok      | +26s  | comment #123                       |
| label_updated     | ok      | +27s  | enriching → enriched               |
| end               | success | 47s   |                                    |

Run 20260321_151000_dev_5 | dev | 15:10:00

| Phase            | Status  | Durée | Message                            |
|------------------|---------|-------|------------------------------------|
| start            | started |       | ticket #5 — plan loaded            |
| context_loaded   | ok      | +2s   |                                    |
| branch_created   | ok      | +4s   | feat/ticket-5-user-auth            |
| implement_start  | ok      | +4s   | 6 todos                            |
| implement_complete| ok     | +90s  |                                    |
| tests_written    | ok      | +105s | unit, integration                  |
| self_review      | ok      | +110s | 1 issue found and fixed            |
| pushed           | ok      | +112s |                                    |
| pr_created       | ok      | +114s | https://github.com/...             |
| docs_updated     | ok      | +115s | claude_md=false                    |
| label_updated    | ok      | +116s | dev-in-progress → to-test          |
| end              | success | 116s  |                                    |

---

=== Résumé ===
Runs : 2  |  Tickets : 1  |  Erreurs : 0
Durée moy. team-lead : 47s  |  Durée moy. dev : 116s
```

**For `--errors` mode**, highlight errors prominently:

```
=== ERRORS — <project> ===

❌ Ticket #7 | dev | 2026-03-21 15:30:01
   Phase : push
   Message : push failed
   Data : {"phase":"push"}
```

## Display rules

- Group by ticket number (ascending), then by run timestamp within each group
- Show only `HH:MM:SS` portion of timestamp in the timeline
- `Durée` column: `+Ns` offset from run start, or total seconds on the `end` row
- Flatten `data` JSON to `key=value` pairs (truncate at 60 chars) for the Message column
- If no entries match the filter: print `No entries found for the given filter.`
- If `python3` unavailable: `cat ${LOG_DIR}/*.jsonl 2>/dev/null || echo "No logs."` + note to install python3
