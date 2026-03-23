"""
Test suite for ghost claim cleanup module.

Tests cleanup of stalled agent claims and recovery of tickets.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, call
from tempfile import TemporaryDirectory

from ghost_cleaner import cleanup_ghost_claim


class TestCleanupGhostClaimBasic:
    """Test basic ghost claim cleanup without branch deletion."""

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_ghost_claim_basic(
        self, mock_remove, mock_add, mock_post
    ):
        """Test basic cleanup of ghost claim."""
        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-123.lock"
            lock_path.write_text('{"agent": "dev-agent", "claimed_at": 123, "last_heartbeat": 123}')

            cleanup_ghost_claim(
                repo="owner/repo",
                issue_number=123,
                lock_path=lock_path
            )

            # Verify remove labels called
            mock_remove.assert_called_once_with(
                repo="owner/repo",
                issue_number=123,
                labels=["dev-in-progress"]
            )

            # Verify add labels called
            mock_add.assert_called_once_with(
                repo="owner/repo",
                issue_number=123,
                labels=["to-dev"]
            )

            # Verify comment posted
            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            assert call_args["repo"] == "owner/repo"
            assert call_args["issue_number"] == 123
            assert "ghost" in call_args["body"].lower() or "stalled" in call_args["body"].lower()

            # Verify lock file deleted
            assert not lock_path.exists()

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_removes_correct_label(self, mock_remove, mock_add, mock_post):
        """Test that cleanup removes dev-in-progress label."""
        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-456.lock"
            lock_path.write_text('{}')

            cleanup_ghost_claim(
                repo="owner/repo",
                issue_number=456,
                lock_path=lock_path
            )

            removed_labels = mock_remove.call_args[1]["labels"]
            assert "dev-in-progress" in removed_labels

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_adds_to_dev_label(self, mock_remove, mock_add, mock_post):
        """Test that cleanup adds to-dev label."""
        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-789.lock"
            lock_path.write_text('{}')

            cleanup_ghost_claim(
                repo="owner/repo",
                issue_number=789,
                lock_path=lock_path
            )

            added_labels = mock_add.call_args[1]["labels"]
            assert "to-dev" in added_labels


class TestCleanupGhostClaimWithBranchDeletion:
    """Test ghost claim cleanup with optional branch deletion."""

    @patch("ghost_cleaner.subprocess.run")
    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_ghost_claim_with_branch_deletion(
        self, mock_remove, mock_add, mock_post, mock_subprocess
    ):
        """Test cleanup with branch deletion."""
        mock_subprocess.return_value = Mock(returncode=0)

        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-999.lock"
            lock_path.write_text('{}')

            cleanup_ghost_claim(
                repo="owner/repo",
                issue_number=999,
                lock_path=lock_path,
                delete_branch=True,
                branch_name="feature/issue-999"
            )

            # Verify labels removed
            mock_remove.assert_called_once()

            # Verify labels added
            mock_add.assert_called_once()

            # Verify comment posted
            mock_post.assert_called_once()

            # Verify branch deletion attempted
            mock_subprocess.assert_called_once_with(
                ["git", "branch", "-D", "feature/issue-999"],
                capture_output=True,
                text=True,
                check=True
            )

            # Verify lock file deleted
            assert not lock_path.exists()

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_requires_branch_name_when_deleting(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that branch_name is required when delete_branch=True."""
        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-555.lock"
            lock_path.write_text('{}')

            with pytest.raises(ValueError, match="branch_name must be provided"):
                cleanup_ghost_claim(
                    repo="owner/repo",
                    issue_number=555,
                    lock_path=lock_path,
                    delete_branch=True,
                    branch_name=None
                )

    @patch("ghost_cleaner.subprocess.run")
    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_handles_branch_deletion_error(
        self, mock_remove, mock_add, mock_post, mock_subprocess
    ):
        """Test that branch deletion error doesn't fail the cleanup."""
        mock_subprocess.side_effect = Exception("Branch not found")

        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-666.lock"
            lock_path.write_text('{}')

            # Should not raise, should complete successfully
            cleanup_ghost_claim(
                repo="owner/repo",
                issue_number=666,
                lock_path=lock_path,
                delete_branch=True,
                branch_name="feature/issue-666"
            )

            # Verify core operations completed
            mock_remove.assert_called_once()
            mock_add.assert_called_once()
            mock_post.assert_called_once()


class TestCleanupHandlesMissingLock:
    """Test cleanup when lock file is missing."""

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_handles_missing_lock_file(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that cleanup handles missing lock file gracefully."""
        lock_path = Path("/nonexistent/path/ticket-111.lock")

        cleanup_ghost_claim(
            repo="owner/repo",
            issue_number=111,
            lock_path=lock_path
        )

        # Should still clean up labels and post comment
        mock_remove.assert_called_once()
        mock_add.assert_called_once()
        mock_post.assert_called_once()

        # Lock file still shouldn't exist
        assert not lock_path.exists()


class TestCleanupSequence:
    """Test that cleanup operations occur in correct sequence."""

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_calls_operations_in_sequence(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that operations are called in correct order."""
        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-222.lock"
            lock_path.write_text('{}')

            cleanup_ghost_claim(
                repo="owner/repo",
                issue_number=222,
                lock_path=lock_path
            )

            # All three functions should be called
            assert mock_remove.called
            assert mock_add.called
            assert mock_post.called

            # Remove should be called first, then add, then post
            assert mock_remove.call_count == 1
            assert mock_add.call_count == 1
            assert mock_post.call_count == 1


class TestCleanupErrorPropagation:
    """Test that GitHub errors are properly propagated."""

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_propagates_remove_error(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that errors from remove_labels are propagated."""
        mock_remove.side_effect = Exception("Remove failed")

        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-333.lock"
            lock_path.write_text('{}')

            with pytest.raises(Exception, match="Remove failed"):
                cleanup_ghost_claim(
                    repo="owner/repo",
                    issue_number=333,
                    lock_path=lock_path
                )

            # Should not continue to add labels
            mock_add.assert_not_called()

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_propagates_add_error(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that errors from add_labels are propagated."""
        mock_add.side_effect = Exception("Add failed")

        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-444.lock"
            lock_path.write_text('{}')

            with pytest.raises(Exception, match="Add failed"):
                cleanup_ghost_claim(
                    repo="owner/repo",
                    issue_number=444,
                    lock_path=lock_path
                )

            # Remove should have been called first
            mock_remove.assert_called_once()

    @patch("ghost_cleaner.post_comment")
    @patch("ghost_cleaner.add_labels_with_retry")
    @patch("ghost_cleaner.remove_labels_with_retry")
    def test_cleanup_propagates_comment_error(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that errors from post_comment are propagated."""
        mock_post.side_effect = Exception("Comment failed")

        with TemporaryDirectory() as tmpdir:
            lock_path = Path(tmpdir) / "ticket-555.lock"
            lock_path.write_text('{}')

            with pytest.raises(Exception, match="Comment failed"):
                cleanup_ghost_claim(
                    repo="owner/repo",
                    issue_number=555,
                    lock_path=lock_path
                )

            # Remove and add should have been called
            mock_remove.assert_called_once()
            mock_add.assert_called_once()
