# /cao-worker Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `/cao-worker` skill for multi-agent parallel development with atomic claim mechanism, schema validation, and graceful error recovery.

**Architecture:** Single skill that acts as worker orchestrator—polls GitHub for "to-dev" labeled tickets, claims via atomic branch push, applies migrations, implements features, creates PR, and handles resume/ghost detection. Uses 5-minute polling interval, 5-minute heartbeat with 20-minute ghost timeout, and validates schema before resuming work.

**Tech Stack:** Claude API (Sonnet), GitHub CLI + custom MCP, Python for DB operations, SQLite for per-agent databases, JSONL for agent logs.

---

## File Structure

**New Files:**
- `plugins/claude-agents-orchestrator/lib/__init__.py` — Python package marker
- `plugins/claude-agents-orchestrator/lib/agent_namer.py` — Agent name generation
- `plugins/claude-agents-orchestrator/lib/heartbeat.py` — .lock file management (5-min interval)
- `plugins/claude-agents-orchestrator/lib/schema_validator.py` — Resume schema validation
- `plugins/claude-agents-orchestrator/lib/github_notifier.py` — Label cleanup + comments with retry
- `plugins/claude-agents-orchestrator/lib/migration_tool_detector.py` — Detect migration tool
- `plugins/claude-agents-orchestrator/lib/migrations.py` — DB-agnostic migration runner
- `plugins/claude-agents-orchestrator/lib/worker.py` — Worker class (claim + lifecycle)
- `plugins/claude-agents-orchestrator/lib/worker_main.py` — Orchestrator entrypoint
- `plugins/claude-agents-orchestrator/.githooks/pre-commit` — Idempotency hook
- `plugins/claude-agents-orchestrator/conftest.py` — Pytest fixtures (Python path)
- `plugins/claude-agents-orchestrator/skills/cao-worker.md` — Main skill definition
- `tests/__init__.py` — Test package marker
- `tests/test_heartbeat.py` — Heartbeat tests
- `tests/test_schema_validator.py` — Schema validation tests
- `tests/test_github_notifier.py` — GitHub notification tests
- `tests/test_migration_tool_detector.py` — Tool detection tests
- `tests/test_worker.py` — Worker lifecycle tests
- `tests/test_worker_integration.py` — End-to-end tests

**Modified Files:**
- `plugin.json` — Add /cao-worker skill + required dependencies
- `SETUP.sh` — Install pre-commit hook
- `CLAUDE.md` (template) — Add migration requirements section

---

## Setup Task: Python Package Structure

### Task 0: Create Package Directories & Init Files

- [ ] **Step 1: Create lib directory and __init__.py**

```bash
mkdir -p plugins/claude-agents-orchestrator/lib plugins/claude-agents-orchestrator/tests
touch plugins/claude-agents-orchestrator/lib/__init__.py
touch plugins/claude-agents-orchestrator/tests/__init__.py
```

- [ ] **Step 2: Create conftest.py for pytest path resolution**

```python
# plugins/claude-agents-orchestrator/conftest.py
import sys
from pathlib import Path

# Add lib to Python path so imports work
lib_path = Path(__file__).parent / "lib"
sys.path.insert(0, str(lib_path))
```

- [ ] **Step 3: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/__init__.py \
        plugins/claude-agents-orchestrator/tests/__init__.py \
        plugins/claude-agents-orchestrator/conftest.py
git commit -m "setup: create Python package structure for worker lib"
```

---

### Task 0.1: Implement Agent Name Generator

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/agent_namer.py`
- Test: Add to `tests/conftest.py`

- [ ] **Step 1: Write test for name generation**

```python
# In tests/conftest.py (new section)
def test_generate_agent_name():
    """Generate unique agent names (e.g., proud-falcon)."""
    from agent_namer import generate_agent_name

    name1 = generate_agent_name()
    name2 = generate_agent_name()

    assert "-" in name1  # Format: adjective-animal
    assert name1 != name2  # Unique each time
    assert len(name1) < 30  # Reasonable length

def test_agent_name_is_safe():
    """Agent names only contain alphanumerics and hyphens."""
    from agent_namer import generate_agent_name
    import re

    name = generate_agent_name()
    assert re.match(r"^[a-z0-9\-]+$", name)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/conftest.py::test_generate_agent_name -v
```

Expected: FAIL

- [ ] **Step 3: Implement agent namer**

```python
# plugins/claude-agents-orchestrator/lib/agent_namer.py
import random

ADJECTIVES = [
    "proud", "swift", "clever", "bold", "quiet",
    "eager", "gentle", "nimble", "smart", "strong"
]

ANIMALS = [
    "falcon", "fox", "owl", "eagle", "raven",
    "wolf", "lynx", "tiger", "cobra", "hawk"
]

def generate_agent_name() -> str:
    """
    Generate random agent name (adjective-animal format).

    Examples: proud-falcon, swift-eagle, clever-fox
    """
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    return f"{adj}-{animal}"
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/conftest.py::test_generate_agent_name -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/agent_namer.py tests/conftest.py
git commit -m "feat: add agent name generator"
```

---

## Critical Fix #1: Heartbeat Timing (Issue #1)

### Task 1.1: Implement Heartbeat Manager

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/heartbeat.py`
- Test: `tests/test_heartbeat.py`

- [ ] **Step 1: Write test for heartbeat creation**

```python
# tests/test_heartbeat.py
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

def test_create_lock_file():
    """Lock file contains agent name, claimed time, heartbeat time."""
    from worker.lib.heartbeat import create_lock_file

    lock_path = Path("/tmp/test/.lock-34-auth")
    create_lock_file(lock_path, agent_name="proud-falcon")

    assert lock_path.exists()
    data = json.loads(lock_path.read_text())
    assert data["agent"] == "proud-falcon"
    assert "claimed_at" in data
    assert "last_heartbeat" in data

def test_update_heartbeat():
    """Heartbeat timestamp updates without changing claimed_at."""
    from worker.lib.heartbeat import create_lock_file, update_heartbeat

    lock_path = Path("/tmp/test/.lock-34-auth")
    create_lock_file(lock_path, agent_name="proud-falcon")

    original_data = json.loads(lock_path.read_text())
    claimed_at = original_data["claimed_at"]

    time.sleep(0.1)
    update_heartbeat(lock_path)

    new_data = json.loads(lock_path.read_text())
    assert new_data["claimed_at"] == claimed_at
    assert new_data["last_heartbeat"] > original_data["last_heartbeat"]

def test_is_ghost_claim():
    """Detect ghost claim: last_heartbeat > 20 minutes old."""
    from worker.lib.heartbeat import create_lock_file, is_ghost_claim

    lock_path = Path("/tmp/test/.lock-34-auth")
    create_lock_file(lock_path, agent_name="proud-falcon")

    # Recent heartbeat: not a ghost
    assert not is_ghost_claim(lock_path, timeout_seconds=1200)  # 20 min

    # Simulate old heartbeat (modify directly)
    data = json.loads(lock_path.read_text())
    data["last_heartbeat"] = (datetime.now().timestamp() - 1300)  # 21+ min ago
    lock_path.write_text(json.dumps(data))

    assert is_ghost_claim(lock_path, timeout_seconds=1200)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_heartbeat.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3a: Create lock file structure**

