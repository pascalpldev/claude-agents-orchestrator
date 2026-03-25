#!/usr/bin/env python3
"""
lib/corrections.py — Behavioral corrections DB for CAO agents.

Dual interface:
  CLI:    python3 lib/corrections.py <subcommand> [args]
  Python: from lib.corrections import init_db, load_corrections, add_correction, ...
"""

import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS corrections (
  id                TEXT PRIMARY KEY,
  agent             TEXT NOT NULL,
  class             TEXT NOT NULL CHECK (class IN ('project-pattern', 'general')),
  gap               TEXT NOT NULL,
  rule              TEXT NOT NULL,
  source            TEXT,
  source_comment_id TEXT,
  status            TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'inactive', 'pending_integration', 'integrated')),
  target_hint       TEXT,
  integrated_commit TEXT,
  integrated_file   TEXT,
  created_at        TEXT NOT NULL,
  updated_at        TEXT NOT NULL
);
"""

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "always", "never", "all", "any", "each",
    "every", "is", "are", "was", "were", "be", "been", "being", "have",
    "has", "had", "do", "does", "did", "will", "would", "could", "should",
    "may", "might", "must", "shall", "check", "verify", "ensure",
    "ask", "who", "what", "when", "where", "how", "why", "use", "get",
    "set", "run", "add", "put", "let", "make", "that", "this", "its",
}

_AGENT_PREFIX = {
    "chief-builder": "cb",
    "dev": "dev",
    "*": "all",
}


def _now() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _slugify_keyword(text: str) -> str:
    """Extract first meaningful word from rule text, max 12 chars."""
    words = re.sub(r"[^a-z0-9\s]", "", text.lower()).split()
    for word in words:
        if word not in _STOP_WORDS and len(word) >= 3:
            return word[:12]
    return "misc"


def generate_id(
    agent: str,
    project: str,
    ticket: str,
    rule: str,
    db_path: Optional[Path] = None,
) -> str:
    """Generate a unique correction ID."""
    prefix = _AGENT_PREFIX.get(agent, agent[:4])
    proj = re.sub(r"[^a-z0-9]", "", project.lower().split("-")[-1])[:12] or "proj"
    tkt = re.sub(r"[^a-z0-9]", "", str(ticket).lower()) or "manual"
    keyword = _slugify_keyword(rule)

    base = f"{prefix}_{proj}_{tkt}_{keyword}"
    if db_path is None:
        return base

    # Collision resolution
    candidate = base
    suffix = 2
    conn = sqlite3.connect(str(db_path))
    try:
        while conn.execute(
            "SELECT 1 FROM corrections WHERE id = ?", (candidate,)
        ).fetchone():
            candidate = f"{base}_{suffix}"
            suffix += 1
    finally:
        conn.close()
    return candidate


def init_db(db_path: Path) -> None:
    """Create DB directory + table if not exists. Idempotent."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()


def add_correction(
    db_path: Path,
    agent: str,
    cls: str,
    gap: str,
    rule: str,
    project_slug: str,
    ticket: str = "manual",
    source: Optional[str] = None,
    source_comment_id: Optional[str] = None,
    target_hint: Optional[str] = None,
) -> str:
    """Insert a correction. Returns the generated ID."""
    db_path = Path(db_path)
    init_db(db_path)
    id_ = generate_id(agent, project_slug, ticket, rule, db_path=db_path)
    now = _now()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """INSERT INTO corrections
               (id, agent, class, gap, rule, source, source_comment_id,
                status, target_hint, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)""",
            (id_, agent, cls, gap, rule, source, source_comment_id, target_hint, now, now),
        )
        conn.commit()
    finally:
        conn.close()
    return id_


def get_correction(db_path: Path, id_: str) -> Optional[dict]:
    """Return correction as dict or None if not found."""
    db_path = Path(db_path)
    if not db_path.exists():
        return None
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT * FROM corrections WHERE id = ?", (id_,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_correction(
    db_path: Path,
    id_: str,
    status: Optional[str] = None,
    integrated_commit: Optional[str] = None,
    integrated_file: Optional[str] = None,
) -> None:
    """Update one or more fields of a correction. Raises ValueError if not found."""
    db_path = Path(db_path)
    sets, params = [], []
    if status is not None:
        sets.append("status = ?")
        params.append(status)
    if integrated_commit is not None:
        sets.append("integrated_commit = ?")
        params.append(integrated_commit)
    if integrated_file is not None:
        sets.append("integrated_file = ?")
        params.append(integrated_file)
    if not sets:
        return
    sets.append("updated_at = ?")
    params.append(_now())
    params.append(id_)
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.execute(
            f"UPDATE corrections SET {', '.join(sets)} WHERE id = ?", params
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise ValueError(f"Correction not found: {id_}")
    finally:
        conn.close()


def update_status(db_path: Path, id_: str, status: str) -> None:
    """Update status of a correction. Raises ValueError if not found."""
    update_correction(db_path, id_, status=status)


def list_corrections(
    db_path: Path,
    agent: Optional[str] = None,
    status: Optional[str] = None,
) -> list:
    """Return corrections matching filters as list of dicts."""
    db_path = Path(db_path)
    if not db_path.exists():
        return []
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        conditions, params = [], []
        if agent and agent != "*":
            conditions.append("agent IN (?, '*')")
            params.append(agent)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        rows = conn.execute(
            f"SELECT * FROM corrections {where} ORDER BY created_at DESC", params
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def comment_already_saved(db_path: Path, comment_id: str) -> bool:
    """Return True if this GitHub comment ID is already in the DB."""
    db_path = Path(db_path)
    if not db_path.exists():
        return False
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT 1 FROM corrections WHERE source_comment_id = ?", (comment_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def load_corrections(agent: str, project_db: Path, global_db: Path) -> str:
    """
    Load active corrections for agent from both DBs.
    Returns formatted constraints block, or empty string if none.
    """
    rows = []
    for db in [project_db, global_db]:
        rows += list_corrections(db, agent=agent, status="active")

    if not rows:
        return ""

    lines = ["## Active corrections (loaded at startup)", ""]
    for row in rows:
        lines.append(f"[{row['class']} — #{row['id']} | {row['agent']}]")
        if row.get("gap"):
            lines.append(f"Gap: {row['gap']}")
        lines.append(f"Rule: {row['rule']}")
        lines.append("")
    return "\n".join(lines).rstrip()
