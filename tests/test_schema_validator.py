"""
Test suite for schema validator - schema validation for resume safety.

Follows TDD: tests written first, then implementation.
"""

import sqlite3
import tempfile
from pathlib import Path
import pytest

from schema_validator import (
    inspect_schema,
    compute_expected_schema,
    schema_matches,
    validate_resume_schema,
)


class TestSchemaValidator:
    """Test cases for schema validation functions."""

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

    def test_inspect_schema_from_empty_db(self):
        """Test inspect_schema on a non-existent database."""
        schema = inspect_schema(Path("/nonexistent/db.sqlite"))
        assert schema == {"tables": {}, "indexes": []}

    def test_inspect_schema_single_table(self, temp_db):
        """Test inspect_schema on database with single table."""
        # Create a table
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Inspect the schema
        schema = inspect_schema(temp_db)
        assert "users" in schema["tables"]
        assert set(schema["tables"]["users"]["columns"]) == {"id", "name", "email"}

    def test_inspect_schema_multiple_tables(self, temp_db):
        """Test inspect_schema on database with multiple tables."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT
            )
        """)
        conn.commit()
        conn.close()

        schema = inspect_schema(temp_db)
        assert "users" in schema["tables"]
        assert "posts" in schema["tables"]
        assert len(schema["tables"]) == 2

    def test_inspect_schema_with_indexes(self, temp_db):
        """Test inspect_schema extracts index information."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT
            )
        """)
        cursor.execute("CREATE INDEX idx_email ON users(email)")
        conn.commit()
        conn.close()

        schema = inspect_schema(temp_db)
        assert "idx_email" in schema["indexes"]

    def test_compute_expected_schema_empty_migrations(self, temp_migrations_dir):
        """Test compute_expected_schema with no migrations."""
        schema = compute_expected_schema(temp_migrations_dir)
        assert schema == {"tables": {}, "indexes": []}

    def test_compute_expected_schema_single_migration(self, temp_migrations_dir):
        """Test compute_expected_schema with single migration."""
        migration_file = temp_migrations_dir / "001_create_users.sql"
        migration_file.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT
            )
        """)

        schema = compute_expected_schema(temp_migrations_dir)
        assert "users" in schema["tables"]
        assert set(schema["tables"]["users"]["columns"]) == {"id", "name", "email"}

    def test_compute_expected_schema_multiple_migrations(self, temp_migrations_dir):
        """Test compute_expected_schema with multiple migrations."""
        # First migration creates users table
        migration1 = temp_migrations_dir / "001_create_users.sql"
        migration1.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        # Second migration creates posts table
        migration2 = temp_migrations_dir / "002_create_posts.sql"
        migration2.write_text("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT
            )
        """)

        schema = compute_expected_schema(temp_migrations_dir)
        assert "users" in schema["tables"]
        assert "posts" in schema["tables"]

    def test_compute_expected_schema_with_alter_column(self, temp_migrations_dir):
        """Test compute_expected_schema handles ALTER TABLE ADD COLUMN."""
        migration1 = temp_migrations_dir / "001_create_users.sql"
        migration1.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        migration2 = temp_migrations_dir / "002_add_email.sql"
        migration2.write_text("""
            ALTER TABLE users ADD COLUMN email TEXT
        """)

        schema = compute_expected_schema(temp_migrations_dir)
        expected_cols = schema["tables"]["users"]["columns"]
        assert "id" in expected_cols
        assert "name" in expected_cols
        assert "email" in expected_cols

    def test_schema_matches_identical_schemas(self):
        """Test schema_matches with identical schemas."""
        actual = {
            "tables": {
                "users": {"columns": ["id", "name", "email"]}
            },
            "indexes": []
        }
        expected = {
            "tables": {
                "users": {"columns": ["id", "name", "email"]}
            },
            "indexes": []
        }
        assert schema_matches(actual, expected) is True

    def test_schema_matches_actual_has_extra_columns(self):
        """Test schema_matches when actual has extra columns."""
        actual = {
            "tables": {
                "users": {"columns": ["id", "name", "email", "phone"]}
            },
            "indexes": []
        }
        expected = {
            "tables": {
                "users": {"columns": ["id", "name", "email"]}
            },
            "indexes": []
        }
        assert schema_matches(actual, expected) is True

    def test_schema_matches_actual_missing_column(self):
        """Test schema_matches fails when actual is missing expected column."""
        actual = {
            "tables": {
                "users": {"columns": ["id", "name"]}
            },
            "indexes": []
        }
        expected = {
            "tables": {
                "users": {"columns": ["id", "name", "email"]}
            },
            "indexes": []
        }
        assert schema_matches(actual, expected) is False

    def test_schema_matches_actual_missing_table(self):
        """Test schema_matches fails when actual is missing expected table."""
        actual = {
            "tables": {},
            "indexes": []
        }
        expected = {
            "tables": {
                "users": {"columns": ["id", "name"]}
            },
            "indexes": []
        }
        assert schema_matches(actual, expected) is False

    def test_schema_matches_actual_has_extra_tables(self):
        """Test schema_matches when actual has extra tables."""
        actual = {
            "tables": {
                "users": {"columns": ["id", "name"]},
                "posts": {"columns": ["id", "content"]}
            },
            "indexes": []
        }
        expected = {
            "tables": {
                "users": {"columns": ["id", "name"]}
            },
            "indexes": []
        }
        assert schema_matches(actual, expected) is True

    def test_validate_resume_schema_success(self, temp_db, temp_migrations_dir):
        """Test validate_resume_schema succeeds with matching schema."""
        # Create migration
        migration = temp_migrations_dir / "001_create_users.sql"
        migration.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        # Create matching database
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Validation should succeed
        result = validate_resume_schema(temp_db, temp_migrations_dir)
        assert result is True

    def test_validate_resume_schema_schema_mismatch(self, temp_db, temp_migrations_dir):
        """Test validate_resume_schema fails with schema mismatch."""
        # Create migration expecting users table with id, name, email
        migration = temp_migrations_dir / "001_create_users.sql"
        migration.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT,
                email TEXT
            )
        """)

        # Create database with only id and name columns
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)
        conn.commit()
        conn.close()

        # Validation should fail
        with pytest.raises(ValueError, match="Schema mismatch"):
            validate_resume_schema(temp_db, temp_migrations_dir)

    def test_validate_resume_schema_missing_table(self, temp_db, temp_migrations_dir):
        """Test validate_resume_schema fails when expected table is missing."""
        # Create migration
        migration = temp_migrations_dir / "001_create_users.sql"
        migration.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        # Create empty database (no tables)
        conn = sqlite3.connect(str(temp_db))
        conn.close()

        # Validation should fail
        with pytest.raises(ValueError, match="Schema mismatch"):
            validate_resume_schema(temp_db, temp_migrations_dir)

    def test_validate_resume_schema_nonexistent_db(self, temp_migrations_dir):
        """Test validate_resume_schema with non-existent database."""
        # Create migration
        migration = temp_migrations_dir / "001_create_users.sql"
        migration.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT
            )
        """)

        # Non-existent database should fail validation
        with pytest.raises(ValueError, match="Schema mismatch"):
            validate_resume_schema(Path("/nonexistent/db.sqlite"), temp_migrations_dir)

    def test_compute_expected_schema_handles_comments(self, temp_migrations_dir):
        """Test compute_expected_schema ignores SQL comments."""
        migration = temp_migrations_dir / "001_create_users.sql"
        migration.write_text("""
            -- This is a comment
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,  -- Primary key
                name TEXT  -- User name
            )
            /* Multi-line
               comment */
        """)

        schema = compute_expected_schema(temp_migrations_dir)
        assert "users" in schema["tables"]
        assert set(schema["tables"]["users"]["columns"]) == {"id", "name"}

    def test_compute_expected_schema_case_insensitive_keywords(self, temp_migrations_dir):
        """Test compute_expected_schema handles mixed-case SQL keywords."""
        migration = temp_migrations_dir / "001_create_users.sql"
        migration.write_text("""
            create table if not exists users (
                id integer primary key,
                name text
            )
        """)

        schema = compute_expected_schema(temp_migrations_dir)
        assert "users" in schema["tables"]
        assert set(schema["tables"]["users"]["columns"]) == {"id", "name"}

    def test_compute_expected_schema_with_multiple_alters(self, temp_migrations_dir):
        """Test compute_expected_schema with multiple ALTER TABLE statements."""
        migration1 = temp_migrations_dir / "001_create_users.sql"
        migration1.write_text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY
            )
        """)

        migration2 = temp_migrations_dir / "002_add_columns.sql"
        migration2.write_text("""
            ALTER TABLE users ADD COLUMN name TEXT;
            ALTER TABLE users ADD COLUMN email TEXT;
        """)

        schema = compute_expected_schema(temp_migrations_dir)
        expected_cols = schema["tables"]["users"]["columns"]
        assert "id" in expected_cols
        assert "name" in expected_cols
        assert "email" in expected_cols

    def test_inspect_schema_column_order_irrelevant(self, temp_db):
        """Test that column order doesn't matter for schema matching."""
        conn = sqlite3.connect(str(temp_db))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE users (
                name TEXT,
                id INTEGER PRIMARY KEY,
                email TEXT
            )
        """)
        conn.commit()
        conn.close()

        schema = inspect_schema(temp_db)
        cols = set(schema["tables"]["users"]["columns"])
        assert cols == {"id", "name", "email"}
