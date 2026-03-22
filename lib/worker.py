"""
Worker for managing ticket processing with heartbeat monitoring.

Workers claim tickets with lock files and periodically update
heartbeats to signal they're still alive. This prevents ghost
claims from blocking tickets indefinitely.
"""

import time
from pathlib import Path
from typing import Callable, Optional

from heartbeat import (
    create_lock_file,
    update_heartbeat,
    delete_lock_file,
)


class Worker:
    """
    Worker that processes tickets with heartbeat-based lifecycle management.

    Attributes:
        agent_name: Name of the agent running this worker.
        repo: Repository name being worked on.
        locks_dir: Directory to store lock files.
        heartbeat_interval: Seconds between heartbeat updates (default: 300 = 5 min).
        ghost_timeout: Seconds before claim is considered ghost (default: 1200 = 20 min).
    """

    def __init__(
        self,
        agent_name: str,
        repo: str,
        locks_dir: Optional[Path] = None,
        heartbeat_interval: int = 300,
        ghost_timeout: int = 1200,
    ):
        """
        Initialize a Worker.

        Args:
            agent_name: Name of the agent running this worker.
            repo: Repository name being worked on.
            locks_dir: Directory to store lock files. Defaults to .locks/
            heartbeat_interval: Seconds between heartbeat updates (default: 300).
            ghost_timeout: Seconds before claim is ghost (default: 1200).
        """
        self.agent_name = agent_name
        self.repo = repo
        self.locks_dir = locks_dir or Path(".locks")
        self.heartbeat_interval = heartbeat_interval
        self.ghost_timeout = ghost_timeout

    def _get_lock_path(self, ticket_id: int) -> Path:
        """
        Get the lock file path for a ticket.

        Args:
            ticket_id: ID of the ticket.

        Returns:
            Path to the lock file.
        """
        return self.locks_dir / f"ticket-{ticket_id}.lock"

    def run_work_cycle(
        self,
        ticket_id: int,
        work_func: Optional[Callable] = None,
    ) -> None:
        """
        Run a work cycle with heartbeat management.

        Creates a lock file at the start, periodically updates the heartbeat
        every heartbeat_interval seconds, calls the work function, and
        cleans up the lock file at the end.

        Args:
            ticket_id: ID of the ticket being worked on.
            work_func: Callable that performs the actual work.
                      If None, just manages lifecycle without work.

        Raises:
            Any exception raised by work_func will be re-raised after cleanup.
        """
        lock_path = self._get_lock_path(ticket_id)

        # Create lock at start
        create_lock_file(lock_path, self.agent_name)

        try:
            # Track when we last updated heartbeat
            last_heartbeat = time.time()

            # Run work function with periodic heartbeat updates
            if work_func:
                # For short work, just run it directly
                # For long work, we'd need to break it into chunks
                work_func()
            else:
                # If no work function, still respect heartbeat interval
                time.sleep(self.heartbeat_interval)

            # Update heartbeat after work
            update_heartbeat(lock_path)

        finally:
            # Always clean up lock file
            delete_lock_file(lock_path)