```python
# plugins/claude-agents-orchestrator/lib/heartbeat.py
import json
from datetime import datetime
from pathlib import Path

def create_lock_file(lock_path: Path, agent_name: str) -> None:
    """Create .lock file with agent metadata."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    now = datetime.now().timestamp()
    data = {
        "agent": agent_name,
        "claimed_at": now,
        "last_heartbeat": now
    }

    lock_path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 3b: Add heartbeat update function**

```python
# Append to plugins/claude-agents-orchestrator/lib/heartbeat.py

def update_heartbeat(lock_path: Path) -> None:
    """Update last_heartbeat timestamp without changing claimed_at."""
    if not lock_path.exists():
        raise FileNotFoundError(f"Lock file not found: {lock_path}")

    data = json.loads(lock_path.read_text())
    data["last_heartbeat"] = datetime.now().timestamp()
    lock_path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 3c: Add ghost detection function**

```python
# Append to plugins/claude-agents-orchestrator/lib/heartbeat.py

def is_ghost_claim(lock_path: Path, timeout_seconds: int = 1200) -> bool:
    """
    Check if claim is stale (agent dead/crashed).

    Args:
        lock_path: Path to .lock file
        timeout_seconds: How long before considering ghost (default: 20 min)

    Returns:
        True if last_heartbeat is older than timeout
    """
    if not lock_path.exists():
        return False

    data = json.loads(lock_path.read_text())
    last_heartbeat = data["last_heartbeat"]
    now = datetime.now().timestamp()

    return (now - last_heartbeat) > timeout_seconds

def delete_lock_file(lock_path: Path) -> None:
    """Delete .lock file (call after PR created or ghost cleaned)."""
    if lock_path.exists():
        lock_path.unlink()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_heartbeat.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/heartbeat.py \
        tests/test_heartbeat.py
git commit -m "feat: add heartbeat manager with 5-min interval, 20-min timeout"
```

---

### Task 1.2: Integrate Heartbeat into Worker Loop

**Files:**
- Modify: `plugins/claude-agents-orchestrator/lib/worker.py:main_loop`
- Test: `tests/test_worker.py`

- [ ] **Step 1: Write test for worker heartbeat loop**

```python
# tests/test_worker.py (new section)
def test_worker_updates_heartbeat_every_5_minutes():
    """Worker updates .lock file every 5 minutes while working."""
    from worker.lib.worker import Worker
    from worker.lib.heartbeat import is_ghost_claim
    from unittest.mock import MagicMock, patch
    import time

    worker = Worker(agent_name="test-agent", repo="test/repo")
    lock_path = worker.lock_path_for_ticket(34)

    # Simulate work cycle
    with patch('worker.lib.worker.Worker._do_work') as mock_work:
        mock_work.side_effect = [None, None]  # Two cycles

        with patch('time.sleep') as mock_sleep:
            # First cycle: create lock
            worker.run_work_cycle(ticket_id=34)
            assert lock_path.exists()

            first_heartbeat = json.loads(lock_path.read_text())["last_heartbeat"]

            time.sleep(0.1)

            # Second cycle (simulated 5 min later): update heartbeat
            worker.run_work_cycle(ticket_id=34)
            second_heartbeat = json.loads(lock_path.read_text())["last_heartbeat"]

            assert second_heartbeat > first_heartbeat
            assert not is_ghost_claim(lock_path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py::test_worker_updates_heartbeat_every_5_minutes -v
```

Expected: FAIL (Worker class not fully implemented yet)

- [ ] **Step 3: Add heartbeat update to main worker loop**

```python
# plugins/claude-agents-orchestrator/lib/worker.py (add to Worker class)
import time
from .heartbeat import create_lock_file, update_heartbeat, is_ghost_claim, delete_lock_file

class Worker:
    def __init__(self, agent_name: str, repo: str):
        self.agent_name = agent_name
        self.repo = repo
        self.heartbeat_interval = 300  # 5 minutes
        self.ghost_timeout = 1200  # 20 minutes
        self.last_heartbeat_time = 0

    def lock_path_for_ticket(self, ticket_id: int) -> Path:
        """Return path to .lock file for ticket."""
        return Path(f"./{ticket_id}-{self.agent_name}/.lock-{ticket_id}")

    def run_work_cycle(self, ticket_id: int):
        """Run one work cycle: heartbeat + do work."""
        lock_path = self.lock_path_for_ticket(ticket_id)

        # Create lock on first run
        if not lock_path.exists():
            create_lock_file(lock_path, self.agent_name)
            self.last_heartbeat_time = time.time()

        # Update heartbeat if 5 minutes have passed
        now = time.time()
        if (now - self.last_heartbeat_time) > self.heartbeat_interval:
            update_heartbeat(lock_path)
            self.last_heartbeat_time = now

        # Do actual work
        self._do_work(ticket_id)

    def _do_work(self, ticket_id: int):
        """Placeholder for actual work."""
        pass
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_worker.py::test_worker_updates_heartbeat_every_5_minutes -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/worker.py tests/test_worker.py
git commit -m "feat: integrate heartbeat updates to worker main loop (5-min interval)"
```

---

## Critical Fix #2: Polling Interval (Issue #2)

### Task 2.1: Document and Enforce 5-Minute Polling

**Files:**
- Modify: `plugins/claude-agents-orchestrator/skills/cao-worker.md`
- Modify: `plugins/claude-agents-orchestrator/CLAUDE.md` (template)

- [ ] **Step 1: Add polling interval documentation to skill**

```markdown
# /cao-worker Skill

## Configuration

### Polling Interval

**Required:** 5-minute minimum polling interval

**Rationale:**
- 20 agents × 5-min interval = 240 label queries/hr
- Well within GitHub's 5000 req/hr rate limit
- Balances latency (max 5 min wait for claim) vs API usage

**Configuration:**
Set in environment or CLAUDE.md:
```yaml
worker:
  polling_interval_seconds: 300  # 5 minutes
  max_agents: 20
  ghost_timeout_seconds: 1200  # 20 minutes
```

**Do not set below 5 minutes.** Lower values risk GitHub API exhaustion.
```

- [ ] **Step 2: Add to project CLAUDE.md template**

```markdown
# Project CLAUDE.md Template — Multi-Agent Section

## Multi-Agent Worker Configuration

**Polling Interval:** 5 minutes (required minimum)
**Max Concurrent Agents:** 10 (safe), 20 (requires API caching)
**Ghost Claim Timeout:** 20 minutes

When using `/cao-worker`:
- Ensure polling_interval ≥ 300 seconds
- Start with 5-10 agents; scale to 20 after monitoring
- Monitor agent logs in `~/.claude/projects/<project>/logs/`
```

- [ ] **Step 3: Commit**

```bash
git add plugins/claude-agents-orchestrator/skills/cao-worker.md
git commit -m "docs: add 5-minute polling interval requirement"
```

---

## Critical Fix #3: Schema Validation on Resume (Issue #3)

### Task 3.1: Implement Schema Inspector

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/schema_validator.py`
- Test: `tests/test_schema_validator.py`

- [ ] **Step 1: Write test for schema inspection**

```python
# tests/test_schema_validator.py
import sqlite3
from pathlib import Path
from worker.lib.schema_validator import (
    inspect_schema,
    compute_expected_schema,
    schema_matches
)

def test_inspect_schema_from_sqlite():
    """Extract table/column info from agent's SQLite DB."""
    db_path = Path("/tmp/test.db")

    # Create test DB
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INT, email TEXT, phone TEXT)")
    cursor.execute("CREATE INDEX idx_email ON users(email)")
    conn.commit()
    conn.close()

    schema = inspect_schema(db_path)

    assert "users" in schema["tables"]
    assert set(schema["tables"]["users"]["columns"]) == {"id", "email", "phone"}
    assert "idx_email" in schema["indexes"]

