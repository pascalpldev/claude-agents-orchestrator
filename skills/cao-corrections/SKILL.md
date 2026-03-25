---
name: cao-corrections
description: |
  Manage behavioral corrections for CAO agents.
  Corrections are rules learned from user feedback, stored in SQLite and
  loaded at agent startup. They can be activated, deactivated, or promoted
  to core behavior files.

  Usage:
  - /cao-corrections list                       → active corrections (project + global)
  - /cao-corrections list --all                 → all statuses
  - /cao-corrections list --agent dev           → filter by agent
  - /cao-corrections list --status pending_integration
  - /cao-corrections deactivate <id>            → active → inactive
  - /cao-corrections activate <id>              → inactive → active
  - /cao-corrections status <id>                → full detail for one correction
  - /cao-corrections promote <id>               → analyze + propose integration into core file
  - /cao-corrections add --agent X --rule "..." --gap "..." --class Y
argument-hint: "[list|deactivate|activate|status|promote|add] [options]"
allowed-tools: [Read, Glob, Grep, Bash, Edit, Write]
---

# /cao-corrections — Behavioral corrections lifecycle manager

## Parse arguments

```
SUBCMD = first token in $ARGUMENTS
ARGS   = remaining tokens
```

## Context

```bash
PROJECT_SLUG=$(pwd | tr '/' '-')
PROJECT_DB="$HOME/.claude/projects/${PROJECT_SLUG}/cao.db"
GLOBAL_DB="$HOME/.claude/cao.db"
```

## Subcommands

### list

```bash
# Build flags
STATUS_FLAG=""
AGENT_FLAG=""
for token in $ARGS; do
  case "$token" in
    --all)   STATUS_FLAG="" ;;          # no filter → all statuses
    --agent) NEXT_IS_AGENT=1 ;;
    --status) NEXT_IS_STATUS=1 ;;
    *)
      [ "$NEXT_IS_AGENT" = "1" ]  && AGENT_FLAG="$token" && NEXT_IS_AGENT=""
      [ "$NEXT_IS_STATUS" = "1" ] && STATUS_FLAG="$token" && NEXT_IS_STATUS=""
      ;;
  esac
done

# Default: active only
[ -z "$STATUS_FLAG" ] && STATUS_FLAG="active"
```

Display two sections:

**Project corrections** — from `$PROJECT_DB` filtered by `$STATUS_FLAG` and `$AGENT_FLAG`
**Global corrections** — from `$GLOBAL_DB` filtered by `$STATUS_FLAG` and `$AGENT_FLAG`

Format each correction as:
```
#<id>  [<class>]  <agent>  [<status>]
  Rule: <rule>
  Gap:  <gap>
  Source: <source>
```

### deactivate / activate

```bash
ID=$(echo "$ARGS" | awk '{print $1}')

# Try project DB first, then global
if python3 lib/corrections.py update "$ID" --status inactive --db "$PROJECT_DB" 2>/dev/null; then
  echo "Deactivated: $ID"
elif python3 lib/corrections.py update "$ID" --status inactive --db "$GLOBAL_DB" 2>/dev/null; then
  echo "Deactivated: $ID"
else
  echo "Error: correction $ID not found in project or global DB"
fi
```

(Same pattern for `activate` with `--status active`.)

### status

Display full JSON for one correction:

```bash
ID=$(echo "$ARGS" | awk '{print $1}')
python3 lib/corrections.py get "$ID" --db "$PROJECT_DB" \
  || python3 lib/corrections.py get "$ID" --db "$GLOBAL_DB" \
  || echo "Not found: $ID"
```

### add

Pass flags directly to `corrections.py add`:

```bash
python3 lib/corrections.py add \
  --project-slug "$(basename $(pwd))" \
  --db "$PROJECT_DB" \
  $ARGS
```

### promote

`promote <id>` triggers an agent analysis session:

1. Load the correction via `corrections.py get`
2. Resolve target file (from `target_hint` or `class`+`agent` table):
   - `general` + `*` → `agents/behaviors/` — ask which file or propose new one
   - `general` + `chief-builder` → `agents/positions/chief-builder/agent.md`
   - `general` + `dev` → `agents/positions/chief-builder/personas/dev.md`
   - `project-pattern` + `chief-builder` → `agents/positions/chief-builder/agent.md`
   - `project-pattern` + `dev` → `agents/positions/chief-builder/personas/dev.md`
3. Read target file in full
4. Check for conflicts, redundancy, and contradictions with existing content
5. Propose exact diff — show the specific lines to add/modify
6. Wait for user confirmation before writing
7. On confirmation: write file, `git add`, `git commit -m "feat: integrate correction #<id> into <file>"`
8. Update correction:
   ```bash
   COMMIT_SHA=$(git rev-parse HEAD)
   python3 lib/corrections.py update "$ID" \
     --status integrated \
     --integrated-commit "$COMMIT_SHA" \
     --integrated-file "<target_file_path>" \
     --db "$PROJECT_DB_OR_GLOBAL_DB"
   ```

**Never write to files without explicit user confirmation.**
