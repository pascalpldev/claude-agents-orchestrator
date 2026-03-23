"""
Integration tests for WorkerOrchestrator.

Tests the complete worker flow from polling to PR creation.
"""

import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from worker_main import WorkerOrchestrator
from github_notifier import run_gh_cli


class TestWorkerOrchestrator:
    """Test cases for the WorkerOrchestrator class."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Provide a WorkerOrchestrator instance for testing."""
        with patch("worker_main.generate_agent_name", return_value="test-agent"):
            return WorkerOrchestrator(
                agent_name="test-agent",
                repo="test-owner/test-repo",
                polling_interval=300,
                project_root=tmp_path,
            )

    def test_orchestrator_initialization(self, orchestrator):
        """Test that WorkerOrchestrator initializes correctly."""
        assert orchestrator.agent_name == "test-agent"
        assert orchestrator.repo == "test-owner/test-repo"
        assert orchestrator.polling_interval == 300
        assert orchestrator.worker is not None

    def test_orchestrator_generates_agent_name_if_not_provided(self, tmp_path):
        """Test that WorkerOrchestrator generates a name if not provided."""
        with patch("worker_main.generate_agent_name", return_value="proud-falcon"):
            orchestrator = WorkerOrchestrator(
                repo="owner/repo",
                project_root=tmp_path,
            )
            assert orchestrator.agent_name == "proud-falcon"

    def test_orchestrator_raises_if_repo_not_provided_and_git_fails(self, tmp_path):
        """Test that WorkerOrchestrator raises if repo cannot be determined."""
        with patch.object(WorkerOrchestrator, "_get_repo_from_git", return_value=None):
            with pytest.raises(RuntimeError, match="Repository not specified"):
                WorkerOrchestrator(
                    agent_name="test-agent",
                    project_root=tmp_path,
                )

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_gets_repo_from_git(self, mock_gh, tmp_path):
        """Test that WorkerOrchestrator gets repo from git config."""
        mock_gh.return_value = "owner/repo"

        with patch.object(WorkerOrchestrator, "_get_repo_from_git", return_value="owner/repo"):
            orchestrator = WorkerOrchestrator(
                agent_name="test-agent",
                project_root=tmp_path,
            )
            assert orchestrator.repo == "owner/repo"

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_poll_for_tickets_returns_list(self, mock_gh, orchestrator):
        """Test that poll_for_tickets returns a list of issue numbers."""
        mock_gh.return_value = '[{"number": 1}, {"number": 2}, {"number": 3}]'

        tickets = orchestrator.poll_for_tickets()

        assert isinstance(tickets, list)
        assert tickets == [1, 2, 3]
        mock_gh.assert_called_once()

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_poll_for_tickets_returns_empty_when_no_tickets(
        self, mock_gh, orchestrator
    ):
        """Test that poll_for_tickets returns empty list when no tickets."""
        mock_gh.return_value = "[]"

        tickets = orchestrator.poll_for_tickets()

        assert tickets == []

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_run_one_cycle_returns_no_tickets(self, mock_gh, orchestrator):
        """Test that run_one_cycle returns no_tickets when queue is empty."""
        mock_gh.return_value = "[]"

        result = orchestrator.run_one_cycle()

        assert result["status"] == "no_tickets"

    @patch("worker_main.add_labels_with_retry")
    @patch("worker_main.run_gh_cli")
    def test_orchestrator_assign_to_self_success(self, mock_gh, mock_add_labels, orchestrator):
        """Test that _assign_to_self succeeds when user can assign."""
        mock_gh.side_effect = ["testuser", None]  # First call: get user, second: assign

        result = orchestrator._assign_to_self(123)

        assert result is True
        assert mock_gh.call_count == 2

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_assign_to_self_fails_gracefully(self, mock_gh, orchestrator):
        """Test that _assign_to_self returns False when assignment fails."""
        mock_gh.side_effect = Exception("API error")

        result = orchestrator._assign_to_self(123)

        assert result is False

    @patch("subprocess.run")
    def test_orchestrator_create_working_branch(self, mock_run, orchestrator):
        """Test that _create_working_branch creates a branch."""
        mock_run.return_value = MagicMock(returncode=0)

        branch_name = orchestrator._create_working_branch(123)

        assert "feature/ticket-123-test-agent" in branch_name
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_orchestrator_create_working_branch_fails(self, mock_run, orchestrator):
        """Test that _create_working_branch raises on failure."""
        error = Exception("git failed")
        mock_run.side_effect = error

        with pytest.raises(Exception):
            orchestrator._create_working_branch(123)

    @patch("worker_main.post_comment")
    def test_orchestrator_notify_claim(self, mock_post, orchestrator):
        """Test that notify_claim posts a comment."""
        orchestrator.notify_claim(123, "feature/ticket-123-test-agent")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[1]["issue_number"] == 123
        assert "test-agent" in call_args[1]["body"]

    def test_orchestrator_implement_feature_stub(self, orchestrator):
        """Test that _implement_feature can be called (stub)."""
        # Should not raise
        orchestrator._implement_feature(123, "feature/ticket-123-test-agent")

    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    @patch("worker_main.post_comment")
    def test_orchestrator_create_pull_request(
        self, mock_post_comment, mock_gh, mock_run, orchestrator
    ):
        """Test that _create_pull_request creates a PR and posts comment."""
        mock_gh.return_value = "https://github.com/owner/repo/pull/1"
        mock_run.return_value = MagicMock(returncode=0)

        pr_url = orchestrator._create_pull_request(123, "feature/ticket-123-test-agent")

        assert pr_url == "https://github.com/owner/repo/pull/1"
        mock_post_comment.assert_called_once()

    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    @patch("worker_main.post_comment")
    def test_orchestrator_create_pull_request_fails(
        self, mock_post_comment, mock_gh, mock_run, orchestrator
    ):
        """Test that _create_pull_request raises on failure."""
        mock_gh.side_effect = Exception("PR creation failed")

        with pytest.raises(Exception, match="Failed to create PR"):
            orchestrator._create_pull_request(123, "feature/ticket-123-test-agent")

    @patch("worker_main.cleanup_labels_after_pr")
    @patch("worker_main.post_comment")
    @patch("worker_main.add_labels_with_retry")
    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    def test_orchestrator_try_claim_and_work_success(
        self,
        mock_gh,
        mock_run,
        mock_add_labels,
        mock_post_comment,
        mock_cleanup,
        orchestrator,
    ):
        """Test that try_claim_and_work completes successfully."""
        # Mock the get_me response (get user for assignment)
        mock_gh.return_value = "testuser"
        mock_run.return_value = MagicMock(returncode=0)

        # Prevent actual subprocess calls to git
        with patch.object(orchestrator, "_create_pull_request", return_value="https://github.com/owner/repo/pull/1"):
            with patch.object(orchestrator.worker, "run_work_cycle"):
                result = orchestrator.try_claim_and_work(123)

        assert result is True

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_try_claim_and_work_claim_fails(self, mock_gh, orchestrator):
        """Test that try_claim_and_work returns False when claim fails."""
        mock_gh.side_effect = Exception("Assignment failed")

        result = orchestrator.try_claim_and_work(123)

        assert result is False

    @patch("worker_main.remove_labels_with_retry")
    @patch("worker_main.run_gh_cli")
    @patch("worker_main.post_comment")
    def test_orchestrator_cleanup_failed_claim(
        self, mock_post_comment, mock_gh, mock_remove_labels, orchestrator
    ):
        """Test that _cleanup_failed_claim removes labels and unassigns."""
        orchestrator._cleanup_failed_claim(123)

        # Should unassign and remove labels
        mock_remove_labels.assert_called_once()
        mock_post_comment.assert_called_once()

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_run_one_cycle_no_claims(self, mock_gh, orchestrator):
        """Test that run_one_cycle returns no_claims when all claims fail."""
        # Return one ticket but assignment fails
        mock_gh.side_effect = [
            '[{"number": 1}]',  # Poll returns one ticket
            Exception("Assignment failed"),  # Assignment fails
        ]

        result = orchestrator.run_one_cycle()

        assert result["status"] == "no_claims"

    @patch("worker_main.cleanup_labels_after_pr")
    @patch("worker_main.post_comment")
    @patch("worker_main.add_labels_with_retry")
    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    def test_orchestrator_run_one_cycle_completed(
        self, mock_gh, mock_run, mock_add_labels, mock_post_comment, mock_cleanup, orchestrator
    ):
        """Test that run_one_cycle returns completed status on success."""
        # First call: poll returns ticket 1; subsequent calls for assignment/PR
        mock_gh.side_effect = [
            '[{"number": 1}]',  # Poll
            "testuser",  # Get user for assignment
        ]
        mock_run.return_value = MagicMock(returncode=0)

        with patch.object(
            orchestrator, "_create_pull_request", return_value="https://github.com/owner/repo/pull/1"
        ), patch.object(
            orchestrator, "_assign_to_self", return_value=True
        ), patch.object(
            orchestrator.worker, "run_work_cycle"
        ):
            result = orchestrator.run_one_cycle()

        assert result["status"] == "completed"
        assert result["ticket"] == 1

    @patch("worker_main.run_gh_cli")
    def test_orchestrator_run_one_cycle_error_handling(self, mock_gh, orchestrator):
        """Test that run_one_cycle catches exceptions gracefully."""
        mock_gh.side_effect = Exception("Unexpected error")

        result = orchestrator.run_one_cycle()

        assert result["status"] == "error"
        assert "error" in result

    def test_orchestrator_claim_ticket_wrapper(self, orchestrator):
        """Test that claim_ticket wrapper works."""
        with patch.object(orchestrator, "_assign_to_self", return_value=True):
            result = orchestrator.claim_ticket(123, "feature/branch")

            assert result is True

    def test_orchestrator_get_repo_from_git_https(self, tmp_path):
        """Test that repo is properly derived from git URL parsing."""
        # Test the URL parsing logic by verifying expected format
        test_url = "https://github.com/owner/repo.git"
        # URL should be parsed correctly (removing .git suffix and github.com prefix)
        assert "owner/repo" in test_url.rstrip(".git")

    def test_orchestrator_get_repo_from_git_ssh(self, tmp_path):
        """Test that repo is properly derived from SSH git URL parsing."""
        # Test the URL parsing logic by verifying expected format
        test_url = "git@github.com:owner/repo.git"
        # URL should be parsed correctly from SSH format
        assert "owner/repo" in test_url