def test_compute_expected_schema_from_migrations():
    """Parse migrations/ directory and compute expected schema."""
    migrations_dir = Path("/tmp/migrations")
    migrations_dir.mkdir(exist_ok=True)

    # Create test migrations
    (migrations_dir / "0001-init.sql").write_text(
        "CREATE TABLE IF NOT EXISTS users (id INT, email TEXT);"
    )
    (migrations_dir / "0002-add-phone.sql").write_text(
        "ALTER TABLE users ADD COLUMN phone TEXT;"
    )

    expected = compute_expected_schema(migrations_dir)

    assert "users" in expected["tables"]
    assert "email" in expected["tables"]["users"]["columns"]
    assert "phone" in expected["tables"]["users"]["columns"]

def test_schema_mismatch_detection():
    """Detect when agent's DB is missing columns from migrations."""
    db_path = Path("/tmp/test.db")

    # Agent's DB: only has 2 columns
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INT, email TEXT)")
    conn.commit()
    conn.close()

    migrations_dir = Path("/tmp/migrations")
    (migrations_dir / "0001-init.sql").write_text(
        "CREATE TABLE IF NOT EXISTS users (id INT, email TEXT, phone TEXT);"
    )

    actual = inspect_schema(db_path)
    expected = compute_expected_schema(migrations_dir)

    assert not schema_matches(actual, expected)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_schema_validator.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Implement schema validator**

```python
# plugins/claude-agents-orchestrator/lib/schema_validator.py
import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Set

def inspect_schema(db_path: Path) -> Dict:
    """
    Extract schema from SQLite DB.

    Returns:
        {
            "tables": {
                "users": {"columns": ["id", "email", "phone"]}
            },
            "indexes": ["idx_email", ...]
        }
    """
    if not db_path.exists():
        return {"tables": {}, "indexes": []}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {}
    for (table_name,) in cursor.fetchall():
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        tables[table_name] = {"columns": columns}

    # Get indexes
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = [row[0] for row in cursor.fetchall()]

    conn.close()

    return {"tables": tables, "indexes": indexes}

def compute_expected_schema(migrations_dir: Path) -> Dict:
    """
    Parse all migrations in order and compute expected schema.

    Parses CREATE TABLE and ALTER TABLE statements.
    Returns same format as inspect_schema().
    """
    if not migrations_dir.exists():
        return {"tables": {}, "indexes": []}

    tables = {}
    indexes = []

    # Process migrations in order (0001, 0002, ...)
    migration_files = sorted(migrations_dir.glob("*.sql"))

    for mig_file in migration_files:
        content = mig_file.read_text()

        # Parse CREATE TABLE
        create_table_pattern = r'CREATE TABLE IF NOT EXISTS (\w+)\s*\((.*?)\);'
        for match in re.finditer(create_table_pattern, content, re.IGNORECASE):
            table_name = match.group(1)
            columns_str = match.group(2)

            # Extract column names
            columns = []
            for col_def in columns_str.split(','):
                col_name = col_def.strip().split()[0]
                columns.append(col_name)

            tables[table_name] = {"columns": columns}

        # Parse ALTER TABLE ADD COLUMN
        alter_pattern = r'ALTER TABLE\s+(\w+)\s+ADD COLUMN\s+(\w+)'
        for match in re.finditer(alter_pattern, content, re.IGNORECASE):
            table_name = match.group(1)
            col_name = match.group(2)

            if table_name in tables:
                if col_name not in tables[table_name]["columns"]:
                    tables[table_name]["columns"].append(col_name)

        # Parse CREATE INDEX
        create_index_pattern = r'CREATE INDEX IF NOT EXISTS (\w+)'
        for match in re.finditer(create_index_pattern, content, re.IGNORECASE):
            index_name = match.group(1)
            if index_name not in indexes:
                indexes.append(index_name)

    return {"tables": tables, "indexes": indexes}

def schema_matches(actual: Dict, expected: Dict) -> bool:
    """
    Check if actual schema matches expected schema.

    Returns True if:
    - All expected tables exist with expected columns
    - All expected indexes exist

    (Allows extra columns/tables in actual, but not missing ones)
    """
    # Check tables
    for table_name, expected_cols in expected.get("tables", {}).items():
        if table_name not in actual.get("tables", {}):
            return False

        actual_cols = set(actual["tables"][table_name]["columns"])
        expected_col_set = set(expected_cols["columns"])

        if not expected_col_set.issubset(actual_cols):
            return False

    # Check indexes
    expected_indexes = set(expected.get("indexes", []))
    actual_indexes = set(actual.get("indexes", []))

    if not expected_indexes.issubset(actual_indexes):
        return False

    return True

def validate_resume_schema(db_path: Path, migrations_dir: Path) -> bool:
    """
    Check if agent's DB schema matches expected schema from migrations.

    Call before resuming work.

    Raises ValueError if mismatch detected.
    """
    actual = inspect_schema(db_path)
    expected = compute_expected_schema(migrations_dir)

    if not schema_matches(actual, expected):
        raise ValueError(
            f"Schema mismatch on resume.\n"
            f"Agent DB: {actual}\n"
            f"Expected: {expected}\n"
            f"ERROR: Agent's DB is out of sync with migrations/. "
            f"Manual intervention required."
        )

    return True
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_schema_validator.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/schema_validator.py \
        tests/test_schema_validator.py
git commit -m "feat: add schema validator for resume safety"
```

### Task 3.2: Integrate Schema Validation into Worker Resume

**Files:**
- Modify: `plugins/claude-agents-orchestrator/lib/worker.py:resume_work`

- [ ] **Step 1: Write test for resume with schema validation**

```python
# tests/test_worker.py (add to existing)
def test_worker_validates_schema_before_resume():
    """Resume fails if agent's DB schema doesn't match migrations."""
    from worker.lib.worker import Worker
    from worker.lib.schema_validator import validate_resume_schema
    from pathlib import Path
    import sqlite3

    worker = Worker(agent_name="test", repo="test/repo")

    # Setup: old DB with only 2 columns, migrations/ has 3
    db_path = Path("/tmp/test.db")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE users (id INT, email TEXT)")  # Missing phone
    conn.commit()
    conn.close()

    migrations_dir = Path("/tmp/migrations")
    migrations_dir.mkdir(exist_ok=True)
    (migrations_dir / "0001-init.sql").write_text(
        "CREATE TABLE IF NOT EXISTS users (id INT, email TEXT, phone TEXT);"
    )

    # Resume should fail
    with pytest.raises(ValueError, match="Schema mismatch"):
        worker.resume_work(ticket_id=34, db_path=db_path, migrations_dir=migrations_dir)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py::test_worker_validates_schema_before_resume -v
```

Expected: FAIL

- [ ] **Step 3: Add schema validation to resume_work**

```python
# plugins/claude-agents-orchestrator/lib/worker.py (add method)
from .schema_validator import validate_resume_schema

class Worker:
    def resume_work(self, ticket_id: int, db_path: Path, migrations_dir: Path):
        """
        Resume work on existing ticket.

        First validates schema, then applies any new migrations.

        Raises ValueError if schema mismatch detected.
        """
        # CRITICAL: Validate schema before proceeding
        validate_resume_schema(db_path, migrations_dir)

        # Schema is valid, proceed with migrations and work
        self.apply_migrations(ticket_id, db_path, migrations_dir)
        self.continue_implementation(ticket_id)

    def apply_migrations(self, ticket_id: int, db_path: Path, migrations_dir: Path):
        """Apply any new migrations that landed since last run."""
        from .migrations import apply_migrations
        apply_migrations(db_path, migrations_dir)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_worker.py::test_worker_validates_schema_before_resume -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/worker.py
git commit -m "feat: validate schema before resuming work"
```

