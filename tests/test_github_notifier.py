"""
Test suite for GitHub notifier - retry logic for label/comment operations.

Follows TDD: tests written first, then implementation.
"""

import time
from unittest.mock import Mock, patch, call
import pytest

from github_notifier import (
    run_gh_cli,
    remove_labels_with_retry,
    add_labels_with_retry,
    post_comment,
    cleanup_labels_after_pr,
)


class TestRunGhCli:
    """Test cases for run_gh_cli function."""

    @patch("subprocess.run")
    def test_run_gh_cli_success(self, mock_run):
        """Test successful gh CLI command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="output",
            stderr=""
        )

        result = run_gh_cli(["issue", "list"])
        assert result == "output"
        mock_run.assert_called_once_with(
            ["gh", "issue", "list"],
            capture_output=True,
            text=True
        )

    @patch("subprocess.run")
    def test_run_gh_cli_failure_raises_exception(self, mock_run):
        """Test that run_gh_cli raises Exception on command failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="error message"
        )

        with pytest.raises(Exception, match="gh command failed: error message"):
            run_gh_cli(["issue", "invalid"])

    @patch("subprocess.run")
    def test_run_gh_cli_includes_args_in_command(self, mock_run):
        """Test that run_gh_cli correctly passes all arguments."""
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        run_gh_cli(["issue", "edit", "123", "--repo=owner/repo"])
        mock_run.assert_called_once_with(
            ["gh", "issue", "edit", "123", "--repo=owner/repo"],
            capture_output=True,
            text=True
        )


class TestRemoveLabelsWithRetry:
    """Test cases for remove_labels_with_retry function."""

    @patch("github_notifier.run_gh_cli")
    def test_remove_labels_succeeds_first_try(self, mock_run_gh):
        """Test successful label removal on first attempt."""
        mock_run_gh.return_value = ""

        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=["label1", "label2"]
        )

        # Should call run_gh_cli twice (once for each label)
        assert mock_run_gh.call_count == 2
        calls = mock_run_gh.call_args_list
        assert calls[0] == call([
            "issue", "edit", "123",
            "--repo=owner/repo", "--remove-label=label1"
        ])
        assert calls[1] == call([
            "issue", "edit", "123",
            "--repo=owner/repo", "--remove-label=label2"
        ])

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_remove_labels_retries_on_error(self, mock_sleep, mock_run_gh):
        """Test that remove_labels retries on error."""
        # First call fails, second succeeds
        mock_run_gh.side_effect = [
            Exception("Network error"),
            "",
            ""
        ]

        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=["label1"]
        )

        # Should succeed after retry
        # First attempt: 1 call fails
        # Second attempt (after sleep): 1 call succeeds
        assert mock_run_gh.call_count == 2
        mock_sleep.assert_called_once_with(5)

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_remove_labels_fails_after_max_retries(self, mock_sleep, mock_run_gh):
        """Test that remove_labels fails after max retries exhausted."""
        mock_run_gh.side_effect = Exception("Persistent error")

        with pytest.raises(Exception, match="Failed to remove labels after 3 retries"):
            remove_labels_with_retry(
                repo="owner/repo",
                issue_number=123,
                labels=["label1"],
                max_retries=3,
                retry_delay=5
            )

        # Should try 3 times before giving up
        assert mock_run_gh.call_count == 3
        # Should sleep 2 times (between attempts 1-2 and 2-3)
        assert mock_sleep.call_count == 2

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_remove_labels_custom_retry_params(self, mock_sleep, mock_run_gh):
        """Test that custom retry parameters are respected."""
        mock_run_gh.side_effect = [
            Exception("Error"),
            Exception("Error"),
            ""
        ]

        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=["label1"],
            max_retries=5,
            retry_delay=2
        )

        # Should use custom retry delay
        mock_sleep.assert_called_with(2)

    @patch("github_notifier.run_gh_cli")
    def test_remove_labels_empty_list(self, mock_run_gh):
        """Test removing empty label list."""
        mock_run_gh.return_value = ""

        # Should not raise any errors
        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=[]
        )

        # Should not call run_gh_cli at all
        mock_run_gh.assert_not_called()

    @patch("github_notifier.run_gh_cli")
    def test_remove_labels_single_label(self, mock_run_gh):
        """Test removing a single label."""
        mock_run_gh.return_value = ""

        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=["only-label"]
        )

        mock_run_gh.assert_called_once()