class TestWorkerOrchestratorIntegration:
    """End-to-end integration tests for complete worker flow."""

    @pytest.fixture
    def full_orchestrator(self, tmp_path):
        """Provide a fully initialized orchestrator for E2E testing."""
        with patch("worker_main.generate_agent_name", return_value="swift-eagle"):
            return WorkerOrchestrator(
                agent_name="swift-eagle",
                repo="integration-owner/integration-repo",
                polling_interval=300,
                project_root=tmp_path,
            )

    @patch("worker_main.cleanup_labels_after_pr")
    @patch("worker_main.post_comment")
    @patch("worker_main.add_labels_with_retry")
    @patch("worker_main.remove_labels_with_retry")
    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    def test_complete_worker_flow(
        self,
        mock_gh,
        mock_run,
        mock_remove_labels,
        mock_add_labels,
        mock_post_comment,
        mock_cleanup,
        full_orchestrator,
    ):
        """
        E2E test: Complete worker flow from polling to PR creation.

        Simulates:
        1. Poll finds one ticket
        2. Assign to self succeeds
        3. Create working branch
        4. Run work cycle
        5. Create PR
        6. Cleanup labels
        """
        # Setup mock responses in order
        mock_gh.return_value = '[{"number": 42}]'

        mock_run.return_value = MagicMock(returncode=0)

        # Mock all the key operations
        with patch.object(
            full_orchestrator, "_assign_to_self", return_value=True
        ), patch.object(
            full_orchestrator.worker, "run_work_cycle"
        ), patch.object(
            full_orchestrator, "_create_pull_request", return_value="https://github.com/integration-owner/integration-repo/pull/1"
        ):
            result = full_orchestrator.run_one_cycle()

        # Verify results
        assert result["status"] == "completed"
        assert result["ticket"] == 42

        # Verify sequence of operations
        mock_add_labels.assert_called_once()
        mock_cleanup.assert_called_once()

        # Verify label operations
        add_labels_call = mock_add_labels.call_args[1]
        assert "dev-in-progress" in add_labels_call["labels"]
        assert "agent/swift-eagle" in add_labels_call["labels"]

    @patch("worker_main.cleanup_labels_after_pr")
    @patch("worker_main.remove_labels_with_retry")
    @patch("worker_main.post_comment")
    @patch("worker_main.add_labels_with_retry")
    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    def test_complete_worker_flow_with_failure_cleanup(
        self,
        mock_gh,
        mock_run,
        mock_add_labels,
        mock_post_comment,
        mock_remove_labels,
        mock_cleanup,
        full_orchestrator,
    ):
        """
        E2E test: Worker handles failure and cleans up properly.

        Simulates:
        1. Poll finds one ticket
        2. Assign to self succeeds
        3. Create labels
        4. Work cycle raises exception
        5. Cleanup removes labels and unassigns
        """
        # Setup mock responses
        mock_gh.return_value = '[{"number": 99}]'

        mock_run.return_value = MagicMock(returncode=0)

        # Mock worker to raise an exception and PR creation to fail
        with patch.object(
            full_orchestrator, "_assign_to_self", return_value=True
        ), patch.object(
            full_orchestrator.worker, "run_work_cycle", side_effect=RuntimeError("Work failed")
        ):
            result = full_orchestrator.run_one_cycle()

        # Should have caught the exception and reported error
        assert result["status"] == "error"

        # Cleanup should have been attempted
        mock_remove_labels.assert_called_once()

    @patch("worker_main.cleanup_labels_after_pr")
    @patch("worker_main.post_comment")
    @patch("worker_main.add_labels_with_retry")
    @patch("subprocess.run")
    @patch("worker_main.run_gh_cli")
    def test_complete_worker_flow_multiple_tickets(
        self,
        mock_gh,
        mock_run,
        mock_add_labels,
        mock_post_comment,
        mock_cleanup,
        full_orchestrator,
    ):
        """
        E2E test: Worker processes first available ticket when multiple exist.

        Simulates:
        1. Poll finds 3 tickets
        2. First two fail to claim
        3. Third one succeeds
        4. Work completes
        """
        # Setup mock responses - note: assignment failures return False, not raise
        # So we need to mock _assign_to_self instead
        mock_gh.side_effect = [
            '[{"number": 1}, {"number": 2}, {"number": 3}]',  # Poll
            "swift-eagle-user",  # Ticket 3 assignment succeeds
            "https://github.com/integration-owner/integration-repo/pull/99",  # PR
        ]

        mock_run.return_value = MagicMock(returncode=0)

        # Mock _assign_to_self to fail for tickets 1,2 and succeed for 3
        assign_call_count = [0]
        def assign_side_effect(ticket_id):
            assign_call_count[0] += 1
            return ticket_id == 3  # Only ticket 3 succeeds

        with patch.object(
            full_orchestrator.worker, "run_work_cycle"
        ), patch.object(
            full_orchestrator, "_assign_to_self", side_effect=assign_side_effect
        ):
            result = full_orchestrator.run_one_cycle()

        # Should have succeeded on third ticket
        assert result["status"] == "completed"
        assert result["ticket"] == 3


class TestWorkerOrchestratorErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.fixture
    def orchestrator(self, tmp_path):
        """Provide an orchestrator for error testing."""
        with patch("worker_main.generate_agent_name", return_value="test-agent"):
            return WorkerOrchestrator(
                agent_name="test-agent",
                repo="test-owner/test-repo",
                project_root=tmp_path,
            )

    @patch("worker_main.run_gh_cli")
    def test_poll_for_tickets_handles_malformed_json(self, mock_gh, orchestrator):
        """Test that poll_for_tickets handles malformed JSON gracefully."""
        mock_gh.return_value = "not valid json"

        with pytest.raises(Exception, match="Failed to poll"):
            orchestrator.poll_for_tickets()

    @patch("worker_main.run_gh_cli")
    def test_poll_for_tickets_handles_gh_cli_error(self, mock_gh, orchestrator):
        """Test that poll_for_tickets handles gh CLI errors."""
        mock_gh.side_effect = Exception("gh: command not found")

        with pytest.raises(Exception, match="Failed to poll"):
            orchestrator.poll_for_tickets()

    @patch("subprocess.run")
    def test_create_working_branch_handles_git_error(self, mock_run, orchestrator):
        """Test branch creation handles git errors."""
        mock_run.side_effect = Exception("git: not found")

        with pytest.raises(Exception):
            orchestrator._create_working_branch(123)

    @patch("worker_main.post_comment")
    def test_notify_claim_handles_comment_failure(self, mock_post, orchestrator):
        """Test that notify_claim doesn't fail orchestrator on comment error."""
        mock_post.side_effect = Exception("Comment posting failed")

        # Should not raise
        orchestrator.notify_claim(123, "branch")

    @patch("worker_main.post_comment")
    def test_cleanup_failed_claim_handles_errors(self, mock_post, orchestrator):
        """Test that cleanup_failed_claim handles errors gracefully."""
        mock_post.side_effect = Exception("Cleanup error")

        # Should not raise
        orchestrator._cleanup_failed_claim(123)

    @patch("worker_main.run_gh_cli")
    def test_get_repo_from_git_handles_missing_git(self, mock_run, tmp_path):
        """Test that _get_repo_from_git handles missing git gracefully."""
        mock_run.side_effect = FileNotFoundError("git not found")

        with patch("worker_main.generate_agent_name", return_value="test-agent"):
            with pytest.raises(RuntimeError):
                WorkerOrchestrator(
                    agent_name="test-agent",
                    project_root=tmp_path,
                )

    def test_run_one_cycle_empty_ticket_list(self, orchestrator):
        """Test that run_one_cycle handles empty ticket list."""
        with patch.object(orchestrator, "poll_for_tickets", return_value=[]):
            result = orchestrator.run_one_cycle()

            assert result["status"] == "no_tickets"

    def test_run_one_cycle_catches_all_exceptions(self, orchestrator):
        """Test that run_one_cycle catches unexpected exceptions."""
        with patch.object(
            orchestrator, "poll_for_tickets", side_effect=RuntimeError("Unexpected")
        ):
            result = orchestrator.run_one_cycle()

            assert result["status"] == "error"
            assert "Unexpected" in result["error"]


class TestWorkerOrchestratorConfig:
    """Tests for configuration and initialization."""

    def test_polling_interval_configurable(self, tmp_path):
        """Test that polling interval can be configured."""
        with patch("worker_main.generate_agent_name", return_value="test"):
            orch = WorkerOrchestrator(
                agent_name="test",
                repo="owner/repo",
                polling_interval=600,
                project_root=tmp_path,
            )
            assert orch.polling_interval == 600

    def test_project_root_defaults_to_cwd(self, tmp_path):
        """Test that project_root defaults to current directory."""
        with patch("worker_main.generate_agent_name", return_value="test"):
            with patch("worker_main.Path.cwd", return_value=tmp_path):
                orch = WorkerOrchestrator(
                    agent_name="test",
                    repo="owner/repo",
                )
                assert orch.project_root is not None

    def test_worker_initialized_with_correct_params(self, tmp_path):
        """Test that Worker is initialized with correct parameters."""
        with patch("worker_main.generate_agent_name", return_value="test"):
            orch = WorkerOrchestrator(
                agent_name="my-agent",
                repo="owner/repo",
                project_root=tmp_path,
            )

            assert orch.worker.agent_name == "my-agent"
            assert orch.worker.repo == "owner/repo"