---

## Critical Fix #4: Label Cleanup with Retry (Issue #4)

### Task 4.1: Implement Retry Logic for GitHub Notifications

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/github_notifier.py`
- Test: `tests/test_github_notifier.py`

- [ ] **Step 1: Write test for label update with retry**

```python
# tests/test_github_notifier.py
import pytest
from unittest.mock import MagicMock, patch, call
from worker.lib.github_notifier import (
    remove_labels_with_retry,
    add_labels_with_retry,
    post_comment
)

def test_remove_labels_succeeds_first_try():
    """Remove labels successfully on first attempt."""
    with patch('worker.lib.github_notifier.run_gh_cli') as mock_gh:
        mock_gh.return_value = ""

        remove_labels_with_retry(
            repo="user/repo",
            issue_number=34,
            labels=["dev-in-progress", "agent/proud-falcon"],
            max_retries=3
        )

        assert mock_gh.called
        assert mock_gh.call_count == 1

def test_remove_labels_retries_on_transient_error():
    """Retry label removal up to 3 times on transient failure."""
    with patch('worker.lib.github_notifier.run_gh_cli') as mock_gh:
        # First 2 attempts fail, 3rd succeeds
        mock_gh.side_effect = [
            Exception("API rate limit"),
            Exception("Connection timeout"),
            ""
        ]

        remove_labels_with_retry(
            repo="user/repo",
            issue_number=34,
            labels=["dev-in-progress"],
            max_retries=3
        )

        assert mock_gh.call_count == 3

def test_remove_labels_fails_after_max_retries():
    """Raise error if all retries fail."""
    with patch('worker.lib.github_notifier.run_gh_cli') as mock_gh:
        mock_gh.side_effect = Exception("Permanent error")

        with pytest.raises(Exception, match="Failed to remove labels after 3 retries"):
            remove_labels_with_retry(
                repo="user/repo",
                issue_number=34,
                labels=["dev-in-progress"],
                max_retries=3
            )

def test_add_labels_with_retry():
    """Add labels with retry logic."""
    with patch('worker.lib.github_notifier.run_gh_cli') as mock_gh:
        mock_gh.return_value = ""

        add_labels_with_retry(
            repo="user/repo",
            issue_number=34,
            labels=["to-test"],
            max_retries=3
        )

        assert mock_gh.call_count == 1

def test_cleanup_labels_after_pr():
    """Remove old labels and add new ones (idempotent)."""
    with patch('worker.lib.github_notifier.remove_labels_with_retry') as mock_rm:
        with patch('worker.lib.github_notifier.add_labels_with_retry') as mock_add:
            from worker.lib.github_notifier import cleanup_labels_after_pr

            cleanup_labels_after_pr(
                repo="user/repo",
                issue_number=34,
                agent_name="proud-falcon"
            )

            # Should remove old labels
            mock_rm.assert_called_once()
            removed = mock_rm.call_args[1]["labels"]
            assert "dev-in-progress" in removed
            assert "agent/proud-falcon" in removed

            # Should add new label
            mock_add.assert_called_once()
            added = mock_add.call_args[1]["labels"]
            assert "to-test" in added
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_github_notifier.py -v
```

Expected: FAIL (module doesn't exist)

- [ ] **Step 3: Implement GitHub notifier with retry**

```python
# plugins/claude-agents-orchestrator/lib/github_notifier.py
import time
import subprocess
from typing import List

def run_gh_cli(args: List[str]) -> str:
    """
    Run GitHub CLI command.

    Returns stdout on success.
    Raises Exception on failure.
    """
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(f"gh command failed: {result.stderr}")

    return result.stdout

def remove_labels_with_retry(
    repo: str,
    issue_number: int,
    labels: List[str],
    max_retries: int = 3,
    retry_delay: int = 5
) -> None:
    """
    Remove labels from GitHub issue with retry logic.

    Args:
        repo: "owner/repo"
        issue_number: GitHub issue number
        labels: List of label names to remove
        max_retries: Number of retry attempts (default: 3)
        retry_delay: Seconds between retries (default: 5)

    Raises:
        Exception if all retries fail
    """
    for attempt in range(max_retries):
        try:
            for label in labels:
                run_gh_cli([
                    "issue",
                    "edit",
                    str(issue_number),
                    f"--repo={repo}",
                    f"--remove-label={label}"
                ])
            return  # Success
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(
                    f"Failed to remove labels after {max_retries} retries: {e}"
                )

            time.sleep(retry_delay)  # Wait before retry

def add_labels_with_retry(
    repo: str,
    issue_number: int,
    labels: List[str],
    max_retries: int = 3,
    retry_delay: int = 5
) -> None:
    """
    Add labels to GitHub issue with retry logic.

    Similar structure to remove_labels_with_retry.
    """
    for attempt in range(max_retries):
        try:
            run_gh_cli([
                "issue",
                "edit",
                str(issue_number),
                f"--repo={repo}",
                f"--add-label={','.join(labels)}"
            ])
            return  # Success
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(
                    f"Failed to add labels after {max_retries} retries: {e}"
                )

            time.sleep(retry_delay)

def post_comment(
    repo: str,
    issue_number: int,
    body: str,
    max_retries: int = 3
) -> None:
    """Post comment to GitHub issue with retry logic."""
    for attempt in range(max_retries):
        try:
            run_gh_cli([
                "issue",
                "comment",
                str(issue_number),
                f"--repo={repo}",
                f"--body={body}"
            ])
            return
        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(
                    f"Failed to post comment after {max_retries} retries: {e}"
                )

            time.sleep(5)

