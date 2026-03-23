"""
Test suite for migration_tool_detector - Detect migration tools (Prisma, Alembic, Flyway, SQL).

Follows TDD: tests written first, then implementation.
"""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import pytest

from migration_tool_detector import (
    MigrationTool,
    detect_migration_tool,
    validate_tool_installed,
    get_migration_command,
)


class TestMigrationToolDetection:
    """Test cases for migration tool detection."""

    def test_detect_prisma_from_claude_md(self, tmp_path):
        """Test detection of Prisma from CLAUDE.md."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
Uses Prisma for database migrations.
## Tech Stack
- Prisma ORM
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.PRISMA

    def test_detect_prisma_case_insensitive(self, tmp_path):
        """Test that Prisma detection is case-insensitive."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
Uses PRISMA for migrations.
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.PRISMA

    def test_detect_alembic_from_claude_md(self, tmp_path):
        """Test detection of Alembic from CLAUDE.md."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
Database migrations with Alembic.
## Tech Stack
- Python with Alembic
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.ALEMBIC

    def test_detect_alembic_case_insensitive(self, tmp_path):
        """Test that Alembic detection is case-insensitive."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
Uses ALEMBIC for migrations.
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.ALEMBIC

    def test_detect_flyway_from_claude_md(self, tmp_path):
        """Test detection of Flyway from CLAUDE.md."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
Database migrations with Flyway.
## Tech Stack
- Java with Flyway
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.FLYWAY

    def test_detect_flyway_case_insensitive(self, tmp_path):
        """Test that Flyway detection is case-insensitive."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
Uses FLYWAY for migrations.
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.FLYWAY

    def test_default_to_sql_migrations_no_claude_md(self, tmp_path):
        """Test that SQL is default when CLAUDE.md doesn't exist."""
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.SQL

    def test_default_to_sql_migrations_no_tool_mentioned(self, tmp_path):
        """Test that SQL is default when no tool is mentioned in CLAUDE.md."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
No migration tool mentioned here.
Just some generic documentation.
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.SQL

    def test_prisma_takes_priority_over_alembic(self, tmp_path):
        """Test that Prisma is detected first if multiple tools mentioned."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
This project uses Prisma.
But we also have Alembic configured.
""")
        tool = detect_migration_tool(tmp_path)
        # Prisma is checked first in the detection logic
        assert tool == MigrationTool.PRISMA

    def test_alembic_takes_priority_over_flyway(self, tmp_path):
        """Test that Alembic is detected before Flyway."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("""
# My Project
This project uses Alembic.
And also Flyway for backup.
""")
        tool = detect_migration_tool(tmp_path)
        assert tool == MigrationTool.ALEMBIC


class TestMigrationToolValidation:
    """Test cases for migration tool validation."""

    def test_validate_sql_always_succeeds(self):
        """Test that SQL migrations always pass validation (no external tool)."""
        # Should not raise
        validate_tool_installed(MigrationTool.SQL)

    @patch("migration_tool_detector.subprocess.run")
    def test_validate_prisma_installed(self, mock_run):
        """Test successful Prisma validation."""
        mock_run.return_value = Mock(returncode=0)
        # Should not raise
        validate_tool_installed(MigrationTool.PRISMA)
        mock_run.assert_called_once_with(
            ["prisma", "--version"], capture_output=True
        )

    @patch("migration_tool_detector.subprocess.run")
    def test_prisma_not_installed_raises_error(self, mock_run):
        """Test that missing Prisma raises RuntimeError."""
        mock_run.return_value = Mock(returncode=1)
        with pytest.raises(RuntimeError, match="prisma not installed"):
            validate_tool_installed(MigrationTool.PRISMA)

    @patch("migration_tool_detector.subprocess.run")
    def test_validate_alembic_installed(self, mock_run):
        """Test successful Alembic validation."""
        mock_run.return_value = Mock(returncode=0)
        # Should not raise
        validate_tool_installed(MigrationTool.ALEMBIC)
        mock_run.assert_called_once_with(
            ["alembic", "--version"], capture_output=True
        )

    @patch("migration_tool_detector.subprocess.run")
    def test_alembic_not_installed_raises_error(self, mock_run):
        """Test that missing Alembic raises RuntimeError."""
        mock_run.return_value = Mock(returncode=1)
        with pytest.raises(RuntimeError, match="alembic not installed"):
            validate_tool_installed(MigrationTool.ALEMBIC)

    @patch("migration_tool_detector.subprocess.run")
    def test_validate_flyway_installed(self, mock_run):
        """Test successful Flyway validation."""
        mock_run.return_value = Mock(returncode=0)
        # Should not raise
        validate_tool_installed(MigrationTool.FLYWAY)
        mock_run.assert_called_once_with(
            ["flyway", "-version"], capture_output=True
        )

    @patch("migration_tool_detector.subprocess.run")
    def test_flyway_not_installed_raises_error(self, mock_run):
        """Test that missing Flyway raises RuntimeError."""
        mock_run.return_value = Mock(returncode=1)
        with pytest.raises(RuntimeError, match="flyway not installed"):
            validate_tool_installed(MigrationTool.FLYWAY)


class TestMigrationCommands:
    """Test cases for migration command generation."""

    def test_get_prisma_migration_command(self):
        """Test that Prisma migration command is correct."""
        cmd = get_migration_command(MigrationTool.PRISMA)
        assert cmd == ["prisma", "migrate", "deploy"]

    def test_get_alembic_migration_command(self):
        """Test that Alembic migration command is correct."""
        cmd = get_migration_command(MigrationTool.ALEMBIC)
        assert cmd == ["alembic", "upgrade", "head"]

    def test_get_flyway_migration_command(self):
        """Test that Flyway migration command is correct."""
        cmd = get_migration_command(MigrationTool.FLYWAY)
        assert cmd == ["flyway", "migrate"]

    def test_get_sql_migration_command(self):
        """Test that SQL migration command is correct."""
        cmd = get_migration_command(MigrationTool.SQL)
        assert cmd == ["python", "lib/migrations.py"]

    def test_migration_commands_are_lists(self):
        """Test that all migration commands return lists."""
        for tool in MigrationTool:
            cmd = get_migration_command(tool)
            assert isinstance(cmd, list)
            assert len(cmd) > 0
            assert all(isinstance(part, str) for part in cmd)


class TestMigrationToolEnum:
    """Test cases for MigrationTool enum."""

    def test_migration_tool_values(self):
        """Test that all MigrationTool enum values are correct."""
        assert MigrationTool.PRISMA.value == "prisma"
        assert MigrationTool.ALEMBIC.value == "alembic"
        assert MigrationTool.FLYWAY.value == "flyway"
        assert MigrationTool.SQL.value == "sql"

    def test_migration_tool_enum_members(self):
        """Test that all expected MigrationTool members exist."""
        tools = [tool.value for tool in MigrationTool]
        assert "prisma" in tools
        assert "alembic" in tools
        assert "flyway" in tools
        assert "sql" in tools
        assert len(tools) == 4
