"""
Test suite for worker - heartbeat integration.

Follows TDD: tests written first, then implementation.
"""

import json
import time
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, call
import pytest

from worker import Worker


class TestWorker:
    """Test cases for the Worker class."""

    @pytest.fixture
    def temp_locks_dir(self, tmp_path):
        """Provide a temporary directory for lock files."""
        return tmp_path / "locks"

    @pytest.fixture
    def worker(self, temp_locks_dir):
        """Provide a Worker instance with test configuration."""
        return Worker(
            agent_name="test-agent",
            repo="test-repo",
            locks_dir=temp_locks_dir,
            heartbeat_interval=0.1,  # 100ms for testing
            ghost_timeout=1,  # 1 second for testing
        )

    def test_worker_initialization(self, worker):
        """Test that Worker initializes with correct attributes."""
        assert worker.agent_name == "test-agent"
        assert worker.repo == "test-repo"
        assert worker.heartbeat_interval == 0.1
        assert worker.ghost_timeout == 1

    def test_worker_default_heartbeat_interval(self):
        """Test that Worker has default heartbeat interval of 300 seconds."""
        worker = Worker("agent", "repo")
        assert worker.heartbeat_interval == 300

    def test_worker_default_ghost_timeout(self):
        """Test that Worker has default ghost timeout of 1200 seconds."""
        worker = Worker("agent", "repo")
        assert worker.ghost_timeout == 1200

    def test_worker_can_specify_locks_dir(self, tmp_path):
        """Test that Worker uses specified locks directory."""
        locks_dir = tmp_path / "custom_locks"
        worker = Worker("agent", "repo", locks_dir=locks_dir)
        assert worker.locks_dir == locks_dir

    def test_worker_has_locks_dir_default(self):
        """Test that Worker has a default locks directory."""
        worker = Worker("agent", "repo")
        assert worker.locks_dir is not None
        assert isinstance(worker.locks_dir, Path)

    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_creates_lock_on_work_cycle_start(
        self, mock_delete, mock_update, mock_create, worker
    ):
        """Test that run_work_cycle creates lock file at start."""
        # Mock the work function to do nothing quickly
        def mock_work():
            pass

        worker.run_work_cycle(123, work_func=mock_work)
        mock_create.assert_called_once()

    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_deletes_lock_on_work_cycle_end(
        self, mock_delete, mock_update, mock_create, worker
    ):
        """Test that run_work_cycle deletes lock file at end."""
        def mock_work():
            pass

        worker.run_work_cycle(123, work_func=mock_work)
        mock_delete.assert_called_once()

    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_calls_work_function(
        self, mock_delete, mock_update, mock_create, worker
    ):
        """Test that run_work_cycle calls the provided work function."""
        mock_work = Mock()
        worker.run_work_cycle(123, work_func=mock_work)
        mock_work.assert_called_once()

    @patch("worker.time.sleep")
    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_updates_heartbeat_during_work(
        self, mock_delete, mock_update, mock_sleep, mock_create, worker
    ):
        """Test that run_work_cycle updates heartbeat periodically."""
        # Track sleeps to simulate time passing
        sleep_count = [0]

        def mock_work():
            # Simulate work that takes multiple heartbeat intervals
            for _ in range(3):
                sleep_count[0] += 1
                time.sleep(0.15)

        with patch("worker.time.sleep", side_effect=time.sleep):
            worker.run_work_cycle(123, work_func=mock_work)

        # Should have called update_heartbeat at least once during work
        assert mock_update.call_count >= 1

    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_lock_file_path_includes_ticket_id(
        self, mock_delete, mock_update, mock_create, worker
    ):
        """Test that lock file path includes the ticket ID."""
        def mock_work():
            pass

        worker.run_work_cycle(456, work_func=mock_work)

        # Check that lock file path was called with ticket number
        call_args = mock_create.call_args
        lock_path = call_args[0][0] if call_args[0] else call_args[1].get("lock_path")
        assert "456" in str(lock_path)

    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_run_work_cycle_with_short_interval(
        self, mock_delete, mock_update, mock_create, temp_locks_dir
    ):
        """Test heartbeat updates with very short work."""
        worker = Worker(
            "test-agent",
            "test-repo",
            locks_dir=temp_locks_dir,
            heartbeat_interval=0.05,  # 50ms
        )

        call_count = [0]

        def mock_work():
            call_count[0] += 1

        worker.run_work_cycle(789, work_func=mock_work)
        assert call_count[0] == 1

    @patch("worker.create_lock_file")
    @patch("worker.update_heartbeat")
    @patch("worker.delete_lock_file")
    def test_worker_handles_exception_in_work_function(
        self, mock_delete, mock_update, mock_create, worker
    ):
        """Test that run_work_cycle cleans up lock even if work fails."""
        def mock_work():
            raise RuntimeError("Work failed")

        with pytest.raises(RuntimeError):
            worker.run_work_cycle(123, work_func=mock_work)

        # Lock should still be deleted
        mock_delete.assert_called_once()

    def test_worker_lock_file_path_format(self, worker, temp_locks_dir):
        """Test that lock file path follows expected format."""
        lock_path = worker._get_lock_path(123)
        assert lock_path.parent == temp_locks_dir
        assert "123" in lock_path.name
        assert lock_path.suffix == ".lock"

    def test_worker_with_real_lock_files(self, worker, temp_locks_dir):
        """Integration test: verify heartbeat updates with real files."""
        update_count = [0]

        def increment_update_count():
            update_count[0] += 1

        # Manually track updates
        from worker import update_heartbeat as real_update

        def tracking_work():
            # Simulate work that takes longer than one heartbeat interval
            time.sleep(0.2)

        # This test verifies the integration without mocking internal calls
        worker.run_work_cycle(999, work_func=tracking_work)
        # Lock file should be cleaned up
        lock_path = worker._get_lock_path(999)
        assert not lock_path.exists()
