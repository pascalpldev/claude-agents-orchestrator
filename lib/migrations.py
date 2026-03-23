"""
Database migrations runner with tracking and validation.

Provides utilities to apply SQL migrations in order, track applied migrations,
and detect checksum mismatches for modified migrations.
"""

import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, Tuple


def compute_checksum(file_path: Path) -> str:
    """
    Compute SHA256 checksum of a migration file.

    Args:
        file_path: Path to the migration file.

    Returns:
        Hexadecimal SHA256 checksum of the file contents.
    """
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def get_applied_migrations(db_path: Path) -> Dict[str, str]:
    """
    Get dictionary of applied migrations with their checksums.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        Dictionary with migration names as keys and checksums as values.
        Returns empty dict if migrations table doesn't exist.
    """
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT migration_name, checksum FROM _migrations ORDER BY applied_at"
        )
        migrations = {row[0]: row[1] for row in cursor.fetchall()}
        return migrations
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return {}
    finally:
        conn.close()


def validate_migration(file_path: Path) -> bool:
    """
    Validate migration file for basic SQL correctness.

    Checks:
    - File is not empty
    - Contains at least one SQL statement (semicolon or CREATE/ALTER/INSERT/etc)
    - File is readable

    Args:
        file_path: Path to the migration file to validate.

    Returns:
        True if migration passes validation.

    Raises:
        ValueError: If migration is invalid.
    """
    if not file_path.exists():
        raise ValueError(f"Migration file not found: {file_path}")

    content = file_path.read_text().strip()

    if not content:
        raise ValueError(f"Migration file is empty: {file_path}")

    # Check for SQL keywords or semicolon
    sql_keywords = (
        "CREATE",
        "ALTER",
        "DROP",
        "INSERT",
        "UPDATE",
        "DELETE",
        "SELECT",
        ";",
    )
    if not any(keyword.lower() in content.lower() for keyword in sql_keywords):
        raise ValueError(f"Migration file contains no SQL statements: {file_path}")

    return True


def apply_migrations(db_path: Path, migrations_dir: Path) -> None:
    """
    Apply all pending migrations to the database in order.

    Creates _migrations tracking table if it doesn't exist, then applies
    all migration files from migrations_dir in alphabetical order.

    Migration files should be named: NNN_description.sql (e.g., 001_init.sql)

    Args:
        db_path: Path to the SQLite database.
        migrations_dir: Path to the migrations directory.

    Raises:
        FileNotFoundError: If migrations_dir doesn't exist.
        ValueError: If a migration file has a checksum mismatch (already applied
                   with different content).
        sqlite3.Error: If SQL execution fails.
    """
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found: {migrations_dir}")

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        # Create migrations tracking table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS _migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT UNIQUE NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()

        # Get already applied migrations
        applied = get_applied_migrations(db_path)

        # Get all migration files in order
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            migration_name = migration_file.name
            current_checksum = compute_checksum(migration_file)

            # Check if migration was already applied
            if migration_name in applied:
                # Verify checksum matches
                if applied[migration_name] != current_checksum:
                    raise ValueError(
                        f"Checksum mismatch for {migration_name}: "
                        f"expected {applied[migration_name]}, "
                        f"got {current_checksum}. Migration may have been modified."
                    )
                # Skip already applied migrations
                continue

            # Validate migration before applying
            validate_migration(migration_file)

            # Read and execute migration
            sql_content = migration_file.read_text()
            cursor.executescript(sql_content)

            # Track migration in _migrations table
            cursor.execute(
                """
                INSERT INTO _migrations (migration_name, checksum)
                VALUES (?, ?)
            """,
                (migration_name, current_checksum),
            )
            conn.commit()

    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()
