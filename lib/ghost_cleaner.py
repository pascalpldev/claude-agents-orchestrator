"""
Ghost claim cleanup for abandoned or stalled tickets.

Detects ghost claims (dead/crashed agents) via heartbeat timeout
and recovers tickets for re-processing.
"""

from pathlib import Path
from typing import Optional
import subprocess

from github_notifier import (
    remove_labels_with_retry,
    add_labels_with_retry,
    post_comment,
)


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
