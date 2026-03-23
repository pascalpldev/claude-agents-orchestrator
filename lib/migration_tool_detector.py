"""
Detect migration tool from CLAUDE.md and validate installation.

Supports: Prisma, Alembic, Flyway, SQL (default).
"""

import subprocess
from enum import Enum
from pathlib import Path
from typing import List


class MigrationTool(Enum):
    """Supported migration tools."""

    PRISMA = "prisma"
    ALEMBIC = "alembic"
    FLYWAY = "flyway"
    SQL = "sql"


def detect_migration_tool(project_root: Path) -> MigrationTool:
    """
    Detect migration tool from CLAUDE.md (case-insensitive).

    Checks CLAUDE.md file for mentions of migration tools in order:
    1. Prisma
    2. Alembic
    3. Flyway
    4. Default to SQL

    Args:
        project_root: Path to the project root directory.

    Returns:
        MigrationTool enum value indicating the detected tool.
    """
    claude_md = project_root / "CLAUDE.md"
    if not claude_md.exists():
        return MigrationTool.SQL

    content = claude_md.read_text().lower()
    if "prisma" in content:
        return MigrationTool.PRISMA
    if "alembic" in content:
        return MigrationTool.ALEMBIC
    if "flyway" in content:
        return MigrationTool.FLYWAY
    return MigrationTool.SQL


def validate_tool_installed(tool: MigrationTool) -> None:
    """
    Verify tool is installed and accessible in PATH.

    SQL migrations don't require external validation (no tool needed).
    For other tools, runs their version command to verify installation.

    Args:
        tool: MigrationTool to validate.

    Raises:
        RuntimeError: If the tool is not installed or not in PATH.
    """
    if tool == MigrationTool.SQL:
        return

    commands = {
        MigrationTool.PRISMA: ["prisma", "--version"],
        MigrationTool.ALEMBIC: ["alembic", "--version"],
        MigrationTool.FLYWAY: ["flyway", "-version"],
    }

    cmd = commands[tool]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"{tool.value} not installed or not in PATH")


def get_migration_command(tool: MigrationTool) -> List[str]:
    """
    Get command to run migrations for the given tool.

    Args:
        tool: MigrationTool to get command for.

    Returns:
        List of command parts that can be passed to subprocess.run().
    """
    if tool == MigrationTool.PRISMA:
        return ["prisma", "migrate", "deploy"]
    elif tool == MigrationTool.ALEMBIC:
        return ["alembic", "upgrade", "head"]
    elif tool == MigrationTool.FLYWAY:
        return ["flyway", "migrate"]
    else:  # SQL
        return ["python", "lib/migrations.py"]
