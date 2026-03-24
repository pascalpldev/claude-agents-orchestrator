#!/usr/bin/env python3
"""
Background heartbeat process for agent lock files.

Launched by the dev agent at startup as an orphaned background process.
Monitors the Claude Code process ($PPID) every INTERVAL seconds and updates
last_heartbeat_ts in the .lock file while Claude Code is alive.

When Claude Code dies (SIGKILL, crash, terminal close), this process stops
updating the heartbeat. Ghost buster detects the stale heartbeat and cleans
up the ticket on the next run.

This process intentionally does NO cleanup on its own — cleanup is the ghost
buster's responsibility. This keeps the process minimal and side-effect-free.

Usage:
    python3 lib/heartbeat_process.py <lock_path> <claude_pid> [interval_seconds]

Args:
    lock_path:        Path to the .lock file to update.
    claude_pid:       PID of the Claude Code process ($PPID from bash).
    interval_seconds: How often to update heartbeat in seconds (default: 30).
"""

import json
import os
import sys
import time
from pathlib import Path


def run(lock_path: Path, claude_pid: int, interval: int) -> None:
    while True:
        time.sleep(interval)

        # Check if Claude Code is still alive via signal 0 (existence check only).
        # os.kill(pid, 0) raises ProcessLookupError if PID is gone,
        # PermissionError if PID exists but belongs to another user (still alive).
        try:
            os.kill(claude_pid, 0)
        except ProcessLookupError:
            # Claude Code is dead — stop updating heartbeat.
            # Ghost buster will detect the stale timestamp and handle cleanup.
            break
        except PermissionError:
            # Process exists, different user — treat as alive.
            pass

        try:
            data = json.loads(lock_path.read_text())
            data["last_heartbeat_ts"] = time.time()
            lock_path.write_text(json.dumps(data, indent=2))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            # Lock file gone (normal cleanup by the agent) — exit cleanly.
            break


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            f"Usage: {sys.argv[0]} <lock_path> <claude_pid> [interval_seconds]",
            file=sys.stderr,
        )
        sys.exit(1)

    _lock_path = Path(sys.argv[1])
    _claude_pid = int(sys.argv[2])
    _interval = int(sys.argv[3]) if len(sys.argv) > 3 else 30

    run(_lock_path, _claude_pid, _interval)
