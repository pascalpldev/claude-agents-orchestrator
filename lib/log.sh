#!/usr/bin/env bash
# lib/log.sh — Append a JSONL log entry for an agent phase.
#
# Usage:
#   bash lib/log.sh RUN_ID AGENT TICKET PHASE STATUS "message" '{"key":"val"}'
#
# Arguments:
#   RUN_ID   — unique run identifier (e.g. 20260321_142301_tl_5)
#   AGENT    — "team-lead" or "dev"
#   TICKET   — numeric ticket number (e.g. 5)
#   PHASE    — phase name (start, context_loaded, analysis_complete, ...)
#   STATUS   — "started" | "ok" | "warning" | "error" | "success"
#   message  — human-readable description
#   data     — optional JSON object, defaults to {}
#
# Log location: ~/.claude/projects/logs/<project>/<YYYY-MM-DD>.jsonl
#
# THIS SCRIPT MUST NEVER FAIL VISIBLY.
# All errors are silenced — a log failure never blocks the agent.

RUN_ID="${1:-}"
AGENT="${2:-}"
TICKET="${3:-0}"
PHASE="${4:-}"
STATUS="${5:-ok}"
MSG="${6:-}"
DATA="${7}"
[[ -z "$DATA" ]] && DATA='{}'

# Derive project slug from git remote (silent on failure)
PROJECT="unknown"
REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
if [[ -n "$REMOTE_URL" ]]; then
  PROJECT=$(echo "$REMOTE_URL" \
    | sed 's|^.*github\.com[:/]||' \
    | sed 's|\.git$||' \
    | sed 's|/|-|g')
fi

# Build log path
LOG_DIR="${HOME}/.claude/projects/logs/${PROJECT}"
DATE=$(date -u +"%Y-%m-%d" 2>/dev/null || echo "unknown")
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || echo "unknown")
LOG_FILE="${LOG_DIR}/${DATE}.jsonl"

# JSON-escape a string value
escape_json() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\t'/\\t}"
  printf '%s' "$s"
}
MSG_ESC=$(escape_json "$MSG")

# Write via python3 (avoids bash braceexpand issues with JSON strings)
(
  mkdir -p "$LOG_DIR" 2>/dev/null
  python3 - "$TS" "$RUN_ID" "$PROJECT" "$AGENT" "$TICKET" "$PHASE" "$STATUS" "$MSG_ESC" "$DATA" "$LOG_FILE" << 'PYEOF' 2>/dev/null
import sys, json
ts, run_id, project, agent, ticket, phase, status, msg, data_str, log_file = sys.argv[1:]
try:
    data = json.loads(data_str)
except Exception:
    data = {"raw": data_str}
entry = {"ts": ts, "run_id": run_id, "project": project, "agent": agent,
         "ticket": int(ticket) if ticket.isdigit() else ticket,
         "phase": phase, "status": status, "msg": msg, "data": data}
with open(log_file, "a") as f:
    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
PYEOF
) 2>/dev/null || true
