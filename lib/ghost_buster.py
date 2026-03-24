#!/usr/bin/env python3
"""
Ghost buster — detects and cleans up abandoned agent claims.

A ghost is an agent that claimed a ticket but is no longer making progress.
Two complementary detection methods are used:

LOCAL detection (same machine only):
  - PID in .lock file is dead  →  immediate ghost
  - last_heartbeat_ts stale > HEARTBEAT_GHOST_SECS (2 min)  →  dead ghost

REMOTE detection (cross-machine, via GitHub):
  - Ticket has label dev-in-progress or enriching
  - Last 🔖 milestone comment older than MILESTONE_GHOST_SECS (20 min)
  - Works from any machine since GitHub is the shared source of truth

Ghost cleanup (same for both):
  - Post GitHub comment explaining what happened + branch info
  - Reset label to-dev (or to-enrich for enriching tickets)
  - Remove .lock file if found locally

Both methods are run and results are deduplicated by ticket number.

Usage:
    python3 lib/ghost_buster.py [--repo OWNER/REPO] [--locks-dir PATH] [--dry-run]
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Thresholds ────────────────────────────────────────────────────────────────

# 2 min — heartbeat sub-process updates every 30s, so 2min = ~4 missed beats
HEARTBEAT_GHOST_SECS = 120

# 20 min — milestone interval is 10min, so 2× = ghost threshold
MILESTONE_GHOST_SECS = 1200

# Extra grace if PID is still alive (stuck in long tool, not dead)
MILESTONE_GRACE_SECS = 300  # 25 min total for stuck agents


# ── Subprocess helpers ────────────────────────────────────────────────────────

def _gh(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["gh"] + list(args), capture_output=True, text=True)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists, different user — treat as alive


def _last_milestone_age(comments: list) -> Optional[float]:
    """Return seconds since last 🔖 milestone comment, or None if no milestones."""
    now = time.time()
    milestone_times = []
    for c in comments:
        if c.get("body", "").startswith("🔖"):
            try:
                ts_str = c["createdAt"]
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                milestone_times.append(dt.timestamp())
            except Exception:
                pass
    if not milestone_times:
        return None
    return now - max(milestone_times)


# ── Local detection ───────────────────────────────────────────────────────────

def bust_local_ghosts(
    locks_dir: Path, owner: str, repo: str, dry_run: bool = False
) -> list[dict]:
    """Check local .lock files for dead PIDs or stale heartbeats."""
    ghosts = []
    now = time.time()

    if not locks_dir.exists():
        return ghosts

    for lock_file in sorted(locks_dir.glob("ticket-*.lock")):
        try:
            data = json.loads(lock_file.read_text())
        except (json.JSONDecodeError, OSError):
            continue

        ticket      = data.get("ticket") or lock_file.stem.replace("ticket-", "")
        pid         = data.get("pid")
        last_hb     = data.get("last_heartbeat_ts", 0)
        last_ms     = data.get("last_milestone_ts", last_hb)
        phase       = data.get("current_phase", "?")
        branch      = data.get("branch", "")
        agent       = data.get("agent", "?")
        machine_id  = data.get("machine_id", "?")

        reason = None

        # Signal 1: PID dead — immediate ghost regardless of timestamps
        if pid and not _pid_alive(int(pid)):
            reason = f"PID {pid} mort"

        # Signal 2: heartbeat stale — process dead or heartbeat_process stopped
        elif now - last_hb > HEARTBEAT_GHOST_SECS:
            stale_min = int((now - last_hb) / 60)
            reason = f"heartbeat stale ({stale_min}min)"

        # Signal 3: milestone stale with extra grace (stuck, not dead)
        elif now - last_ms > MILESTONE_GHOST_SECS + MILESTONE_GRACE_SECS:
            stale_min = int((now - last_ms) / 60)
            reason = f"milestone stale ({stale_min}min, PID vivant)"

        if reason:
            ghost = {
                "ticket":     str(ticket),
                "agent":      agent,
                "machine_id": machine_id,
                "phase":      phase,
                "branch":     branch,
                "reason":     reason,
                "lock_file":  str(lock_file),
                "source":     "local",
            }
            ghosts.append(ghost)
            if not dry_run:
                _cleanup_ghost(owner, repo, **{k: ghost[k] for k in
                               ("ticket", "agent", "machine_id", "phase", "branch", "reason")})
                lock_file.unlink(missing_ok=True)

    return ghosts


# ── Remote detection ──────────────────────────────────────────────────────────

def bust_remote_ghosts(
    owner: str, repo: str, dry_run: bool = False
) -> list[dict]:
    """Check GitHub for tickets with stale milestones (cross-machine detection)."""
    ghosts = []

    for label in ("dev-in-progress", "enriching"):
        result = _gh(
            "issue", "list",
            "--repo", f"{owner}/{repo}",
            "--label", label,
            "--state", "open",
            "--json", "number,title,comments,updatedAt",
            "--limit", "50",
        )
        if result.returncode != 0:
            continue

        try:
            issues = json.loads(result.stdout)
        except json.JSONDecodeError:
            continue

        for issue in issues:
            ticket   = str(issue["number"])
            comments = issue.get("comments", [])
            age      = _last_milestone_age(comments)

            if age is None:
                # No milestones yet — use updatedAt as proxy for when label was set
                try:
                    updated = issue.get("updatedAt", "")
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    age = time.time() - dt.timestamp()
                except Exception:
                    continue

            if age > MILESTONE_GHOST_SECS:
                reason = f"dernière activité il y a {int(age / 60)}min (remote)"
                ghost = {
                    "ticket":     ticket,
                    "agent":      "inconnu",
                    "machine_id": "?",
                    "phase":      "inconnu",
                    "branch":     "",
                    "reason":     reason,
                    "source":     "remote",
                    "reset_label": "to-dev" if label == "dev-in-progress" else "to-enrich",
                }
                ghosts.append(ghost)
                if not dry_run:
                    _cleanup_ghost(
                        owner, repo,
                        ticket=ticket,
                        agent="inconnu",
                        machine_id="?",
                        phase="inconnu",
                        branch="",
                        reason=reason,
                        from_label=label,
                        to_label=ghost["reset_label"],
                    )

    return ghosts


# ── Cleanup ───────────────────────────────────────────────────────────────────

def _cleanup_ghost(
    owner: str,
    repo: str,
    ticket: str,
    agent: str,
    machine_id: str,
    phase: str,
    branch: str,
    reason: str,
    from_label: str = "dev-in-progress",
    to_label: str = "to-dev",
) -> None:
    branch_info = f"\nBranche: `{branch}`" if branch else ""
    machine_info = f"\nMachine: `{machine_id}`" if machine_id and machine_id != "?" else ""

    body = (
        f"👻 **Ghost détecté** — agent `{agent}` ne répond plus ({reason}).{machine_info}\n\n"
        f"Phase au moment de la détection : `{phase}`{branch_info}\n\n"
        f"Ticket remis en `{to_label}`. "
        f"Le prochain agent reprendra depuis le dernier commit pushé sur la branche."
    )
    _gh("issue", "comment", ticket, f"--repo={owner}/{repo}", f"--body={body}")
    _gh(
        "issue", "edit", ticket, f"--repo={owner}/{repo}",
        f"--remove-label={from_label}", f"--add-label={to_label}",
    )


# ── Main entry ────────────────────────────────────────────────────────────────

def run(locks_dir: Path, owner: str, repo: str, dry_run: bool = False) -> int:
    """Run ghost buster. Returns number of ghosts cleaned (or detected if dry_run)."""
    local_ghosts  = bust_local_ghosts(locks_dir, owner, repo, dry_run)
    remote_ghosts = bust_remote_ghosts(owner, repo, dry_run)

    # Deduplicate: local detection takes precedence over remote for same ticket
    local_tickets  = {g["ticket"] for g in local_ghosts}
    unique_remote  = [g for g in remote_ghosts if g["ticket"] not in local_tickets]
    all_ghosts     = local_ghosts + unique_remote

    prefix = "[DRY RUN] " if dry_run else ""
    if all_ghosts:
        print(f"\n{prefix}👻 Ghost buster — {len(all_ghosts)} ghost(s) détecté(s) :")
        for g in all_ghosts:
            src = g["source"]
            print(
                f"  #{g['ticket']:>4}  {g['agent']:<18}  {g['machine_id']:<14}"
                f"  {g['reason']}  [{src}]"
            )
        print()
    else:
        print(f"{prefix}👻 Ghost buster — aucun ghost détecté.")

    return len(all_ghosts)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ghost buster for abandoned agent claims")
    parser.add_argument("--repo",      help="OWNER/REPO (auto-détecté depuis git remote si absent)")
    parser.add_argument("--locks-dir", help="Chemin vers le répertoire .locks")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Détecter sans nettoyer")
    args = parser.parse_args()

    # Auto-detect repo
    if args.repo:
        _owner, _repo = args.repo.split("/", 1)
    else:
        _r = subprocess.run(
            ["git", "remote", "get-url", "origin"], capture_output=True, text=True
        )
        _match = re.search(r"github\.com[:/]([^/]+)/([^/.]+)", _r.stdout.strip())
        if not _match:
            print("ERROR: impossible de détecter le repo depuis git remote", file=sys.stderr)
            sys.exit(1)
        _owner, _repo = _match.group(1), _match.group(2)

    # Auto-detect locks dir
    if args.locks_dir:
        _locks_dir = Path(args.locks_dir)
    else:
        _root = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
        )
        _locks_dir = Path(_root.stdout.strip()) / ".locks"

    sys.exit(0 if run(_locks_dir, _owner, _repo, args.dry_run) == 0 else 1)
