#!/usr/bin/env python3
"""
lib/logger.py — Canonical JSONL logging for CAO agents and workers.

Dual interface:
  CLI:    python3 lib/logger.py RUN_ID AGENT TICKET PHASE STATUS ["msg"] ['{"key":"val"}']
  Python: from logger import log_event, estimate_cost
"""

import functools
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl
    _FCNTL_AVAILABLE = True
except ImportError:
    _FCNTL_AVAILABLE = False

PRICING = {
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
    "claude-opus-4-6": {"input": 15.0, "output": 75.0},
}


@functools.lru_cache(maxsize=1)
def _get_project_slug():
    """git remote get-url origin -> owner-repo. Returns 'unknown' on failure."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return "unknown"
        url = result.stdout.strip()
        if not url:
            return "unknown"
        # Strip protocol/host prefix: handles both SSH and HTTPS
        # SSH:   git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git
        for prefix in ("https://github.com/", "http://github.com/", "git@github.com:"):
            if url.startswith(prefix):
                url = url[len(prefix):]
                break
        # Remove trailing .git
        if url.endswith(".git"):
            url = url[:-4]
        # Replace remaining slashes with dashes (owner/repo -> owner-repo)
        slug = url.replace("/", "-")
        return slug if slug else "unknown"
    except Exception:
        return "unknown"


def _get_log_path(project):
    """~/.claude/projects/logs/<project>/<YYYY-MM-DD>.jsonl"""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return Path.home() / ".claude" / "projects" / "logs" / project / f"{date_str}.jsonl"


def _normalize_ticket(ticket):
    """Normalize ticket to int or None."""
    if ticket is None:
        return None
    if isinstance(ticket, int):
        return ticket
    s = str(ticket).strip()
    if s.lower() == "null" or s == "":
        return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return s


def log_event(
    run_id,
    agent,
    ticket,
    phase,
    status,
    msg="",
    data=None,
    project=None,
):
    """Append one JSONL entry. NEVER raises."""
    try:
        if project is None:
            project = _get_project_slug()

        if data is None:
            data = {}

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        entry = {
            "ts": ts,
            "run_id": run_id,
            "project": project,
            "agent": agent,
            "ticket": _normalize_ticket(ticket),
            "phase": phase,
            "status": status,
            "msg": msg,
            "data": data,
        }

        log_path = _get_log_path(project)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a", encoding="utf-8") as f:
            if _FCNTL_AVAILABLE:
                fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
            else:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Logging must never block the agent
        pass


def estimate_cost(model, files_read_chars, files_written_chars):
    """Estimate API cost in USD. Returns None for unknown models."""
    pricing = PRICING.get(model)
    if pricing is None:
        return None
    input_tokens = files_read_chars / 4
    output_tokens = files_written_chars / 4
    cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
    return cost


def _main():
    if len(sys.argv) < 6:
        print(
            "Usage: logger.py RUN_ID AGENT TICKET PHASE STATUS [msg] [data_json]",
            file=sys.stderr,
        )
        sys.exit(1)

    run_id = sys.argv[1]
    agent = sys.argv[2]
    ticket_raw = sys.argv[3]
    phase = sys.argv[4]
    status = sys.argv[5]
    msg = sys.argv[6] if len(sys.argv) > 6 else ""
    data_str = sys.argv[7] if len(sys.argv) > 7 else "{}"

    try:
        data = json.loads(data_str)
    except Exception:
        data = {"raw": data_str}

    ticket = _normalize_ticket(ticket_raw)

    log_event(
        run_id=run_id,
        agent=agent,
        ticket=ticket,
        phase=phase,
        status=status,
        msg=msg,
        data=data,
    )


if __name__ == "__main__":
    _main()
