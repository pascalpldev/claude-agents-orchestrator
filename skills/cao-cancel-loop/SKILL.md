---
name: cao-cancel-loop
description: |
  Cancel an active cao-process-tickets loop.
  Writes a stop signal file that the loop detects at the start of its next iteration,
  after the current ticket finishes. Graceful — never interrupts a running agent.
argument-hint: "[chief-builder|dev|all]"
allowed-tools: [Bash]
---

# /cao-cancel-loop — Cancel an active loop

Stops the loop polling started by `/cao-process-tickets --loop`.
Graceful: the current ticket always finishes before the loop exits.

## What it does

Parse `$ARGUMENTS`:
- No argument or `all` → match all `loop-*.json` files
- `chief-builder`       → match `loop-chief-builder-*.json`
- `dev`                 → match `loop-dev-*.json`

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
LOCKS="${REPO_ROOT}/.locks"

# Determine glob pattern
case "${ARGUMENTS:-all}" in
  chief-builder) PATTERN="loop-chief-builder-*.json" ;;
  dev)           PATTERN="loop-dev-*.json" ;;
  *)             PATTERN="loop-*.json" ;;
esac

FOUND=0
for f in ${LOCKS}/${PATTERN}; do
  [ -f "$f" ] || continue
  FOUND=1

  PID=$(python3 -c "import json; print(json.load(open('$f'))['pid'])" 2>/dev/null)
  ROLE=$(python3 -c "import json; print(json.load(open('$f'))['role'])" 2>/dev/null)

  # Verify PID is alive
  if ! kill -0 "$PID" 2>/dev/null; then
    echo "⚠️  Loop pid $PID is already dead — cleaning up"
    rm -f "$f"
    continue
  fi

  # Write stop signal (same name, .stop extension)
  STOP="${f%.json}.stop"
  touch "$STOP"
  echo "✅ Stop signal sent to loop ${ROLE} (pid: ${PID})"
  echo "   The loop will stop after the current ticket finishes."
done

if [ "$FOUND" -eq 0 ]; then
  echo "ℹ️  No active cao loop found for role: ${ARGUMENTS:-all}"
fi
```