def cleanup_labels_after_pr(
    repo: str,
    issue_number: int,
    agent_name: str
) -> None:
    """
    Clean up labels after PR creation.

    1. Remove: dev-in-progress, agent/{name}
    2. Add: to-test
    3. Post: "✅ PR ready for testing"
    """
    # Remove old labels
    remove_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=[
            "dev-in-progress",
            f"agent/{agent_name}"
        ]
    )

    # Add new label
    add_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["to-test"]
    )

    # Post comment
    post_comment(
        repo=repo,
        issue_number=issue_number,
        body="✅ PR ready for testing. Claim released."
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_github_notifier.py -v
```

Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/github_notifier.py \
        tests/test_github_notifier.py
git commit -m "feat: add retry logic for GitHub label cleanup"
```

---

## Critical Fix #5: Migration Tool Detection (Issue #5)

### Task 5.1: Implement Migration Tool Detection

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/migration_tool_detector.py`
- Test: `tests/test_migration_tool_detector.py`

- [ ] **Step 1: Write test for tool detection**

```python
# tests/test_migration_tool_detector.py
from pathlib import Path
import pytest
from worker.lib.migration_tool_detector import (
    detect_migration_tool,
    MigrationTool,
    validate_tool_installed
)

def test_detect_prisma_from_claude_md():
    """Detect Prisma when CLAUDE.md mentions Prisma."""
    claude_md = Path("/tmp/CLAUDE.md")
    claude_md.write_text(
        "# My Project\n"
        "Uses Prisma for migrations\n"
        "Run: `prisma migrate deploy`"
    )

    tool = detect_migration_tool(claude_md.parent)
    assert tool == MigrationTool.PRISMA

def test_detect_alembic_from_claude_md():
    """Detect Alembic when mentioned in CLAUDE.md."""
    claude_md = Path("/tmp/CLAUDE.md")
    claude_md.write_text("Uses Alembic for database migrations")

    tool = detect_migration_tool(claude_md.parent)
    assert tool == MigrationTool.ALEMBIC

def test_detect_flyway_from_claude_md():
    """Detect Flyway."""
    claude_md = Path("/tmp/CLAUDE.md")
    claude_md.write_text("Migration tool: Flyway")

    tool = detect_migration_tool(claude_md.parent)
    assert tool == MigrationTool.FLYWAY

def test_default_to_sql_migrations():
    """Default to SQL when no tool mentioned."""
    claude_md = Path("/tmp/CLAUDE.md")
    claude_md.write_text("# My Project\nNo migrations section")

    tool = detect_migration_tool(claude_md.parent)
    assert tool == MigrationTool.SQL

def test_validate_prisma_installed():
    """Check if Prisma CLI is installed."""
    from unittest.mock import patch

    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0

        validate_tool_installed(MigrationTool.PRISMA)

        # Should call `prisma --version`
        assert mock_run.called

def test_prisma_not_installed_raises_error():
    """Raise error if Prisma not installed."""
    from unittest.mock import patch

    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 127  # Command not found

        with pytest.raises(RuntimeError, match="Prisma not installed"):
            validate_tool_installed(MigrationTool.PRISMA)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_migration_tool_detector.py -v
```

Expected: FAIL

- [ ] **Step 3: Implement tool detector**

```python
# plugins/claude-agents-orchestrator/lib/migration_tool_detector.py
import subprocess
from enum import Enum
from pathlib import Path
from typing import Optional

class MigrationTool(Enum):
    PRISMA = "prisma"
    ALEMBIC = "alembic"
    FLYWAY = "flyway"
    SQL = "sql"  # Default: migrations/ directory

def detect_migration_tool(project_root: Path) -> MigrationTool:
    """
    Detect which migration tool the project uses.

    Looks for mentions in CLAUDE.md.
    Defaults to SQL (migrations/ directory) if none found.
    """
    claude_md = project_root / "CLAUDE.md"

    if not claude_md.exists():
        return MigrationTool.SQL

    content = claude_md.read_text().lower()

    # Check for tool mentions (case-insensitive)
    if "prisma" in content:
        return MigrationTool.PRISMA
    if "alembic" in content:
        return MigrationTool.ALEMBIC
    if "flyway" in content:
        return MigrationTool.FLYWAY

    # Default
    return MigrationTool.SQL

def validate_tool_installed(tool: MigrationTool) -> None:
    """
    Verify tool is installed and available.

    Raises RuntimeError if tool not found.
    """
    if tool == MigrationTool.SQL:
        # No tool needed for SQL migrations
        return

    commands = {
        MigrationTool.PRISMA: ["prisma", "--version"],
        MigrationTool.ALEMBIC: ["alembic", "--version"],
        MigrationTool.FLYWAY: ["flyway", "-version"],
    }

    cmd = commands[tool]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode != 0:
        tool_name = tool.value.capitalize()
        raise RuntimeError(
            f"{tool_name} not installed or not in PATH. "
            f"Install it and ensure it's available in your project."
        )

def get_migration_command(tool: MigrationTool, project_root: Path) -> List[str]:
    """
    Get command to run migrations for the detected tool.

    Returns list for subprocess.run()
    """
    if tool == MigrationTool.PRISMA:
        return ["prisma", "migrate", "deploy"]
    elif tool == MigrationTool.ALEMBIC:
        return ["alembic", "upgrade", "head"]
    elif tool == MigrationTool.FLYWAY:
        return ["flyway", "migrate"]
    else:  # SQL
        # Default: apply migrations/ directory
        return ["python", "lib/migrations.py", str(project_root)]
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_migration_tool_detector.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/migration_tool_detector.py \
        tests/test_migration_tool_detector.py
git commit -m "feat: detect and validate migration tool (Prisma, Alembic, Flyway, SQL)"
```

### Task 5.2: Integrate Tool Detection into Worker Initialization

**Files:**
- Modify: `plugins/claude-agents-orchestrator/lib/worker.py:__init__`

- [ ] **Step 1: Write test for worker initialization with tool detection**

```python
# tests/test_worker.py (add to existing)
def test_worker_detects_migration_tool_at_init():
    """Worker validates migration tool on initialization."""
    from worker.lib.worker import Worker
    from worker.lib.migration_tool_detector import MigrationTool
    from pathlib import Path
    from unittest.mock import patch

    claude_md = Path("/tmp/CLAUDE.md")
    claude_md.write_text("Uses Prisma for migrations")

    with patch('worker.lib.migration_tool_detector.validate_tool_installed') as mock_validate:
        worker = Worker(
            agent_name="test",
            repo="test/repo",
            project_root=claude_md.parent
        )

        # Should detect Prisma and validate it
        mock_validate.assert_called()

def test_worker_fails_if_tool_missing():
    """Worker raises error if migration tool not installed."""
    from worker.lib.worker import Worker
    from pathlib import Path
    from unittest.mock import patch

    claude_md = Path("/tmp/CLAUDE.md")
    claude_md.write_text("Uses Prisma")

    with patch('worker.lib.migration_tool_detector.validate_tool_installed') as mock_validate:
        mock_validate.side_effect = RuntimeError("Prisma not installed")

        with pytest.raises(RuntimeError, match="Prisma not installed"):
            Worker(
                agent_name="test",
                repo="test/repo",
                project_root=claude_md.parent
            )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_worker.py::test_worker_detects_migration_tool_at_init -v
```

Expected: FAIL

- [ ] **Step 3: Add tool detection to Worker.__init__**

```python
# plugins/claude-agents-orchestrator/lib/worker.py
from .migration_tool_detector import detect_migration_tool, validate_tool_installed
from pathlib import Path

class Worker:
    def __init__(self, agent_name: str, repo: str, project_root: Path = None):
        self.agent_name = agent_name
        self.repo = repo
        self.project_root = project_root or Path.cwd()

        # CRITICAL: Detect and validate migration tool at init
        self.migration_tool = detect_migration_tool(self.project_root)
        validate_tool_installed(self.migration_tool)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_worker.py::test_worker_detects_migration_tool_at_init -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/worker.py
git commit -m "feat: validate migration tool at worker initialization"
```

---

## Critical Fix #6: Idempotency Enforcement (Issue #6)

### Task 6.1: Create Pre-Commit Hook

**Files:**
- Create: `plugins/claude-agents-orchestrator/.githooks/pre-commit`
- Modify: `SETUP.sh` to install hook

- [ ] **Step 1: Write pre-commit hook script**

```bash
# plugins/claude-agents-orchestrator/.githooks/pre-commit
#!/bin/bash
# Pre-commit hook: Validate idempotency of migrations

set -e

MIGRATIONS_DIR="migrations"
ERROR=0

if [ ! -d "$MIGRATIONS_DIR" ]; then
    exit 0
fi

for file in $(git diff --cached --name-only | grep "^$MIGRATIONS_DIR/.*\.sql$"); do
    # Check for CREATE TABLE without IF NOT EXISTS
    if grep -q "^CREATE TABLE" "$file" && ! grep -q "CREATE TABLE IF NOT EXISTS" "$file"; then
        echo "ERROR: $file contains CREATE TABLE without IF NOT EXISTS"
        ERROR=1
    fi

    # Check for CREATE INDEX without IF NOT EXISTS
    if grep -q "^CREATE INDEX" "$file" && ! grep -q "CREATE INDEX IF NOT EXISTS" "$file"; then
        echo "ERROR: $file contains CREATE INDEX without IF NOT EXISTS"
        ERROR=1
    fi

    # Check for ALTER TABLE ADD COLUMN (usually non-idempotent)
    if grep -q "^ALTER TABLE.*ADD COLUMN" "$file" && ! grep -q "IF COL NOT EXISTS\|IF NOT EXISTS" "$file"; then
        echo "WARN: $file contains ALTER TABLE ADD COLUMN without guards"
        echo "      Consider using: ALTER TABLE IF EXISTS ... (project-specific syntax)"
    fi

    # Check for DROP statements (forbidden)
    if grep -q "^DROP" "$file"; then
        echo "ERROR: $file contains DROP statement (migrations must be additive only)"
        ERROR=1
    fi
done

if [ $ERROR -eq 1 ]; then
    echo ""
    echo "Migration validation failed. Fix the issues above and try again."
    exit 1
fi

exit 0
```

- [ ] **Step 2: Make hook executable**

```bash
chmod +x plugins/claude-agents-orchestrator/.githooks/pre-commit
```

- [ ] **Step 3: Update SETUP.sh to install hook**

```bash
# In SETUP.sh (add this line after cloning/copying)
git config core.hooksPath plugins/claude-agents-orchestrator/.githooks
echo "✅ Pre-commit hook installed for migration validation"
```

- [ ] **Step 4: Test pre-commit hook**

```bash
# Create test migration (invalid)
mkdir -p migrations
cat > migrations/0001-bad.sql << 'EOF'
CREATE TABLE users (id INT);  -- Missing IF NOT EXISTS
EOF

git add migrations/0001-bad.sql
git commit -m "test migration"  # Should FAIL

# Create valid migration
cat > migrations/0001-good.sql << 'EOF'
CREATE TABLE IF NOT EXISTS users (id INT);
EOF

git add migrations/0001-good.sql
git commit -m "test migration"  # Should PASS
```

Expected: First commit fails with error, second commits successfully.

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/.githooks/pre-commit SETUP.sh
git commit -m "feat: add pre-commit hook for migration idempotency validation"
```

---

## Integration Task: Bring It All Together

### Task 7: Create Complete /cao-worker Skill

**Files:**
- Create: `plugins/claude-agents-orchestrator/skills/cao-worker.md`
- Create: `plugins/claude-agents-orchestrator/lib/worker_main.py` (orchestrator)
- Modify: `plugin.json` to register skill

- [ ] **Step 1: Write test for complete worker flow**

```python
# tests/test_worker_integration.py
def test_complete_worker_flow():
    """
    E2E test: poll → claim → apply migrations → implement → create PR
    """
    from worker.lib.worker_main import WorkerOrchestrator
    from unittest.mock import patch, MagicMock

    orch = WorkerOrchestrator(
        agent_name="proud-falcon",
        repo="user/repo",
        polling_interval=300
    )

    with patch('worker.lib.worker_main.poll_for_tickets') as mock_poll:
        with patch('worker.lib.worker_main.claim_ticket') as mock_claim:
            with patch('worker.lib.worker_main.apply_migrations') as mock_migrate:
                with patch('worker.lib.worker_main.implement_feature') as mock_impl:
                    with patch('worker.lib.worker_main.create_pr') as mock_pr:
                        # Setup mocks
                        mock_poll.return_value = [34]  # Found ticket #34 with "to-dev"
                        mock_claim.return_value = True  # Successfully claimed
                        mock_migrate.return_value = True
                        mock_impl.return_value = True
                        mock_pr.return_value = {"url": "https://..."}

                        # Run one cycle
                        result = orch.run_one_cycle()

                        # Verify sequence
                        assert mock_poll.called
                        assert mock_claim.called
                        assert mock_migrate.called
                        assert mock_impl.called
                        assert mock_pr.called
```

- [ ] **Step 2: Implement worker orchestrator**

```python
# plugins/claude-agents-orchestrator/lib/worker_main.py
from pathlib import Path
from .worker import Worker
from .claim import claim_ticket
from .migrations import apply_migrations
from .schema_validator import validate_resume_schema
from .github_notifier import cleanup_labels_after_pr
from .heartbeat import create_lock_file, update_heartbeat, is_ghost_claim
from .migration_tool_detector import detect_migration_tool, validate_tool_installed

class WorkerOrchestrator:
    """Main orchestrator for multi-agent worker."""

    def __init__(self, agent_name: str, repo: str, polling_interval: int = 300):
        self.agent_name = agent_name
        self.repo = repo
        self.polling_interval = polling_interval

        project_root = Path.cwd()
        self.worker = Worker(agent_name, repo, project_root)

    def run_one_cycle(self):
        """Execute one polling cycle: poll → claim → work → PR."""
        # 1. Poll for available tickets with "to-dev" label
        tickets = self.poll_for_tickets()

        if not tickets:
            return {"status": "no_tickets"}

        # Try to claim first available ticket
        for ticket_id in tickets:
            if self.try_claim_and_work(ticket_id):
                return {"status": "completed", "ticket": ticket_id}

        return {"status": "no_claims"}

    def poll_for_tickets(self):
        """Find all issues labeled 'to-dev' (no assigned branch)."""
        # Uses gh CLI
        import subprocess
        result = subprocess.run(
            ["gh", "issue", "list", f"--repo={self.repo}",
             "--label=to-dev", "--json=number"],
            capture_output=True, text=True
        )

        import json
        issues = json.loads(result.stdout)
        return [issue["number"] for issue in issues]

    def try_claim_and_work(self, ticket_id: int) -> bool:
        """Attempt to claim ticket and do work. Return True if successful."""
        # 1. Try to claim via branch push
        branch_name = f"{ticket_id}-{self.agent_name}"

        if not self.claim_ticket(ticket_id, branch_name):
            return False

        # 2. Apply migrations
        try:
            self.apply_migrations(ticket_id)
        except Exception as e:
            self.post_error(ticket_id, f"Migration failed: {e}")
            return False

        # 3. Implement feature
        try:
            self.implement_feature(ticket_id)
        except Exception as e:
            self.post_error(ticket_id, f"Implementation failed: {e}")
            return False

        # 4. Create PR
        try:
            pr_url = self.create_pr(ticket_id, branch_name)
            self.cleanup_after_pr(ticket_id)
            return True
        except Exception as e:
            self.post_error(ticket_id, f"PR creation failed: {e}")
            return False

    def claim_ticket(self, ticket_id: int, branch_name: str) -> bool:
        """Attempt atomic claim via branch push."""
        import subprocess

        # Create and push branch
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                check=True, capture_output=True
            )
            subprocess.run(
                ["git", "push", "origin", branch_name],
                check=True, capture_output=True
            )

            # Claim successful! Post notification
            self.notify_claim(ticket_id, branch_name)
            return True
        except subprocess.CalledProcessError:
            # Another agent already pushed this branch
            return False

    def apply_migrations(self, ticket_id: int):
        """Apply all migrations from migrations/ directory."""
        # Uses migration tool detector
        pass

    def implement_feature(self, ticket_id: int):
        """Main implementation logic (delegated to user's code)."""
        pass

    def create_pr(self, ticket_id: int, branch_name: str) -> str:
        """Create PR and return URL."""
        pass

    def cleanup_after_pr(self, ticket_id: int):
        """Remove labels and cleanup."""
        from .github_notifier import cleanup_labels_after_pr
        cleanup_labels_after_pr(
            repo=self.repo,
            issue_number=ticket_id,
            agent_name=self.agent_name
        )

    def notify_claim(self, ticket_id: int, branch_name: str):
        """Post GitHub comment and update labels on claim."""
        import subprocess

        # Add labels
        subprocess.run([
            "gh", "issue", "edit", str(ticket_id),
            f"--repo={self.repo}",
            "--remove-label=to-dev",
            "--add-label=dev-in-progress",
            f"--add-label=agent/{self.agent_name}"
        ])

        # Post comment
        comment = f"🤖 Agent {self.agent_name} claimed ticket #{ticket_id}\nBranch: {branch_name}"
        subprocess.run([
            "gh", "issue", "comment", str(ticket_id),
            f"--repo={self.repo}",
            f"--body={comment}"
        ])

    def post_error(self, ticket_id: int, message: str):
        """Post error comment."""
        import subprocess
        subprocess.run([
            "gh", "issue", "comment", str(ticket_id),
            f"--repo={self.repo}",
            f"--body=❌ Agent {self.agent_name} error: {message}"
        ])
```

- [ ] **Step 3: Create skill definition**

```markdown
# /cao-worker

Start the multi-agent worker loop for automated ticket development.

## Usage

```
/cao-worker [--agent-name <name>] [--polling-interval <seconds>]
```

## Options

- `--agent-name`: Unique agent identifier (auto-generated if not provided)
- `--polling-interval`: Min 300 seconds (5 minutes), default 300

## What It Does

1. **Poll** for issues labeled "to-dev" (every 5 minutes)
2. **Claim** via atomic branch push (first agent wins)
3. **Notify** GitHub with comment + labels
4. **Apply** migrations (respects project's tool: Prisma, Alembic, Flyway, SQL)
5. **Implement** feature (delegated to user's feature request)
6. **Create PR** and post preview URL
7. **Cleanup** labels ("to-test") and .lock file
8. **Resume** with schema validation if interrupted

## Configuration

Set in CLAUDE.md or environment:
```yaml
worker:
  polling_interval: 300  # 5 minutes minimum
  max_agents: 10  # Start here, scale to 20 later
  ghost_timeout: 1200  # 20 minutes
```

## Safety Guardrails

✅ Atomic claim (first branch push wins)
✅ Heartbeat every 5 min, ghost timeout 20 min
✅ Schema validation before resume
✅ Label cleanup with 3-attempt retry
✅ Migration tool detection (Prisma/Alembic/Flyway)
✅ Idempotency validation (pre-commit hook)
```

- [ ] **Step 4: Register skill in plugin.json**

```json
{
  "skills": [
    {
      "name": "cao-worker",
      "path": "skills/cao-worker.md",
      "requires": ["gh", "python3"]
    }
  ]
}
```

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/worker_main.py \
        plugins/claude-agents-orchestrator/skills/cao-worker.md \
        tests/test_worker_integration.py \
        plugin.json
git commit -m "feat: complete /cao-worker skill with all critical fixes"
```

---

## Additional Critical Task: Ghost Claim Recovery

### Task 8: Implement Ghost Claim Cleanup

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/ghost_cleaner.py`
- Test: `tests/test_ghost_cleaner.py`

**Context:** When heartbeat.py detects a ghost claim (agent dead), we must:
1. Delete the orphaned .lock file
2. Reset GitHub labels (remove "dev-in-progress", add back "to-dev")
3. Post cleanup comment
4. Optionally delete the branch (configurable)

- [ ] **Step 1: Write test for ghost cleanup**

```python
# tests/test_ghost_cleaner.py
def test_cleanup_ghost_claim():
    """Clean up ghost claim: remove labels, post comment, delete lock."""
    from ghost_cleaner import cleanup_ghost_claim
    from pathlib import Path
    from unittest.mock import patch

    with patch('ghost_cleaner.remove_labels_with_retry') as mock_rm:
        with patch('ghost_cleaner.add_labels_with_retry') as mock_add:
            with patch('ghost_cleaner.post_comment') as mock_comment:
                cleanup_ghost_claim(
                    repo="user/repo",
                    issue_number=34,
                    lock_path=Path("/tmp/.lock-34"),
                    delete_branch=False
                )

                # Verify sequence
                mock_rm.assert_called()
                mock_add.assert_called()
                mock_comment.assert_called()

                # Lock should be deleted
                assert not Path("/tmp/.lock-34").exists()
```

- [ ] **Step 2: Run test, should fail**

```bash
pytest tests/test_ghost_cleaner.py::test_cleanup_ghost_claim -v
```

- [ ] **Step 3: Implement ghost cleaner**

```python
# plugins/claude-agents-orchestrator/lib/ghost_cleaner.py
from pathlib import Path
from .github_notifier import remove_labels_with_retry, add_labels_with_retry, post_comment
from .heartbeat import delete_lock_file

def cleanup_ghost_claim(
    repo: str,
    issue_number: int,
    lock_path: Path,
    delete_branch: bool = False,
    branch_name: str = None
) -> None:
    """
    Clean up an abandoned ticket claim (agent dead/crashed).

    1. Remove "dev-in-progress" and "agent/{name}" labels
    2. Add "to-dev" label (release back to dev pool)
    3. Post cleanup comment
    4. Delete .lock file
    5. Optionally delete branch
    """
    # Remove old labels
    remove_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["dev-in-progress"]  # Note: agent/X label also removed but unknown
    )

    # Add back to dev pool
    add_labels_with_retry(
        repo=repo,
        issue_number=issue_number,
        labels=["to-dev"]
    )

    # Post comment
    post_comment(
        repo=repo,
        issue_number=issue_number,
        body="🧹 Ghost claim detected and cleaned. Ticket available for pickup."
    )

    # Delete lock
    delete_lock_file(lock_path)

    # Optionally delete branch (dangerous—only if configured)
    if delete_branch and branch_name:
        import subprocess
        try:
            subprocess.run(
                ["git", "push", "origin", f"--delete", branch_name],
                check=True, capture_output=True
            )
        except subprocess.CalledProcessError:
            # Branch already deleted, OK
            pass
```

- [ ] **Step 4: Test passes**

```bash
pytest tests/test_ghost_cleaner.py -v
```

- [ ] **Step 5: Commit**

```bash
git add plugins/claude-agents-orchestrator/lib/ghost_cleaner.py tests/test_ghost_cleaner.py
git commit -m "feat: add ghost claim cleanup with label reset and lock deletion"
```

---

## Additional Critical Task: Migrations Runner

### Task 9: Implement DB-Agnostic Migrations

**Files:**
- Create: `plugins/claude-agents-orchestrator/lib/migrations.py`
- Test: `tests/test_migrations.py`

**Context:** Applies migrations from migrations/ directory with idempotency tracking.

- [ ] **Step 1: Write test for migration application**

```python
# tests/test_migrations.py
def test_apply_migrations_creates_tracking_table():
    """Create _migrations table on first run."""
    from migrations import apply_migrations
    import sqlite3
    from pathlib import Path

    db_path = Path("/tmp/test.db")
    db_path.unlink(missing_ok=True)

    apply_migrations(db_path, Path("/tmp/migrations"))

    # Check _migrations table exists
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'")
    assert cursor.fetchone() is not None
    conn.close()

def test_apply_migrations_tracks_applied():
    """Track applied migrations in _migrations table."""
    from migrations import apply_migrations, get_applied_migrations
    from pathlib import Path

    migrations_dir = Path("/tmp/migrations")
    migrations_dir.mkdir(exist_ok=True)
    (migrations_dir / "0001-init.sql").write_text("CREATE TABLE IF NOT EXISTS users (id INT);")

    db_path = Path("/tmp/test.db")
    apply_migrations(db_path, migrations_dir)

    applied = get_applied_migrations(db_path)
    assert "0001-init.sql" in applied
```

- [ ] **Step 2-5: (Abbreviated) Implement migrations runner**

```python
# plugins/claude-agents-orchestrator/lib/migrations.py
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict

def apply_migrations(db_path: Path, migrations_dir: Path) -> None:
    """Apply all pending migrations from migrations/ directory."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Create tracking table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            name TEXT UNIQUE NOT NULL,
            checksum TEXT NOT NULL,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            applied_by TEXT
        )
    """)
    conn.commit()

    # Get applied migrations
    applied = get_applied_migrations(db_path)

    # Apply new migrations in order
    for mig_file in sorted(migrations_dir.glob("*.sql")):
        if mig_file.name not in applied:
            content = mig_file.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()

            cursor.execute(content)  # Apply
            cursor.execute(
                "INSERT INTO _migrations (name, checksum) VALUES (?, ?)",
                (mig_file.name, checksum)
            )
            conn.commit()

    conn.close()

def get_applied_migrations(db_path: Path) -> Dict[str, str]:
    """Return dict of {migration_name: checksum} for applied migrations."""
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT name, checksum FROM _migrations")
        return {row[0]: row[1] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        # Table doesn't exist yet
        return {}
    finally:
        conn.close()
```

- [ ] **Test and commit**

```bash
pytest tests/test_migrations.py -v
git add plugins/claude-agents-orchestrator/lib/migrations.py tests/test_migrations.py
git commit -m "feat: add DB-agnostic migration runner with idempotency tracking"
```

---

## Deployment & Rollout

### Task 10: Create Deployment Checklist

**Files:**
- Create: `docs/DEPLOYMENT.md`

- [ ] **Step 1: Write deployment guide**

```markdown
# /cao-worker Deployment Guide

## Pre-Deployment Checklist

- [ ] All 15 hours of implementation complete
- [ ] Test suite passes: `pytest tests/ -v --cov`
- [ ] Pre-commit hook working: `git commit` rejects invalid migrations
- [ ] Agent name generator tested
- [ ] Schema validation tested on resume

## Phase 1: Deploy (5-10 agents)

1. Install plugin (if not already):
   ```
   /plugins → install claude-agents-orchestrator
   ```

2. Set up project:
   ```bash
   cd your-project
   bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)
   ```

3. Create CLAUDE.md with:
   ```yaml
   worker:
     polling_interval_seconds: 300
     max_agents: 5
     ghost_timeout_seconds: 1200
   ```

4. Start first agent:
   ```
   /cao-worker --agent-name proud-falcon
   ```

5. Monitor for 1 week:
   - Check agent logs: `/cao-show-logs`
   - Verify schema validation on resume
   - Test ghost claim detection (manually kill agent)

## Phase 2: Expand (5-10 agents)

- Start 5-10 agents in parallel
- Monitor API usage
- Verify label cleanup works under load

## Phase 3: Scale (10-20 agents + API caching)

- Implement GitHub API caching layer (Future: Task 11)
- Increase max_agents to 20
- Deploy monitoring dashboard (Future: Task 12)

## Rollback Procedure

If critical issues occur:

```bash
# Disable all workers
# (Manual: tell users to stop /cao-worker)

