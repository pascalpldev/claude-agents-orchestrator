"""
Schema validator for resume safety.

Provides functions to extract table/column info from SQLite databases,
compute expected schemas from migrations, and validate that actual
database schemas match expected ones before resuming work.
"""

import sqlite3
import re
from pathlib import Path
from typing import Dict, List


def inspect_schema(db_path: Path) -> Dict:
    """
    Extract schema from SQLite database.

    Extracts table names, column names for each table, and index names.

    Args:
        db_path: Path to SQLite database file.

    Returns:
        Dictionary with structure:
        {
            "tables": {
                "table_name": {"columns": ["col1", "col2", ...]},
                ...
            },
            "indexes": ["idx_name", ...]
        }

    Returns empty schema if database doesn't exist.
    """
    if not db_path.exists():
        return {"tables": {}, "indexes": []}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get all tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {}
    for (table_name,) in cursor.fetchall():
        # Get columns for this table
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        tables[table_name] = {"columns": columns}

    # Get all indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    conn.close()
    return {"tables": tables, "indexes": indexes}


def compute_expected_schema(migrations_dir: Path) -> Dict:
    """
    Parse migrations and compute expected schema.

    Parses SQL migration files in migrations_dir and extracts table
    and column definitions from CREATE TABLE and ALTER TABLE statements.

    Supports:
    - CREATE TABLE IF NOT EXISTS (case-insensitive keywords)
    - ALTER TABLE ... ADD COLUMN
    - SQL comments (both -- and /* */)

    Args:
        migrations_dir: Path to directory containing migration files (*.sql).

    Returns:
        Dictionary with structure matching inspect_schema output:
        {
            "tables": {
                "table_name": {"columns": ["col1", "col2", ...]},
                ...
            },
            "indexes": []
        }
    """
    tables: Dict[str, Dict] = {}

    if not migrations_dir.exists():
        return {"tables": {}, "indexes": []}

    # Get all migration files sorted by name (to process in order)
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for migration_file in migration_files:
        content = migration_file.read_text()

        # Remove SQL comments
        # Remove multi-line comments /* ... */
        content = re.sub(r"/\*.*?\*/", " ", content, flags=re.DOTALL)
        # Remove single-line comments -- ...
        content = re.sub(r"--.*?$", " ", content, flags=re.MULTILINE)

        # Normalize whitespace for easier parsing
        content = re.sub(r"\s+", " ", content)

        # Parse CREATE TABLE statements (with or without IF NOT EXISTS)
        # Use [^)]* to match everything except closing paren (simpler than lazy quantifier)
        create_pattern = r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\(([^)]*)\)"
        for match in re.finditer(create_pattern, content, re.IGNORECASE):
            table_name = match.group(1)
            columns_def = match.group(2)

            # Extract column names
            # Split by comma, then take the first word of each line (the column name)
            column_lines = columns_def.split(",")
            columns = []
            for line in column_lines:
                line = line.strip()
                if line:
                    # First word is column name
                    col_name = line.split()[0]
                    if col_name:
                        columns.append(col_name)

            if columns:
                tables[table_name] = {"columns": columns}

        # Parse ALTER TABLE ... ADD COLUMN statements
        alter_pattern = r"ALTER\s+TABLE\s+(\w+)\s+ADD\s+COLUMN\s+(\w+)"
        for match in re.finditer(alter_pattern, content, re.IGNORECASE):
            table_name = match.group(1)
            column_name = match.group(2)

            if table_name not in tables:
                tables[table_name] = {"columns": []}

            if column_name not in tables[table_name]["columns"]:
                tables[table_name]["columns"].append(column_name)

    return {"tables": tables, "indexes": []}


def schema_matches(actual: Dict, expected: Dict) -> bool:
    """
    Compare schemas.

    Checks if actual schema contains all expected tables and columns.
    Actual schema can have extra tables/columns - only checks that
    expected elements exist.

    Args:
        actual: Schema from inspect_schema() (actual database)
        expected: Schema from compute_expected_schema() (migrations)

    Returns:
        True if actual schema contains all expected tables and columns,
        False otherwise.
    """
    # Check each expected table exists and has expected columns
    for table_name, expected_cols_info in expected.get("tables", {}).items():
        # Check table exists
        if table_name not in actual.get("tables", {}):
            return False

        # Check expected columns exist in actual
        actual_cols = set(actual["tables"][table_name]["columns"])
        expected_col_set = set(expected_cols_info["columns"])

        if not expected_col_set.issubset(actual_cols):
            return False

    return True


def validate_resume_schema(db_path: Path, migrations_dir: Path) -> bool:
    """
    Validate schema before resume.

    Checks that the actual database schema matches the expected schema
    from migrations. Raises ValueError if there's a mismatch.

    Args:
        db_path: Path to SQLite database file.
        migrations_dir: Path to directory containing migration files.

    Returns:
        True if schema is valid.

    Raises:
        ValueError: If schema mismatch detected.
    """
    actual = inspect_schema(db_path)
    expected = compute_expected_schema(migrations_dir)

    if not schema_matches(actual, expected):
        raise ValueError(
            f"Schema mismatch on resume: actual database schema does not match "
            f"expected schema from migrations"
        )

    return True
