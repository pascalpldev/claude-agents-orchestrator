"""
Test suite for lib/logger.py — canonical JSONL logging module.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import logger
from logger import log_event, estimate_cost, _get_project_slug, _get_log_path


class TestLogEvent:
    """Tests for log_event()."""

    def test_writes_valid_jsonl_with_all_required_fields(self, tmp_path):
        log_file = tmp_path / "2026-01-01.jsonl"
        project = "test-owner-repo"

        with patch("logger._get_log_path", return_value=log_file):
            log_event(
                run_id="20260101_000000_tl_5",
                agent="team-lead",
                ticket=5,
                phase="start",
                status="started",
                msg="ticket #5 started",
                data={"trigger": "dev"},
                project=project,
            )

        assert log_file.exists()
        line = log_file.read_text(encoding="utf-8").strip()
        entry = json.loads(line)

        assert entry["run_id"] == "20260101_000000_tl_5"
        assert entry["project"] == project
        assert entry["agent"] == "team-lead"
        assert entry["ticket"] == 5
        assert entry["phase"] == "start"
        assert entry["status"] == "started"
        assert entry["msg"] == "ticket #5 started"
        assert entry["data"] == {"trigger": "dev"}
        assert "ts" in entry

    def test_normalizes_ticket_string_int(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", "5", "p", "ok", project="proj")
        entry = json.loads(log_file.read_text())
        assert entry["ticket"] == 5

    def test_normalizes_ticket_string_null(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", "null", "p", "ok", project="proj")
        entry = json.loads(log_file.read_text())
        assert entry["ticket"] is None

    def test_normalizes_ticket_none(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", None, "p", "ok", project="proj")
        entry = json.loads(log_file.read_text())
        assert entry["ticket"] is None

    def test_normalizes_ticket_int(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", 42, "p", "ok", project="proj")
        entry = json.loads(log_file.read_text())
        assert entry["ticket"] == 42

    def test_invalid_data_json_does_not_raise(self, tmp_path):
        """Invalid data dict passed as str would come from CLI; at Python API level
        this test verifies data=None defaults to {} without raising."""
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            # data=None should default to {}
            log_event("rid", "dev", 1, "p", "ok", data=None, project="proj")
        entry = json.loads(log_file.read_text())
        assert entry["data"] == {}

    def test_never_raises_on_unwritable_path(self, tmp_path):
        """log_event must not raise even if the path is unwritable."""
        unwritable = Path("/nonexistent/deeply/nested/path/out.jsonl")
        with patch("logger._get_log_path", return_value=unwritable):
            # Should not raise
            log_event("rid", "dev", 1, "p", "ok", project="proj")

    def test_project_none_calls_get_project_slug(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_project_slug", return_value="auto-slug") as mock_slug, \
             patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", 1, "p", "ok")
        mock_slug.assert_called_once()

    def test_project_explicit_skips_slug_detection(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_project_slug") as mock_slug, \
             patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", 1, "p", "ok", project="explicit-project")
        mock_slug.assert_not_called()

    def test_creates_parent_directories(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c" / "out.jsonl"
        with patch("logger._get_log_path", return_value=nested):
            log_event("rid", "dev", 1, "p", "ok", project="proj")
        assert nested.exists()

    def test_appends_multiple_entries(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", 1, "phase1", "ok", project="proj")
            log_event("rid", "dev", 1, "phase2", "ok", project="proj")
        lines = log_file.read_text().strip().splitlines()
        assert len(lines) == 2
        assert json.loads(lines[0])["phase"] == "phase1"
        assert json.loads(lines[1])["phase"] == "phase2"

    def test_default_msg_is_empty_string(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", 1, "p", "ok", project="proj")
        entry = json.loads(log_file.read_text())
        assert entry["msg"] == ""

    def test_utf8_encoding(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            log_event("rid", "dev", 1, "p", "ok", msg="héllo wörld — 日本語", project="proj")
        entry = json.loads(log_file.read_text(encoding="utf-8"))
        assert entry["msg"] == "héllo wörld — 日本語"

    def test_non_serializable_data_does_not_raise(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file):
            # object() is not JSON-serializable; log_event must not raise
            log_event("rid", "dev", 1, "p", "ok", data={"key": object()}, project="proj")


class TestCLIInterface:
    """Tests for the command-line interface."""

    def test_valid_args_writes_log(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file), \
             patch("logger._get_project_slug", return_value="proj"):
            with patch.object(sys, "argv", [
                "logger.py",
                "run123", "team-lead", "5", "start", "started",
                "hello", '{"key": "val"}'
            ]):
                logger._main()
        entry = json.loads(log_file.read_text())
        assert entry["run_id"] == "run123"
        assert entry["ticket"] == 5
        assert entry["data"] == {"key": "val"}

    def test_fewer_than_5_args_exits_1(self):
        with patch.object(sys, "argv", ["logger.py", "run123", "dev", "5"]):
            with pytest.raises(SystemExit) as exc_info:
                logger._main()
        assert exc_info.value.code == 1

    def test_exactly_5_args_does_not_exit(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file), \
             patch("logger._get_project_slug", return_value="proj"):
            with patch.object(sys, "argv", [
                "logger.py", "rid", "dev", "null", "phase", "ok"
            ]):
                logger._main()  # should not raise
        assert log_file.exists()

    def test_invalid_data_json_stores_raw(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file), \
             patch("logger._get_project_slug", return_value="proj"):
            with patch.object(sys, "argv", [
                "logger.py", "rid", "dev", "1", "p", "ok", "msg", "not-valid-json"
            ]):
                logger._main()
        entry = json.loads(log_file.read_text())
        assert entry["data"] == {"raw": "not-valid-json"}

    def test_exactly_4_user_args_exits_1(self):
        # 5 elements in sys.argv = script name + 4 user args → len < 6 → exit(1)
        with patch.object(sys, "argv", ["logger.py", "run_id", "dev", "5", "start"]):
            with pytest.raises(SystemExit) as exc_info:
                logger._main()
        assert exc_info.value.code == 1

    def test_ticket_null_string_normalizes(self, tmp_path):
        log_file = tmp_path / "out.jsonl"
        with patch("logger._get_log_path", return_value=log_file), \
             patch("logger._get_project_slug", return_value="proj"):
            with patch.object(sys, "argv", [
                "logger.py", "rid", "dev", "null", "p", "ok"
            ]):
                logger._main()
        entry = json.loads(log_file.read_text())
        assert entry["ticket"] is None


class TestEstimateCost:
    """Tests for estimate_cost()."""

    def test_sonnet_cost(self):
        # 4000 chars read = 1000 input tokens; 4000 chars written = 1000 output tokens
        # cost = (1000 * 3.0 + 1000 * 15.0) / 1_000_000 = 0.018
        cost = estimate_cost("claude-sonnet-4-6", 4000, 4000)
        assert abs(cost - 0.018) < 1e-9

    def test_haiku_cost(self):
        # 4000 read = 1000 input, 4000 written = 1000 output
        # cost = (1000 * 0.25 + 1000 * 1.25) / 1_000_000 = 0.0015
        cost = estimate_cost("claude-haiku-4-5", 4000, 4000)
        assert abs(cost - 0.0015) < 1e-9

    def test_opus_cost(self):
        # 4000 read = 1000 input, 4000 written = 1000 output
        # cost = (1000 * 15.0 + 1000 * 75.0) / 1_000_000 = 0.09
        cost = estimate_cost("claude-opus-4-6", 4000, 4000)
        assert abs(cost - 0.09) < 1e-9

    def test_unknown_model_returns_none(self):
        assert estimate_cost("gpt-4", 1000, 1000) is None
        assert estimate_cost("unknown-model-x", 0, 0) is None

    def test_zero_chars(self):
        cost = estimate_cost("claude-sonnet-4-6", 0, 0)
        assert cost == 0.0

    def test_only_input_chars(self):
        # 4000 read = 1000 input tokens, 0 output
        # cost = (1000 * 3.0) / 1_000_000 = 0.003
        cost = estimate_cost("claude-sonnet-4-6", 4000, 0)
        assert abs(cost - 0.003) < 1e-9

    def test_only_output_chars(self):
        # 0 input, 4000 written = 1000 output tokens
        # cost = (1000 * 15.0) / 1_000_000 = 0.015
        cost = estimate_cost("claude-sonnet-4-6", 0, 4000)
        assert abs(cost - 0.015) < 1e-9


class TestGetProjectSlug:
    """Tests for _get_project_slug()."""

    def test_ssh_url(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:owner/repo.git\n"
        with patch("subprocess.run", return_value=mock_result):
            slug = _get_project_slug()
        assert slug == "owner-repo"

    def test_https_url(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/owner/repo.git\n"
        with patch("subprocess.run", return_value=mock_result):
            slug = _get_project_slug()
        assert slug == "owner-repo"

    def test_https_url_without_git_suffix(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/owner/repo\n"
        with patch("subprocess.run", return_value=mock_result):
            slug = _get_project_slug()
        assert slug == "owner-repo"

    def test_nonzero_returncode_returns_unknown(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            slug = _get_project_slug()
        assert slug == "unknown"

    def test_subprocess_exception_returns_unknown(self):
        with patch("subprocess.run", side_effect=Exception("git not found")):
            slug = _get_project_slug()
        assert slug == "unknown"

    def test_empty_output_returns_unknown(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            slug = _get_project_slug()
        assert slug == "unknown"

    def test_org_with_multiple_parts(self):
        """owner/repo path becomes owner-repo."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "git@github.com:my-org/my-repo.git\n"
        with patch("subprocess.run", return_value=mock_result):
            slug = _get_project_slug()
        assert slug == "my-org-my-repo"


class TestGetLogPath:
    """Tests for _get_log_path()."""

    def test_path_structure(self):
        path = _get_log_path("owner-repo")
        assert path.parent.name == "owner-repo"
        assert path.parent.parent.name == "logs"
        assert path.suffix == ".jsonl"
        # filename is a date in YYYY-MM-DD format
        import re
        assert re.match(r"\d{4}-\d{2}-\d{2}\.jsonl", path.name)

    def test_path_under_home(self):
        path = _get_log_path("proj")
        assert str(path).startswith(str(Path.home()))
