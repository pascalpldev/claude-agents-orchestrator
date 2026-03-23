"""
Ghost claim cleanup for abandoned or stalled tickets.

Detects ghost claims (dead/crashed agents) via heartbeat timeout
and recovers tickets for re-processing.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess

from github_notifier import (
    remove_labels_with_retry,
    add_labels_with_retry,
    post_comment,
)
from logger import log_event


def cleanup_ghost_claim(
    repo: str,
    issue_number: int,
    lock_path: Path,
    delete_branch: bool = False,
    branch_name: Optional[str] = None
) -> None:
    """
    Clean up a ghost claim (stalled agent) on a ticket.

    Performs the following operations:
    1. Remove: dev-in-progress label
    2. Add: to-dev label
    3. Post: notification comment
    4. Delete: lock file
    5. Optionally: delete working branch

    Args:
        repo: Repository in format "owner/repo".
        issue_number: Issue number of the ghost ticket.
        lock_path: Path to the lock file to delete.
        delete_branch: Whether to delete the working branch (default False).
        branch_name: Name of the branch to delete (required if delete_branch=True).

    Raises:
        Exception: If any GitHub operation fails after retries.
        ValueError: If delete_branch=True but branch_name is None.
    """
    if delete_branch and branch_name is None:
        raise ValueError("branch_name must be provided when delete_branch=True")

    # Remove dev-in-progress label
    remove_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["dev-in-progress"]
    )

    # Add to-dev label
    add_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["to-dev"]
    )

    # Post notification comment
    post_comment(
        repo=repo,
        issue_number=issue_number,
        body="🔧 Ghost claim cleaned up: agent stalled. Ticket re-opened for development."
    )

    # Log ghost detection before deleting the lock file
    lock_data = json.loads(lock_path.read_text()) if lock_path.exists() else {}
    last_hb = lock_data.get("last_heartbeat", 0)
    stale_agent = lock_data.get("agent", "unknown")
    age_seconds = int(time.time() - last_hb) if last_hb else 0
    run_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_ghost_{issue_number}"
    log_event(
        run_id, "worker", issue_number, "ghost_detected", "warning",
        f"ghost claim detected on ticket #{issue_number}",
        {"stale_agent": stale_agent, "age_seconds": age_seconds},
    )

    # Delete lock file
    if lock_path.exists():
        lock_path.unlink()

    # Optionally delete the working branch
    if delete_branch and branch_name:
        try:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                capture_output=True,
                text=True,
                check=True
            )
        except Exception:
            # Log but don't fail - branch may already be deleted or other issues
            pass
