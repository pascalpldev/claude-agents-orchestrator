"""
Test suite for heartbeat manager - ghost claim detection.

Follows TDD: tests written first, then implementation.
"""

import json
import time
from pathlib import Path
from datetime import datetime
import pytest

from heartbeat import (
    create_lock_file,
    update_heartbeat,
    is_ghost_claim,
    delete_lock_file,
)


class TestHeartbeatManager:
    """Test cases for the heartbeat module."""

    @pytest.fixture
    def temp_lock_dir(self, tmp_path):
        """Provide a temporary directory for lock files."""
        return tmp_path / "locks"

    @pytest.fixture
    def lock_file_path(self, temp_lock_dir):
        """Provide a lock file path."""
        return temp_lock_dir / "ticket-123.lock"

    def test_create_lock_file_creates_file(self, lock_file_path):
        """Test that create_lock_file creates a lock file."""
        create_lock_file(lock_file_path, "test-agent")
        assert lock_file_path.exists()

    def test_create_lock_file_contains_agent_name(self, lock_file_path):
        """Test that lock file contains the correct agent name."""
        agent_name = "test-agent"
        create_lock_file(lock_file_path, agent_name)
        data = json.loads(lock_file_path.read_text())
        assert data["agent"] == agent_name

    def test_create_lock_file_contains_claimed_at(self, lock_file_path):
        """Test that lock file contains claimed_at timestamp."""
        before_time = datetime.now().timestamp()
        create_lock_file(lock_file_path, "test-agent")
        after_time = datetime.now().timestamp()

        data = json.loads(lock_file_path.read_text())
        assert "claimed_at" in data
        assert before_time <= data["claimed_at"] <= after_time

    def test_create_lock_file_contains_last_heartbeat(self, lock_file_path):
        """Test that lock file contains last_heartbeat timestamp."""
        before_time = datetime.now().timestamp()
        create_lock_file(lock_file_path, "test-agent")
        after_time = datetime.now().timestamp()

        data = json.loads(lock_file_path.read_text())
        assert "last_heartbeat" in data
        assert before_time <= data["last_heartbeat"] <= after_time

    def test_create_lock_file_initial_timestamps_equal(self, lock_file_path):
        """Test that claimed_at and last_heartbeat are equal initially."""
        create_lock_file(lock_file_path, "test-agent")
        data = json.loads(lock_file_path.read_text())
        assert data["claimed_at"] == data["last_heartbeat"]

    def test_create_lock_file_creates_parent_directories(self, tmp_path):
        """Test that create_lock_file creates parent directories if needed."""
        nested_path = tmp_path / "a" / "b" / "c" / "ticket.lock"
        create_lock_file(nested_path, "test-agent")
        assert nested_path.exists()
        assert nested_path.parent.exists()

    def test_update_heartbeat_raises_when_file_not_exists(self, lock_file_path):
        """Test that update_heartbeat raises FileNotFoundError if lock doesn't exist."""
        with pytest.raises(FileNotFoundError):
            update_heartbeat(lock_file_path)

    def test_update_heartbeat_updates_timestamp(self, lock_file_path):
        """Test that update_heartbeat updates last_heartbeat."""
        create_lock_file(lock_file_path, "test-agent")
        data = json.loads(lock_file_path.read_text())
        original_heartbeat = data["last_heartbeat"]

        # Wait a bit and update
        time.sleep(0.1)
        update_heartbeat(lock_file_path)

        data = json.loads(lock_file_path.read_text())
        assert data["last_heartbeat"] > original_heartbeat

    def test_update_heartbeat_preserves_claimed_at(self, lock_file_path):
        """Test that update_heartbeat doesn't change claimed_at."""
        create_lock_file(lock_file_path, "test-agent")
        data = json.loads(lock_file_path.read_text())
        original_claimed_at = data["claimed_at"]

        time.sleep(0.1)
        update_heartbeat(lock_file_path)

        data = json.loads(lock_file_path.read_text())
        assert data["claimed_at"] == original_claimed_at

    def test_update_heartbeat_preserves_agent_name(self, lock_file_path):
        """Test that update_heartbeat doesn't change agent name."""
        agent_name = "test-agent"
        create_lock_file(lock_file_path, agent_name)

        update_heartbeat(lock_file_path)

        data = json.loads(lock_file_path.read_text())
        assert data["agent"] == agent_name

    def test_is_ghost_claim_returns_false_when_file_not_exists(self, lock_file_path):
        """Test that is_ghost_claim returns False if lock doesn't exist."""
        assert is_ghost_claim(lock_file_path) is False

    def test_is_ghost_claim_returns_false_for_fresh_claim(self, lock_file_path):
        """Test that is_ghost_claim returns False for fresh claims."""
        create_lock_file(lock_file_path, "test-agent")
        assert is_ghost_claim(lock_file_path) is False

    def test_is_ghost_claim_detects_stale_claim(self, lock_file_path):
        """Test that is_ghost_claim detects stale claims."""
        create_lock_file(lock_file_path, "test-agent")

        # Manually set heartbeat to 1200+ seconds ago
        data = json.loads(lock_file_path.read_text())
        data["last_heartbeat"] = datetime.now().timestamp() - 1201
        lock_file_path.write_text(json.dumps(data, indent=2))

        assert is_ghost_claim(lock_file_path) is True

    def test_is_ghost_claim_respects_custom_timeout(self, lock_file_path):
        """Test that is_ghost_claim respects custom timeout."""
        create_lock_file(lock_file_path, "test-agent")

        # Set heartbeat to 100 seconds ago
        data = json.loads(lock_file_path.read_text())
        data["last_heartbeat"] = datetime.now().timestamp() - 100
        lock_file_path.write_text(json.dumps(data, indent=2))

        # Should not be ghost with 200 second timeout
        assert is_ghost_claim(lock_file_path, timeout_seconds=200) is False
        # Should be ghost with 50 second timeout
        assert is_ghost_claim(lock_file_path, timeout_seconds=50) is True

    def test_is_ghost_claim_boundary_at_timeout(self, lock_file_path):
        """Test is_ghost_claim behavior at the timeout boundary."""
        create_lock_file(lock_file_path, "test-agent")

        # Set heartbeat 1199 seconds ago (just before timeout)
        data = json.loads(lock_file_path.read_text())
        now = datetime.now().timestamp()
        data["last_heartbeat"] = now - 1199
        lock_file_path.write_text(json.dumps(data, indent=2))

        # Should not be ghost (still within timeout)
        assert is_ghost_claim(lock_file_path, timeout_seconds=1200) is False

        # Set to 1201 seconds ago (just past timeout)
        data["last_heartbeat"] = now - 1201
        lock_file_path.write_text(json.dumps(data, indent=2))
        assert is_ghost_claim(lock_file_path, timeout_seconds=1200) is True

    def test_delete_lock_file_removes_file(self, lock_file_path):
        """Test that delete_lock_file removes the lock file."""
        create_lock_file(lock_file_path, "test-agent")
        assert lock_file_path.exists()

        delete_lock_file(lock_file_path)
        assert not lock_file_path.exists()

    def test_delete_lock_file_when_not_exists(self, lock_file_path):
        """Test that delete_lock_file handles non-existent files gracefully."""
        # Should not raise an error
        delete_lock_file(lock_file_path)
        assert not lock_file_path.exists()

    def test_full_lifecycle(self, lock_file_path):
        """Test a complete lifecycle: create -> update -> check -> delete."""
        # Create lock
        create_lock_file(lock_file_path, "agent-1")
        assert lock_file_path.exists()
        assert is_ghost_claim(lock_file_path) is False

        # Update heartbeat
        time.sleep(0.1)
        update_heartbeat(lock_file_path)
        assert is_ghost_claim(lock_file_path) is False

        # Simulate ghost (don't update)
        data = json.loads(lock_file_path.read_text())
        data["last_heartbeat"] = datetime.now().timestamp() - 1300
        lock_file_path.write_text(json.dumps(data, indent=2))
        assert is_ghost_claim(lock_file_path) is True

        # Clean up
        delete_lock_file(lock_file_path)
        assert not lock_file_path.exists()
