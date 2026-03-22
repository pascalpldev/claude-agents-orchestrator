"""
Heartbeat manager for ghost claim detection.

Agents create .lock files to claim tickets and periodically update
a heartbeat timestamp. If the heartbeat isn't updated within a
timeout window (default 20 minutes), the claim is considered "ghost"
(agent dead/crashed) and the claim can be reclaimed.
"""

import json
from datetime import datetime
from pathlib import Path


def create_lock_file(lock_path: Path, agent_name: str) -> None:
    """
    Create .lock file with agent metadata.

    Args:
        lock_path: Path to the lock file to create.
        agent_name: Name of the agent claiming the ticket.

    Creates parent directories if they don't exist.
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now().timestamp()
    data = {
        "agent": agent_name,
        "claimed_at": now,
        "last_heartbeat": now
    }
    lock_path.write_text(json.dumps(data, indent=2))


def update_heartbeat(lock_path: Path) -> None:
    """
    Update last_heartbeat timestamp without changing claimed_at.

    Args:
        lock_path: Path to the lock file to update.

    Raises:
        FileNotFoundError: If lock file does not exist.
    """
    if not lock_path.exists():
        raise FileNotFoundError(f"Lock file not found: {lock_path}")
    data = json.loads(lock_path.read_text())
    data["last_heartbeat"] = datetime.now().timestamp()
    lock_path.write_text(json.dumps(data, indent=2))


def is_ghost_claim(lock_path: Path, timeout_seconds: int = 1200) -> bool:
    """
    Check if claim is stale (agent dead/crashed).

    Args:
        lock_path: Path to the lock file to check.
        timeout_seconds: Timeout threshold in seconds (default: 1200 = 20 min).

    Returns:
        True if lock file hasn't been heartbeated in longer than timeout_seconds,
        False if file doesn't exist or heartbeat is fresh.
    """
    if not lock_path.exists():
        return False
    data = json.loads(lock_path.read_text())
    last_heartbeat = data["last_heartbeat"]
    now = datetime.now().timestamp()
    return (now - last_heartbeat) > timeout_seconds


def delete_lock_file(lock_path: Path) -> None:
    """
    Delete .lock file (call after PR created or ghost cleaned).

    Args:
        lock_path: Path to the lock file to delete.

    Does nothing if file doesn't exist.
    """
    if lock_path.exists():
        lock_path.unlink()
