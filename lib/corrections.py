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
    return words[0][:12] if words else "misc"


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
