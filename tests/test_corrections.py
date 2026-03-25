"""
tests/test_corrections.py — Tests for behavioral corrections DB.
"""

import sqlite3
import tempfile
from pathlib import Path
import pytest


def test_init_creates_db_and_table(tmp_path):
    """Test that init_db creates the DB file and corrections table."""
    db_path = tmp_path / "test.db"
    from lib.corrections import init_db

    init_db(db_path)

    assert db_path.exists()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='corrections'"
    )
    assert cursor.fetchone() is not None
    conn.close()


def test_init_is_idempotent(tmp_path):
    """Test that calling init_db twice does not raise and does not corrupt DB."""
    db_path = tmp_path / "test.db"
    from lib.corrections import init_db

    init_db(db_path)
    init_db(db_path)  # second call must not raise

    assert db_path.exists()


def test_init_creates_parent_directory(tmp_path):
    """Test that init_db creates parent directories if they don't exist."""
    db_path = tmp_path / "nested" / "dir" / "test.db"
    from lib.corrections import init_db

    init_db(db_path)

    assert db_path.exists()


def test_corrections_table_has_required_columns(tmp_path):
    """Test that the corrections table has all required columns."""
    db_path = tmp_path / "test.db"
    from lib.corrections import init_db

    init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA table_info(corrections)")
    columns = {row[1] for row in cursor.fetchall()}

    required_columns = {
        'id', 'agent', 'class', 'gap', 'rule', 'source', 'source_comment_id',
        'status', 'target_hint', 'integrated_commit', 'integrated_file',
        'created_at', 'updated_at'
    }
    assert required_columns.issubset(columns), f"Missing columns: {required_columns - columns}"

    conn.close()


def test_corrections_table_id_is_primary_key(tmp_path):
    """Test that id column is the primary key."""
    db_path = tmp_path / "test.db"
    from lib.corrections import init_db

    init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute("PRAGMA table_info(corrections)")
    columns = {row[1]: row for row in cursor.fetchall()}

    # pk=1 means it's the primary key (1-indexed)
    assert columns['id'][5] == 1, "id column should be primary key"

    conn.close()


def test_class_column_has_check_constraint(tmp_path):
    """Test that class column only accepts 'project-pattern' or 'general'."""
    db_path = tmp_path / "test.db"
    from lib.corrections import init_db

    init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Insert valid values should succeed
    cursor.execute(
        "INSERT INTO corrections (id, agent, class, gap, rule, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("test-1", "chief-builder", "project-pattern", "gap1", "rule1", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
    )
    conn.commit()

    cursor.execute(
        "INSERT INTO corrections (id, agent, class, gap, rule, created_at, updated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("test-2", "dev", "general", "gap2", "rule2", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
    )
    conn.commit()

    # Insert invalid value should fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO corrections (id, agent, class, gap, rule, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("test-3", "dev", "invalid-class", "gap3", "rule3", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        conn.commit()

    conn.close()


def test_status_column_has_check_constraint(tmp_path):
    """Test that status column only accepts valid status values."""
    db_path = tmp_path / "test.db"
    from lib.corrections import init_db

    init_db(db_path)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Insert valid values should succeed
    valid_statuses = ['active', 'inactive', 'pending_integration', 'integrated']
    for i, status in enumerate(valid_statuses):
        cursor.execute(
            "INSERT INTO corrections (id, agent, class, gap, rule, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (f"test-{i}", "chief-builder", "general", "gap", "rule", status, "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
    conn.commit()

    # Insert invalid status should fail
    with pytest.raises(sqlite3.IntegrityError):
        cursor.execute(
            "INSERT INTO corrections (id, agent, class, gap, rule, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("test-invalid", "dev", "general", "gap", "rule", "invalid-status", "2026-01-01T00:00:00Z", "2026-01-01T00:00:00Z")
        )
        conn.commit()

    conn.close()


def test_generate_id_basic():
    from lib.corrections import generate_id
    # chief-builder, project instavid, ticket 7, rule about rate limits
    # "ratelimit" is a single token — slugify picks it as the first non-stop keyword
    id_ = generate_id("chief-builder", "instavid", "7", "always check ratelimit before API design")
    assert id_ == "cb_instavid_7_ratelimit"


def test_generate_id_star_agent():
    from lib.corrections import generate_id
    # "first" is the first non-stop word (ask/who are stop words)
    id_ = generate_id("*", "global", "manual", "ask who the first user is")
    assert id_ == "all_global_manual_first"


def test_generate_id_strips_stopwords():
    from lib.corrections import generate_id
    id_ = generate_id("dev", "myapp", "12", "always verify the migration exists")
    assert id_ == "dev_myapp_12_migration"


def test_generate_id_max_lengths():
    from lib.corrections import generate_id
    id_ = generate_id("chief-builder", "averylongprojectname", "42", "superlongkeywordthatexceedslimit")
    parts = id_.split("_")
    assert len(parts[1]) <= 12  # project slug
    assert len(parts[3]) <= 12  # keyword


def test_generate_id_collision(tmp_path):
    import sqlite3
    from lib.corrections import generate_id, init_db
    db = tmp_path / "test.db"
    init_db(db)
    conn = sqlite3.connect(str(db))
    base = generate_id("dev", "proj", "1", "check migration")
    conn.execute(
        "INSERT INTO corrections (id, agent, class, gap, rule, status, created_at, updated_at) "
        "VALUES (?, 'dev', 'general', 'gap', 'rule', 'active', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        (base,)
    )
    conn.commit()
    conn.close()
    id2 = generate_id("dev", "proj", "1", "check migration", db_path=db)
    assert id2 == base + "_2"


def test_generate_id_fallback_with_all_stopwords():
    from lib.corrections import generate_id
    id_ = generate_id("dev", "proj", "1", "the a or for")
    assert id_.endswith("_misc"), f"Expected 'misc' keyword, got {id_}"


def test_generate_id_fallback_with_short_words():
    from lib.corrections import generate_id
    id_ = generate_id("dev", "proj", "1", "ab cd ef")
    assert id_.endswith("_misc"), f"Expected 'misc' keyword, got {id_}"
