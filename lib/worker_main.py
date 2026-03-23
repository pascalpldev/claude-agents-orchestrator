"""
WorkerOrchestrator - Main orchestrator for /cao-worker skill.

Provides the core orchestration logic for polling tickets, claiming, working,
and creating pull requests. This is the final integration point that ties together:
  - Worker (heartbeat-based claim lifecycle)
  - GitHubNotifier (label and comment operations)
  - SchemaValidator (resume safety)
  - AgentNamer (unique agent identification)

Typical usage:

    orchestrator = WorkerOrchestrator(
        agent_name="proud-falcon",
        repo="owner/repo",
        polling_interval=300
    )
    result = orchestrator.run_one_cycle()
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

from worker import Worker
from github_notifier import (
    cleanup_labels_after_pr,
    add_labels_with_retry,
    remove_labels_with_retry,
    post_comment,
    run_gh_cli,
)
from agent_namer import generate_agent_name


class WorkerOrchestrator:
    """
    Main orchestrator for /cao-worker skill.

    Coordinates the complete worker lifecycle:
    1. Poll for "to-dev" labeled tickets
    2. Claim a ticket atomically (branch push to prevent race)
    3. Assign to self
    4. Run work (implementation)
    5. Create PR
    6. Clean up labels + add "to-test"

    Attributes:
        agent_name: Name of the agent (e.g., "proud-falcon")
        repo: Repository in format "owner/repo"
        polling_interval: Seconds between polling cycles (default 300 = 5 min)
        worker: Worker instance for heartbeat lifecycle management
    """

    def __init__(
        self,
        agent_name: Optional[str] = None,
        repo: Optional[str] = None,
        polling_interval: int = 300,
        project_root: Optional[Path] = None,
    ):
        """
        Initialize WorkerOrchestrator.

        Args:
            agent_name: Name of the agent. If None, generates a random one.
            repo: Repository in format "owner/repo". If None, uses git config.
            polling_interval: Polling interval in seconds (default 300).
            project_root: Root of project (for migration tool detection).
                         Defaults to current directory.

        Raises:
            RuntimeError: If repo cannot be determined and not provided.
        """
        # Generate agent name if not provided
        self.agent_name = agent_name or generate_agent_name()

        # Determine repository
        if repo is None:
            # Try to get from git config
            repo = self._get_repo_from_git()
            if repo is None:
                raise RuntimeError(
                    "Repository not specified and could not be determined from git config. "
                    "Provide repo='owner/repo' or run in a git repository."
                )
        self.repo = repo

        self.polling_interval = polling_interval
        self.project_root = project_root or Path.cwd()

        # Initialize Worker
        self.worker = Worker(
            agent_name=self.agent_name,
            repo=self.repo,
            project_root=self.project_root,
        )

    def _get_repo_from_git(self) -> Optional[str]:
        """
        Get repository owner/name from git config.

        Queries git for origin remote URL and parses owner/repo.

        Returns:
            Repository in format "owner/repo", or None if not found.
        """
        try:
            result = subprocess.run(
                ["git", "config", "--get", "remote.origin.url"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )
            if result.returncode != 0:
                return None

            url = result.stdout.strip()
            # Parse git@github.com:owner/repo.git or https://github.com/owner/repo.git
            if "github.com" in url:
                # Remove .git suffix and extract owner/repo
                if url.endswith(".git"):
                    url = url[:-4]
                # Handle both ssh and https formats
                if ":" in url:
                    url = url.split(":")[-1]  # ssh: take after colon
                else:
                    url = url.split("/")[-2:]  # https: take last two parts
                    url = "/".join(url)
                return url
        except Exception:
            pass

        return None

    def run_one_cycle(self) -> Dict[str, Any]:
        """
        Run one complete worker cycle.

        Process:
        1. Poll for "to-dev" labeled tickets
        2. Try to claim the first available
        3. If claimed, implement the feature
        4. Create PR and clean up labels

        Returns:
            Dict with status and details:
            {
                "status": "no_tickets" | "no_claims" | "completed" | "error",
                "ticket": <int> (if claimed),
                "error": <str> (if status == "error")
            }
        """
        try:
            # Step 1: Poll for tickets
            tickets = self.poll_for_tickets()
            if not tickets:
                return {"status": "no_tickets"}

            # Step 2: Try to claim first available ticket
            for ticket_id in tickets:
                claimed = self.try_claim_and_work(ticket_id)
                if claimed:
                    return {"status": "completed", "ticket": ticket_id}

            # No claims succeeded
            return {"status": "no_claims"}

        except Exception as e:
            return {"status": "error", "error": str(e)}

    def poll_for_tickets(self) -> List[int]:
        """
        Poll for all "to-dev" labeled issues without assignee.

        Uses gh CLI to query open issues with "to-dev" label that are not assigned
        to anyone. This prevents multiple agents from competing on the same ticket.

        Returns:
            List of issue numbers (ticket IDs).

        Raises:
            Exception: If gh command fails.
        """
        try:
            output = run_gh_cli([
                "issue", "list",
                f"--repo={self.repo}",
                "--label=to-dev",
                "--state=open",
                "--assignee=none",
                "--json=number",
            ])

            # Parse JSON output: [{"number": 1}, {"number": 2}, ...]
            issues = json.loads(output)
            return [issue["number"] for issue in issues]

        except Exception as e:
            raise Exception(f"Failed to poll for tickets: {e}")

    def try_claim_and_work(self, ticket_id: int) -> bool:
        """
        Claim a ticket and perform work.

        Atomic process:
        1. Assign to self (signals claim)
        2. Add "dev-in-progress" label
        3. Add "agent/{agent_name}" label
        4. Create working branch
        5. Implement feature (stub for now)
        6. Create PR
        7. Cleanup labels

        Returns:
            True if work completed successfully, False if claim failed.

        Raises:
            Exception: If work fails after claiming (e.g., implementation error).
        """
        # Step 1: Try to assign to self (atomic claim)
        if not self._assign_to_self(ticket_id):
            return False

        try:
            # Step 2: Add labels
            add_labels_with_retry(
                repo=self.repo,
                issue_number=ticket_id,
                labels=["dev-in-progress", f"agent/{self.agent_name}"],
            )

            # Step 3: Create working branch
            branch_name = self._create_working_branch(ticket_id)

            # Step 4: Notify on GitHub (optional comment)
            self.notify_claim(ticket_id, branch_name)

            # Step 5: Run work cycle (with heartbeat)
            def work_func():
                # Stub implementation for now
                # In real scenario, this would implement the feature
                self._implement_feature(ticket_id, branch_name)

            self.worker.run_work_cycle(ticket_id, work_func=work_func)

            # Step 6: Create PR
            pr_url = self._create_pull_request(ticket_id, branch_name)

            # Step 7: Cleanup labels and add to-test
            cleanup_labels_after_pr(self.repo, ticket_id, self.agent_name)

            return True

        except Exception as e:
            # If work fails, unassign and reset labels
            self._cleanup_failed_claim(ticket_id)
            raise Exception(f"Work failed on ticket #{ticket_id}: {e}")

    def _assign_to_self(self, ticket_id: int) -> bool:
        """
        Attempt to assign ticket to self (atomic claim).

        Returns:
            True if assignment succeeded (claim acquired), False otherwise.
        """
        try:
            # Get current user login
            me_output = run_gh_cli(["api", "user", "--jq=.login"])
            current_user = me_output.strip()

            # Try to assign
            run_gh_cli([
                "issue", "edit", str(ticket_id),
                f"--repo={self.repo}",
                f"--assignee={current_user}",
            ])

            return True

        except Exception:
            # Assignment failed (likely someone else got there first)
            return False

    def _create_working_branch(self, ticket_id: int) -> str:
        """
        Create a working branch for the ticket.

        Branch naming: feature/ticket-{ticket_id}-{agent_name}

        Returns:
            Branch name created.

        Raises:
            Exception: If branch creation fails.
        """
        branch_name = f"feature/ticket-{ticket_id}-{self.agent_name}"

        try:
            # Create branch from dev
            subprocess.run(
                ["git", "checkout", "-b", branch_name, "origin/dev"],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to create branch {branch_name}: {e.stderr}")

        return branch_name

    def notify_claim(self, ticket_id: int, branch_name: str) -> None:
        """
        Post a GitHub comment to notify about claim.

        Posts a comment indicating work has started and working branch.

        Args:
            ticket_id: The issue number.
            branch_name: The working branch name.

        Raises:
            Exception: If comment posting fails (non-fatal for orchestrator).
        """
        try:
            message = (
                f"🚀 Starting development on feature-{ticket_id}\n\n"
                f"**Agent:** {self.agent_name}\n"
                f"**Branch:** `{branch_name}`\n\n"
                f"Will keep you posted on progress."
            )
            post_comment(
                repo=self.repo,
                issue_number=ticket_id,
                body=message,
            )
        except Exception as e:
            # Log but don't fail the claim
            print(f"Warning: Failed to post claim notification: {e}")

    def _implement_feature(self, ticket_id: int, branch_name: str) -> None:
        """
        Stub for feature implementation.

        In a real scenario, this would:
        - Read ticket details from GitHub
        - Implement the feature
        - Run tests
        - Commit changes

        For now, this is a placeholder.

        Args:
            ticket_id: The issue number.
            branch_name: The working branch name.
        """
        # Stub: Log that work is happening
        print(f"Implementing feature for ticket #{ticket_id} on branch {branch_name}")

        # In a real implementation:
        # 1. git checkout branch_name
        # 2. Fetch ticket details via gh API
        # 3. Implement changes
        # 4. Run tests
        # 5. git add / git commit
        # 6. git push origin branch_name

    def _create_pull_request(self, ticket_id: int, branch_name: str) -> str:
        """
        Create a pull request from working branch to dev.

        Returns:
            URL of the created PR.

        Raises:
            Exception: If PR creation fails.
        """
        try:
            # Push working branch
            subprocess.run(
                ["git", "push", "origin", branch_name],
                cwd=self.project_root,
                check=True,
                capture_output=True,
            )

            # Create PR via gh CLI
            pr_output = run_gh_cli([
                "pr", "create",
                f"--repo={self.repo}",
                f"--base=dev",
                f"--head={branch_name}",
                f"--title=Feature: Ticket #{ticket_id}",
                f"--body=Closes #{ticket_id}",
                "--json=url",
                "--jq=.url",
            ])

            pr_url = pr_output.strip()

            # Post PR URL as comment on original issue
            post_comment(
                repo=self.repo,
                issue_number=ticket_id,
                body=f"✅ Pull Request created: {pr_url}\n\nReady for testing.",
            )

            return pr_url

        except Exception as e:
            raise Exception(f"Failed to create PR: {e}")

    def _cleanup_failed_claim(self, ticket_id: int) -> None:
        """
        Clean up after a failed claim.

        Removes "dev-in-progress" and agent labels, unassigns.

        Args:
            ticket_id: The issue number.
        """
        try:
            # Unassign
            run_gh_cli([
                "issue", "edit", str(ticket_id),
                f"--repo={self.repo}",
                "--assignee=",  # Empty removes assignee
            ])

            # Remove labels
            remove_labels_with_retry(
                repo=self.repo,
                issue_number=ticket_id,
                labels=["dev-in-progress", f"agent/{self.agent_name}"],
            )

            # Post comment
            post_comment(
                repo=self.repo,
                issue_number=ticket_id,
                body=(
                    f"⚠️ Agent {self.agent_name} encountered an error and "
                    f"released the ticket. Returning to 'to-dev' state."
                ),
            )

        except Exception as e:
            print(f"Warning: Failed to cleanup failed claim: {e}")

    def claim_ticket(self, ticket_id: int, branch_name: str) -> bool:
        """
        Claim a ticket with atomic branch push.

        Legacy method for explicit claim. Use try_claim_and_work() for full workflow.

        Args:
            ticket_id: The issue number.
            branch_name: The working branch name.

        Returns:
            True if claim succeeded, False otherwise.
        """
        return self._assign_to_self(ticket_id)