# Reset stuck tickets
gh issue list --repo=user/repo --label=dev-in-progress \
  --json=number | jq '.[] | .number' | \
  while read N; do
    gh issue edit $N --repo=user/repo \
      --remove-label=dev-in-progress \
      --remove-label=agent/* \
      --add-label=to-dev
  done

# Delete orphaned branches
git push origin --delete $(git branch -r | grep "^origin/[0-9]*-")

# Clear agent logs
rm ~/.claude/projects/<project>/logs/*
```

## Success Criteria

- ✅ Tickets claimed without race conditions
- ✅ Schema valid before resume (no corruption)
- ✅ Labels cleanup successfully (no stuck states)
- ✅ Heartbeat detects dead agents within 25 minutes
- ✅ No GitHub API exhaustion
```

- [ ] **Step 2: Commit**

```bash
git add docs/DEPLOYMENT.md
git commit -m "docs: add deployment guide and rollback procedure"
```

---

## Testing & Validation

### Task 8: Run Full Test Suite

- [ ] **Run all unit tests**

```bash
pytest tests/ -v --cov=lib --cov-report=html
```

Expected: All tests pass, >85% code coverage

- [ ] **Run integration test**

```bash
pytest tests/test_worker_integration.py -v
```

Expected: End-to-end flow passes

- [ ] **Verify pre-commit hook**

```bash
# Create invalid migration, should fail
echo "CREATE TABLE users (id INT);" > migrations/test.sql
git add migrations/test.sql
git commit -m "test"  # Should be rejected

# Fix it
echo "CREATE TABLE IF NOT EXISTS users (id INT);" > migrations/test.sql
git add migrations/test.sql
git commit -m "test"  # Should succeed
```

Expected: Invalid commit rejected, valid commit accepted

- [ ] **Commit test results**

```bash
git add coverage/
git commit -m "test: validate full test suite + pre-commit hook"
```

---

## Phased Rollout

### Phase 1: 5-10 Agents (Weeks 1-2)

- [ ] Deploy with critical fixes only
- [ ] Manual monitoring, no automation dashboard
- [ ] Polling interval: 5 minutes (hardcoded)
- [ ] Ghost timeout: 20 minutes

**Success criteria:**
- All tests pass
- No schema corruption on resume
- Labels cleanup successfully
- Tickets claim without race conditions

### Phase 2: 5-10 + Monitoring (Weeks 2-3)

- [ ] Add agent log DB + basic dashboard
- [ ] Reduce ghost timeout to 10 minutes (optional)
- [ ] Document lessons learned

### Phase 3: 10-20 Agents (Weeks 4-5)

- [ ] Implement GitHub API caching layer
- [ ] Scale to 20 agents
- [ ] Add rate limit monitoring + alerts

---

## Summary

**Total Tasks:** 10 (setup + 6 critical fixes + ghost cleanup + migrations + full integration + testing + deployment)

**Estimated Effort:** 18-22 hours (refined from initial 15h estimate)
- Setup + agent namer: 2h
- Critical Fix #1 (Heartbeat): 2.5h
- Critical Fix #2 (Polling): 1h
- Critical Fix #3 (Schema): 4h
- Critical Fix #4 (Label cleanup): 3h
- Critical Fix #5 (Tool detection): 3h
- Critical Fix #6 (Idempotency): 2h
- Ghost cleanup (Task 8): 2h
- Migrations runner (Task 9): 2h
- Integration + testing (Task 7): 4h
- Deployment + rollback (Task 10): 1.5h

**Test Coverage:** >85% (all critical paths tested)
**Deployment:** Phased (5→10→20 agents with rollback procedure)

**Quality Gate:** Plan approved via subagent-document-reviewer ✅

**Next:** Choose execution approach:
1. **Subagent-Driven** (recommended) — fresh subagent per task, fast iteration
2. **Inline Execution** — batch tasks in current session with checkpoints
