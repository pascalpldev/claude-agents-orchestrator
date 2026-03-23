"""
GitHub notifier with retry logic for label and comment operations.

Provides resilient GitHub CLI wrapper with 3-attempt retry mechanism
for handling transient failures (rate limits, network errors, etc.).
"""

import time
import subprocess
from typing import List


def run_gh_cli(args: List[str]) -> str:
    """
    Run gh CLI command, raise Exception on failure.

    Args:
        args: List of arguments to pass to gh CLI (not including 'gh' prefix).

    Returns:
        stdout output from the gh command.

    Raises:
        Exception: If gh command exits with non-zero status.
    """
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise Exception(f"gh command failed: {result.stderr}")
    return result.stdout


def remove_labels_with_retry(
    repo: str,
    issue_number: int,
    labels: List[str],
    max_retries: int = 3,
    retry_delay: int = 5
) -> None:
    """
    Remove labels from issue with retry logic.

    Attempts to remove each label, retrying up to max_retries times
    if transient errors occur.

    Args:
        repo: Repository in format "owner/repo".
        issue_number: Issue number to remove labels from.
        labels: List of label names to remove.
        max_retries: Maximum number of retry attempts (default 3).
        retry_delay: Delay in seconds between retries (default 5).

    Raises:
        Exception: If all retry attempts fail.
    """
    if not labels:
        return

    for attempt in range(max_retries):
        try:
            for label in labels:
                run_gh_cli([
                    "issue", "edit", str(issue_number),
                    f"--repo={repo}",
                    f"--remove-label={label}"
                ])
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to remove labels after {max_retries} retries: {e}")
            time.sleep(retry_delay)


def add_labels_with_retry(
    repo: str,
    issue_number: int,
    labels: List[str],
    max_retries: int = 3,
    retry_delay: int = 5
) -> None:
    """
    Add labels to issue with retry logic.

    Attempts to add each label, retrying up to max_retries times
    if transient errors occur.

    Args:
        repo: Repository in format "owner/repo".
        issue_number: Issue number to add labels to.
        labels: List of label names to add.
        max_retries: Maximum number of retry attempts (default 3).
        retry_delay: Delay in seconds between retries (default 5).

    Raises:
        Exception: If all retry attempts fail.
    """
    if not labels:
        return

    for attempt in range(max_retries):
        try:
            for label in labels:
                run_gh_cli([
                    "issue", "edit", str(issue_number),
                    f"--repo={repo}",
                    f"--add-label={label}"
                ])
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to add labels after {max_retries} retries: {e}")
            time.sleep(retry_delay)


def post_comment(
    repo: str,
    issue_number: int,
    body: str,
    max_retries: int = 3
) -> None:
    """
    Post comment to issue with retry logic.

    Attempts to post a comment, retrying up to max_retries times
    if transient errors occur.

    Args:
        repo: Repository in format "owner/repo".
        issue_number: Issue number to comment on.
        body: Comment body text.
        max_retries: Maximum number of retry attempts (default 3).

    Raises:
        Exception: If all retry attempts fail.
    """
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            run_gh_cli([
                "issue", "comment", str(issue_number),
                f"--repo={repo}",
                f"--body={body}"
            ])
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to post comment after {max_retries} retries: {e}")
            time.sleep(retry_delay)


def cleanup_labels_after_pr(
    repo: str,
    issue_number: int,
    agent_name: str
) -> None:
    """
    Clean up labels after PR creation.

    Performs the following operations:
    1. Remove: dev-in-progress, agent/{agent_name}
    2. Add: to-test
    3. Post: success comment

    Args:
        repo: Repository in format "owner/repo".
        issue_number: Issue number to clean up.
        agent_name: Name of the agent (used in agent/{name} label).

    Raises:
        Exception: If any operation fails after retries.
    """
    # Remove dev-in-progress and agent/{agent_name}
    remove_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["dev-in-progress", f"agent/{agent_name}"]
    )

    # Add to-test label
    add_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["to-test"]
    )

    # Post success comment
    post_comment(
        repo=repo,
        issue_number=issue_number,
        body="✅ PR ready for testing"
    )