class TestAddLabelsWithRetry:
    """Test cases for add_labels_with_retry function."""

    @patch("github_notifier.run_gh_cli")
    def test_add_labels_succeeds_first_try(self, mock_run_gh):
        """Test successful label addition on first attempt."""
        mock_run_gh.return_value = ""

        add_labels_with_retry(
            repo="owner/repo",
            issue_number=456,
            labels=["label1", "label2"]
        )

        # Should call run_gh_cli twice (once for each label)
        assert mock_run_gh.call_count == 2
        calls = mock_run_gh.call_args_list
        assert calls[0] == call([
            "issue", "edit", "456",
            "--repo=owner/repo", "--add-label=label1"
        ])
        assert calls[1] == call([
            "issue", "edit", "456",
            "--repo=owner/repo", "--add-label=label2"
        ])

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_add_labels_retries_on_error(self, mock_sleep, mock_run_gh):
        """Test that add_labels retries on error."""
        # First call fails, second succeeds
        mock_run_gh.side_effect = [
            Exception("Rate limited"),
            ""
        ]

        add_labels_with_retry(
            repo="owner/repo",
            issue_number=456,
            labels=["label1"]
        )

        assert mock_run_gh.call_count == 2
        mock_sleep.assert_called_once_with(5)

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_add_labels_fails_after_max_retries(self, mock_sleep, mock_run_gh):
        """Test that add_labels fails after max retries exhausted."""
        mock_run_gh.side_effect = Exception("API error")

        with pytest.raises(Exception, match="Failed to add labels after 3 retries"):
            add_labels_with_retry(
                repo="owner/repo",
                issue_number=456,
                labels=["label1"],
                max_retries=3
            )

        assert mock_run_gh.call_count == 3

    @patch("github_notifier.run_gh_cli")
    def test_add_labels_empty_list(self, mock_run_gh):
        """Test adding empty label list."""
        mock_run_gh.return_value = ""

        add_labels_with_retry(
            repo="owner/repo",
            issue_number=456,
            labels=[]
        )

        mock_run_gh.assert_not_called()


class TestPostComment:
    """Test cases for post_comment function."""

    @patch("github_notifier.run_gh_cli")
    def test_post_comment_succeeds_first_try(self, mock_run_gh):
        """Test successful comment posting on first attempt."""
        mock_run_gh.return_value = ""

        post_comment(
            repo="owner/repo",
            issue_number=789,
            body="Great work!"
        )

        mock_run_gh.assert_called_once_with([
            "issue", "comment", "789",
            "--repo=owner/repo", "--body=Great work!"
        ])

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_post_comment_retries_on_error(self, mock_sleep, mock_run_gh):
        """Test that post_comment retries on error."""
        mock_run_gh.side_effect = [
            Exception("Connection timeout"),
            ""
        ]

        post_comment(
            repo="owner/repo",
            issue_number=789,
            body="Test comment"
        )

        assert mock_run_gh.call_count == 2
        mock_sleep.assert_called_once_with(5)

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_post_comment_fails_after_max_retries(self, mock_sleep, mock_run_gh):
        """Test that post_comment fails after max retries."""
        mock_run_gh.side_effect = Exception("Server error")

        with pytest.raises(Exception, match="Failed to post comment after 3 retries"):
            post_comment(
                repo="owner/repo",
                issue_number=789,
                body="Test",
                max_retries=3
            )

        assert mock_run_gh.call_count == 3

    @patch("github_notifier.run_gh_cli")
    def test_post_comment_with_multiline_body(self, mock_run_gh):
        """Test posting comment with multiline body."""
        mock_run_gh.return_value = ""
        body = "Line 1\nLine 2\nLine 3"

        post_comment(
            repo="owner/repo",
            issue_number=789,
            body=body
        )

        # Should preserve newlines in body
        args = mock_run_gh.call_args[0][0]
        assert f"--body={body}" in args

    @patch("github_notifier.run_gh_cli")
    def test_post_comment_custom_max_retries(self, mock_run_gh):
        """Test post_comment with custom max_retries."""
        mock_run_gh.side_effect = Exception("Error")

        with pytest.raises(Exception, match="Failed to post comment after 5 retries"):
            post_comment(
                repo="owner/repo",
                issue_number=789,
                body="Test",
                max_retries=5
            )

        assert mock_run_gh.call_count == 5


