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


def init_db(db_path: Path) -> None:
    """Create DB directory + table if not exists. Idempotent."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(SCHEMA)
    conn.commit()
    conn.close()
