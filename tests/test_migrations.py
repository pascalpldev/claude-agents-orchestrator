"""
Test suite for migrations runner - database migration tracking and application.

Follows TDD: tests written first, then implementation.
"""

import hashlib
import sqlite3
import tempfile
from pathlib import Path

import pytest

from migrations import (
    apply_migrations,
    compute_checksum,
    get_applied_migrations,
    validate_migration,
)


class TestMigrations:
    """Test cases for migrations module."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        # Cleanup
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def temp_migrations_dir(self, tmp_path):
        """Create a temporary migrations directory."""
        migrations_dir = tmp_path / "migrations"
        migrations_dir.mkdir()
        return migrations_dir

    def test_apply_migrations_creates_tracking_table(self, temp_db, temp_migrations_dir):
        """Test that apply_migrations creates _migrations tracking table."""
        # Create a simple migration
        migration_file = temp_migrations_dir / "001_init.sql"
        migration_file.write_text("CREATE TABLE test (id INTEGER);")

        # Apply migrations
        apply_migrations(temp_db, temp_migrations_dir)

        # Verify _migrations table exists
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='_migrations'
        """
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None, "_migrations table was not created"

    def test_apply_migrations_tracks_applied(self, temp_db, temp_migrations_dir):
        """Test that apply_migrations tracks applied migrations."""
        # Create a migration
        migration_file = temp_migrations_dir / "001_init.sql"
        migration_content = "CREATE TABLE test (id INTEGER);"
        migration_file.write_text(migration_content)

        # Apply migrations
        apply_migrations(temp_db, temp_migrations_dir)

        # Verify migration is tracked
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT migration_name, checksum FROM _migrations")
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "001_init.sql"
        assert result[1] == hashlib.sha256(migration_content.encode()).hexdigest()

    def test_apply_migrations_skips_already_applied(self, temp_db, temp_migrations_dir):
        """Test that apply_migrations skips already applied migrations."""
        # Create first migration
        migration_file = temp_migrations_dir / "001_init.sql"
        migration_file.write_text("CREATE TABLE test (id INTEGER);")

        # Apply migrations first time
        apply_migrations(temp_db, temp_migrations_dir)

        # Create second migration
        migration_file2 = temp_migrations_dir / "002_alter.sql"
        migration_file2.write_text("ALTER TABLE test ADD COLUMN name TEXT;")

        # Apply migrations second time (should skip 001, apply 002)
        apply_migrations(temp_db, temp_migrations_dir)

        # Verify both migrations are tracked
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM _migrations")
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 2

    def test_get_applied_migrations_empty_db(self):
        """Test that get_applied_migrations returns empty dict for new database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            result = get_applied_migrations(db_path)
            assert result == {}
        finally:
            if db_path.exists():
                db_path.unlink()

    def test_get_applied_migrations_returns_dict(
        self, temp_db, temp_migrations_dir
    ):
        """Test that get_applied_migrations returns correct dictionary."""
        # Create migrations
        migration1 = temp_migrations_dir / "001_init.sql"
        migration1.write_text("CREATE TABLE test (id INTEGER);")
        migration2 = temp_migrations_dir / "002_alter.sql"
        migration2.write_text("ALTER TABLE test ADD COLUMN name TEXT;")

        # Apply migrations
        apply_migrations(temp_db, temp_migrations_dir)

        # Get applied migrations
        applied = get_applied_migrations(temp_db)

        assert len(applied) == 2
        assert "001_init.sql" in applied
        assert "002_alter.sql" in applied
        assert applied["001_init.sql"] == compute_checksum(migration1)
        assert applied["002_alter.sql"] == compute_checksum(migration2)

    def test_checksum_mismatch_detected(self, temp_db, temp_migrations_dir):
        """Test that checksum mismatch is detected for modified migrations."""
        # Create and apply first migration
        migration_file = temp_migrations_dir / "001_init.sql"
        migration_file.write_text("CREATE TABLE test (id INTEGER);")
        apply_migrations(temp_db, temp_migrations_dir)

        # Modify the migration file
        migration_file.write_text("CREATE TABLE test (id INTEGER, name TEXT);")

        # Apply migrations again - should raise ValueError
        with pytest.raises(
            ValueError, match="Checksum mismatch for 001_init.sql"
        ):
            apply_migrations(temp_db, temp_migrations_dir)

    def test_apply_migrations_in_order(self, temp_db, temp_migrations_dir):
        """Test that migrations are applied in alphabetical order."""
        # Create migrations with ordered names
        migration1 = temp_migrations_dir / "001_create_users.sql"
        migration1.write_text("CREATE TABLE users (id INTEGER PRIMARY KEY);")

        migration2 = temp_migrations_dir / "002_create_posts.sql"
        migration2.write_text("CREATE TABLE posts (id INTEGER PRIMARY KEY);")

        migration3 = temp_migrations_dir / "003_add_fk.sql"
        migration3.write_text(
            "ALTER TABLE posts ADD COLUMN user_id INTEGER REFERENCES users(id);"
        )

        # Apply all migrations
        apply_migrations(temp_db, temp_migrations_dir)

        # Verify all tables exist in correct order
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()

        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        assert "users" in tables
        assert "posts" in tables

        # Check migration tracking order
        cursor.execute(
            "SELECT migration_name FROM _migrations ORDER BY applied_at"
        )
        migrations = [row[0] for row in cursor.fetchall()]

        assert migrations == ["001_create_users.sql", "002_create_posts.sql", "003_add_fk.sql"]
        conn.close()

    def test_validate_migration_empty_file(self, tmp_path):
        """Test that validate_migration rejects empty files."""
        migration_file = tmp_path / "empty.sql"
        migration_file.write_text("")

        with pytest.raises(ValueError, match="empty"):
            validate_migration(migration_file)

    def test_validate_migration_no_sql(self, tmp_path):
        """Test that validate_migration rejects files without SQL."""
        migration_file = tmp_path / "no_sql.sql"
        migration_file.write_text("This is just plain text with no SQL keywords")

        with pytest.raises(ValueError, match="no SQL statements"):
            validate_migration(migration_file)

    def test_validate_migration_valid(self, tmp_path):
        """Test that validate_migration accepts valid SQL."""
        migration_file = tmp_path / "valid.sql"
        migration_file.write_text("CREATE TABLE test (id INTEGER);")

        assert validate_migration(migration_file) is True

    def test_validate_migration_with_semicolon(self, tmp_path):
        """Test that validate_migration accepts files with just semicolon."""
        migration_file = tmp_path / "semicolon.sql"
        migration_file.write_text("INSERT INTO table VALUES (1);")

        assert validate_migration(migration_file) is True

    def test_compute_checksum_consistency(self, tmp_path):
        """Test that compute_checksum returns consistent results."""
        migration_file = tmp_path / "test.sql"
        content = "CREATE TABLE test (id INTEGER);"
        migration_file.write_text(content)

        checksum1 = compute_checksum(migration_file)
        checksum2 = compute_checksum(migration_file)

        assert checksum1 == checksum2

    def test_compute_checksum_different_files(self, tmp_path):
        """Test that different files have different checksums."""
        file1 = tmp_path / "file1.sql"
        file1.write_text("CREATE TABLE test1 (id INTEGER);")

        file2 = tmp_path / "file2.sql"
        file2.write_text("CREATE TABLE test2 (id INTEGER);")

        checksum1 = compute_checksum(file1)
        checksum2 = compute_checksum(file2)

        assert checksum1 != checksum2

    def test_apply_migrations_missing_directory(self, temp_db):
        """Test that apply_migrations raises FileNotFoundError for missing directory."""
        missing_dir = Path("/nonexistent/migrations")

        with pytest.raises(FileNotFoundError):
            apply_migrations(temp_db, missing_dir)

    def test_apply_migrations_with_comments(self, temp_db, temp_migrations_dir):
        """Test that apply_migrations works with SQL comments."""
        migration_file = temp_migrations_dir / "001_init.sql"
        migration_file.write_text(
            """
            -- This is a comment
            CREATE TABLE test (id INTEGER);
            /* Multi-line
               comment */
            CREATE INDEX idx_test ON test(id);
        """
        )

        apply_migrations(temp_db, temp_migrations_dir)

        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT migration_name FROM _migrations WHERE migration_name = '001_init.sql'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_apply_migrations_transaction_rollback_on_error(
        self, temp_db, temp_migrations_dir
    ):
        """Test that failed migration doesn't leave partial state."""
        # Create a valid migration
        migration1 = temp_migrations_dir / "001_init.sql"
        migration1.write_text("CREATE TABLE test (id INTEGER);")

        # Create an invalid migration
        migration2 = temp_migrations_dir / "002_invalid.sql"
        migration2.write_text("INVALID SQL SYNTAX;")

        # Try to apply migrations - should fail on second one
        with pytest.raises(sqlite3.OperationalError):
            apply_migrations(temp_db, temp_migrations_dir)

        # Verify only first migration was tracked
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM _migrations")
        count = cursor.fetchone()[0]
        conn.close()

        # Should have tracked first migration before failing on second
        assert count == 1

    def test_apply_migrations_case_sensitive_names(
        self, temp_db, temp_migrations_dir
    ):
        """Test that migration names are case-sensitive."""
        migration_file = temp_migrations_dir / "001_Init.sql"
        migration_file.write_text("CREATE TABLE test (id INTEGER);")

        apply_migrations(temp_db, temp_migrations_dir)

        applied = get_applied_migrations(temp_db)
        assert "001_Init.sql" in applied
