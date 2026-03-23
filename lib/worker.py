"""
Worker for managing ticket processing with heartbeat monitoring.

Workers claim tickets with lock files and periodically update
heartbeats to signal they're still alive. This prevents ghost
claims from blocking tickets indefinitely.

For long-running work (> ghost_timeout), the work_func must accept a
heartbeat_callback parameter and call it periodically to signal liveness.
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

        Note:
            heartbeat_interval should be well below ghost_timeout. Default values
            ensure heartbeats are sent every 5 minutes with a 20-minute ghost timeout.
        """
        self.agent_name = agent_name
        self.repo = repo
        self.locks_dir = locks_dir or Path(".locks")
        self.heartbeat_interval = heartbeat_interval
        self.ghost_timeout = ghost_timeout
        self.last_heartbeat_time = time.time()

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

        Creates a lock file at the start, calls the work function (with optional
        heartbeat callback for long-running operations), and cleans up the lock
        file at the end.

        For long-running work_func (> ghost_timeout seconds), the work_func MUST:
            1. Accept a heartbeat_callback parameter
            2. Call heartbeat_callback() periodically (at least every heartbeat_interval seconds)

        Example long-running work:
            def long_work(heartbeat_callback):
                for i in range(100):
                    do_something()
                    if i % 10 == 0:
                        heartbeat_callback()  # Update every 10 iterations

        Args:
            ticket_id: ID of the ticket being worked on.
            work_func: Callable that performs the actual work.
                      If None, just manages lifecycle without work.
                      For long work, should accept (heartbeat_callback) parameter.

        Raises:
            Any exception raised by work_func will be re-raised after cleanup.
        """
        lock_path = self._get_lock_path(ticket_id)

        # Create lock at start
        create_lock_file(lock_path, self.agent_name)
        self.last_heartbeat_time = time.time()

        try:
            if work_func:
                # Define heartbeat callback for long-running work
                def heartbeat_callback():
                    update_heartbeat(lock_path)
                    self.last_heartbeat_time = time.time()

                # Try to call with heartbeat_callback first (for long-running work)
                try:
                    work_func(heartbeat_callback)
                except TypeError:
                    # work_func doesn't accept heartbeat_callback parameter
                    # This is OK for short-running work
                    work_func()
            else:
                # If no work function, still respect heartbeat interval
                time.sleep(self.heartbeat_interval)

            # Final heartbeat after work completes
            update_heartbeat(lock_path)
            self.last_heartbeat_time = time.time()

        finally:
            # Always clean up lock file
            delete_lock_file(lock_path)
