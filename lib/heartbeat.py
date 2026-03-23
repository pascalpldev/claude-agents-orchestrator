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
from typing import Dict, Optional, Tuple


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
        ValueError: If lock file is corrupted/invalid JSON.
    """
    if not lock_path.exists():
        raise FileNotFoundError(f"Lock file not found: {lock_path}")

    try:
        data = json.loads(lock_path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Corrupted lock file {lock_path}: {e}") from e

    if "last_heartbeat" not in data:
        raise ValueError(f"Invalid lock file {lock_path}: missing 'last_heartbeat' field")

    data["last_heartbeat"] = datetime.now().timestamp()
    lock_path.write_text(json.dumps(data, indent=2))


def is_ghost_claim(
    lock_path: Path,
    timeout_seconds: int = 1200,
    cache: Optional[Dict] = None
) -> bool:
    """
    Check if claim is stale, with optional mtime caching for performance.

    For bulk operations on multiple lock files, pass a cache dict to avoid
    re-parsing JSON files that haven't changed:
        cache = {}
        for lock_file in locks_dir.glob("*.lock"):
            is_ghost_claim(lock_file, timeout_seconds, cache)

    Args:
        lock_path: Path to the lock file to check.
        timeout_seconds: Ghost timeout (default 1200 = 20 min).
        cache: Optional dict to cache {lock_path: (mtime, is_ghost)} for batch operations.

    Returns:
        True if lock file hasn't been heartbeated in longer than timeout_seconds,
        False if file doesn't exist or heartbeat is fresh.
    """
    if not lock_path.exists():
        return False

    # Check cache if provided
    if cache is not None and lock_path in cache:
        cached_mtime, cached_result = cache[lock_path]
        if lock_path.stat().st_mtime == cached_mtime:
            return cached_result

    # Read and check
    data = json.loads(lock_path.read_text())
    last_heartbeat = data["last_heartbeat"]
    now = datetime.now().timestamp()
    is_ghost = (now - last_heartbeat) > timeout_seconds

    # Cache if provided
    if cache is not None:
        cache[lock_path] = (lock_path.stat().st_mtime, is_ghost)

    return is_ghost


def check_all_ghost_claims(
    locks_dir: Path,
    timeout_seconds: int = 1200
) -> Dict[Path, bool]:
    """
    Efficiently check multiple lock files for ghost claims using caching.

    Uses mtime-based caching to avoid re-parsing JSON for unchanged files.

    Args:
        locks_dir: Directory containing .lock files to check.
        timeout_seconds: Ghost timeout (default 1200 = 20 min).

    Returns:
        Dict mapping lock file paths to ghost status (True = stale, False = fresh).
    """
    cache: Dict[Path, Tuple[float, bool]] = {}
    results: Dict[Path, bool] = {}

    if not locks_dir.exists():
        return results

    for lock_file in locks_dir.glob("*.lock"):
        results[lock_file] = is_ghost_claim(lock_file, timeout_seconds, cache)

    return results


def delete_lock_file(lock_path: Path) -> None:
    """
    Delete .lock file (call after PR created or ghost cleaned).

    Args:
        lock_path: Path to the lock file to delete.

    Does nothing if file doesn't exist.
    """
    if lock_path.exists():
        lock_path.unlink()