class TestCleanupLabelsAfterPr:
    """Test cases for cleanup_labels_after_pr function."""

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_after_pr_success(
        self, mock_remove, mock_add, mock_post
    ):
        """Test successful cleanup after PR creation."""
        cleanup_labels_after_pr(
            repo="owner/repo",
            issue_number=100,
            agent_name="dev-agent"
        )

        # Should remove dev-in-progress and agent/dev-agent
        mock_remove.assert_called_once_with(
            repo="owner/repo",
            issue_number=100,
            labels=["dev-in-progress", "agent/dev-agent"]
        )

        # Should add to-test
        mock_add.assert_called_once_with(
            repo="owner/repo",
            issue_number=100,
            labels=["to-test"]
        )

        # Should post success comment
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["repo"] == "owner/repo"
        assert call_args[1]["issue_number"] == 100
        assert "✅" in call_args[1]["body"] or "ready" in call_args[1]["body"].lower()

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_removes_correct_labels(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that cleanup removes the correct labels."""
        cleanup_labels_after_pr(
            repo="owner/repo",
            issue_number=200,
            agent_name="enrichment-agent"
        )

        # Verify the exact labels passed to remove
        removed_labels = mock_remove.call_args[1]["labels"]
        assert "dev-in-progress" in removed_labels
        assert f"agent/enrichment-agent" in removed_labels

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_adds_to_test(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that cleanup adds to-test label."""
        cleanup_labels_after_pr(
            repo="owner/repo",
            issue_number=300,
            agent_name="test-agent"
        )

        added_labels = mock_add.call_args[1]["labels"]
        assert "to-test" in added_labels

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_posts_success_comment(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that cleanup posts a success comment."""
        cleanup_labels_after_pr(
            repo="owner/repo",
            issue_number=400,
            agent_name="my-agent"
        )

        mock_post.assert_called_once()
        call_args = mock_post.call_args[1]
        assert call_args["repo"] == "owner/repo"
        assert call_args["issue_number"] == 400
        assert len(call_args["body"]) > 0

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_calls_in_sequence(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that operations are called in correct sequence."""
        cleanup_labels_after_pr(
            repo="owner/repo",
            issue_number=500,
            agent_name="seq-agent"
        )

        # All three functions should be called
        assert mock_remove.called
        assert mock_add.called
        assert mock_post.called

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_propagates_remove_errors(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that errors from remove_labels are propagated."""
        mock_remove.side_effect = Exception("Remove failed")

        with pytest.raises(Exception, match="Remove failed"):
            cleanup_labels_after_pr(
                repo="owner/repo",
                issue_number=600,
                agent_name="error-agent"
            )

        # Should not continue to add labels
        mock_add.assert_not_called()

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_propagates_add_errors(
        self, mock_remove, mock_add, mock_post
    ):
        """Test that errors from add_labels are propagated."""
        mock_add.side_effect = Exception("Add failed")

        with pytest.raises(Exception, match="Add failed"):
            cleanup_labels_after_pr(
                repo="owner/repo",
                issue_number=700,
                agent_name="error-agent"
            )

        # Should have called remove first
        mock_remove.assert_called_once()

    @patch("github_notifier.post_comment")
    @patch("github_notifier.add_labels_with_retry")
    @patch("github_notifier.remove_labels_with_retry")
    def test_cleanup_labels_with_various_agent_names(
        self, mock_remove, mock_add, mock_post
    ):
        """Test cleanup with different agent names."""
        agent_names = ["dev-agent", "enrichment-agent", "test-bot", "my-special-agent"]

        for agent_name in agent_names:
            mock_remove.reset_mock()
            mock_add.reset_mock()
            mock_post.reset_mock()

            cleanup_labels_after_pr(
                repo="owner/repo",
                issue_number=800,
                agent_name=agent_name
            )

            removed_labels = mock_remove.call_args[1]["labels"]
            assert f"agent/{agent_name}" in removed_labels


class TestRetryMechanics:
    """Test retry behavior across all functions."""

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_retry_delay_timing(self, mock_sleep, mock_run_gh):
        """Test that retry delay is applied between attempts."""
        mock_run_gh.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            ""
        ]

        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=["label1"],
            retry_delay=10
        )

        # Should sleep twice with delay of 10
        assert mock_sleep.call_count == 2
        for call_obj in mock_sleep.call_args_list:
            assert call_obj[0][0] == 10

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_no_sleep_on_first_success(self, mock_sleep, mock_run_gh):
        """Test that no sleep occurs if first attempt succeeds."""
        mock_run_gh.return_value = ""

        remove_labels_with_retry(
            repo="owner/repo",
            issue_number=123,
            labels=["label1"]
        )

        mock_sleep.assert_not_called()

    @patch("github_notifier.run_gh_cli")
    @patch("time.sleep")
    def test_max_retries_boundary(self, mock_sleep, mock_run_gh):
        """Test behavior at max_retries boundary."""
        mock_run_gh.side_effect = Exception("Error")

        # With max_retries=1, should fail on first attempt with no sleep
        with pytest.raises(Exception):
            remove_labels_with_retry(
                repo="owner/repo",
                issue_number=123,
                labels=["label1"],
                max_retries=1
            )

        assert mock_run_gh.call_count == 1
        mock_sleep.assert_not_called()
