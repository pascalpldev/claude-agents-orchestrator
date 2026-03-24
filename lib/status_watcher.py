#!/usr/bin/env python3
"""
status_watcher.py — Real-time CAO status in the terminal.

Polls lock files, GitHub labels, and logs every N seconds.
Uses ANSI escape codes to rewrite output in place (no scroll spam).

Usage:
    python3 lib/status_watcher.py [--interval N] [--repo owner/repo]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ── ANSI palette ──────────────────────────────────────────────────────────────

R = "\033[0m"           # reset

def bold(s):   return f"\033[1m{s}{R}"
def dim(s):    return f"\033[2m{s}{R}"
def italic(s): return f"\033[3m{s}{R}"

# 256-color foreground: \033[38;5;Nm
def c(n, s):   return f"\033[38;5;{n}m{s}{R}"

# Named colors (256-color)
def white(s):      return c(255, s)
def gray(s):       return c(244, s)
def dark_gray(s):  return c(238, s)
def cyan(s):       return c(39,  s)
def blue(s):       return c(33,  s)
def purple(s):     return c(141, s)
def green(s):      return c(82,  s)
def lime(s):       return c(148, s)
def yellow(s):     return c(220, s)
def orange(s):     return c(208, s)
def red(s):        return c(196, s)
def pink(s):       return c(205, s)

# Semantic
def tick(s):       return green(s)    # success / active
def warn(s):       return yellow(s)   # in-progress / pending
def danger(s):     return red(s)      # error / ghost
def info(s):       return cyan(s)     # agent name
def accent(s):     return purple(s)   # milestone
def muted(s):      return dim(gray(s))

# Background highlight (for section headers)
def bg_section(s): return f"\033[48;5;235m\033[38;5;255m{s}{R}"

# ── Terminal helpers ──────────────────────────────────────────────────────────

def _clear_screen():
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

def _move_top():
    sys.stdout.write("\033[H")
    sys.stdout.flush()

def _width():
    try:
        return os.get_terminal_size().columns
    except Exception:
        return 80

def _bar(color_fn=gray, char="─"):
    return color_fn(char * min(_width(), 72))

def _thick_bar(char="━"):
    return c(240, char * min(_width(), 72))

# ── Elapsed time coloring ─────────────────────────────────────────────────────

def _elapsed_color(mins: int, s: str) -> str:
    if mins < 10:  return green(s)
    if mins < 30:  return yellow(s)
    if mins < 60:  return orange(s)
    return red(s)

# ── Header ────────────────────────────────────────────────────────────────────

def _header(repo, interval, last_ts, session_count):
    w = min(_width(), 72)
    owner, _, name = repo.partition("/")
    repo_str = f"{dim(owner + '/')}{bold(white(name))}"

    count_str = (
        f"  {tick('●')} {bold(str(session_count))} completed today"
        if session_count else ""
    )

    print(_thick_bar())
    print(f"  {bold(white('CAO Watch'))}  {repo_str}{count_str}")
    print(f"  {muted('⟳')} {muted(f'{interval}s')}  "
          f"{muted('upd')} {yellow(last_ts)}  "
          f"{muted('Ctrl+C to quit')}")
    print(_thick_bar())

# ── Data fetchers ─────────────────────────────────────────────────────────────

def _get_repo():
    try:
        r = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5
        )
        url = r.stdout.strip()
        for p in ("https://github.com/", "git@github.com:"):
            if url.startswith(p):
                url = url[len(p):]
        return url.removesuffix(".git")
    except Exception:
        return "unknown/unknown"


def _fmt_time(ts: float) -> str:
    if not ts:
        return "—"
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def _get_lock_data(repo_root: Path):
    locks_dir = repo_root / ".locks"
    if not locks_dir.exists():
        return []
    agents = []
    now = time.time()
    for lf in sorted(locks_dir.glob("*.lock")):
        try:
            d = json.loads(lf.read_text())
            ticket    = lf.stem.replace("ticket-", "")
            elapsed_s = int(now - d.get("claimed_at", now))
            # Support legacy field name last_heartbeat as fallback
            last_hb   = d.get("last_heartbeat_ts", d.get("last_heartbeat", now))
            last_ms   = d.get("last_milestone_ts", last_hb)
            hb_age    = int(now - last_hb)
            ms_age    = int(now - last_ms)
            # DEAD ghost: heartbeat stale 2min (heartbeat_process stopped)
            # STUCK ghost: milestone stale 20min (agent alive but no progress)
            ghost_dead  = hb_age > 120
            ghost_stuck = ms_age > 1200
            agents.append({
                "ticket":        ticket,
                "agent":         d.get("agent", "?"),
                "machine_id":    d.get("machine_id", ""),
                "elapsed_s":     elapsed_s,
                "elapsed_min":   elapsed_s // 60,
                "phase":         d.get("current_phase", "—"),
                "milestones":    d.get("milestone_count", 0),
                "last_ms_title": d.get("last_milestone_title", ""),
                "session_start": _fmt_time(d.get("session_start")),
                "task_start":    _fmt_time(d.get("task_start") or d.get("claimed_at")),
                "pid":           d.get("pid"),
                "ghost":         ghost_dead or ghost_stuck,
                "ghost_type":    "DEAD" if ghost_dead else ("STUCK" if ghost_stuck else ""),
                "ms_age_min":    ms_age // 60,
                "lock_path":     lf,
            })
        except Exception:
            pass
    return agents


def _get_tickets(repo: str):
    WORKFLOW_LABELS = {
        "to-enrich", "enriching", "enriched",
        "to-dev", "dev-in-progress", "to-test", "godeploy", "deployed"
    }
    try:
        out = subprocess.run(
            ["gh", "issue", "list", f"--repo={repo}", "--state=open",
             "--json=number,title,labels,updatedAt", "--limit=30"],
            capture_output=True, text=True, timeout=10
        )
        issues = json.loads(out.stdout or "[]")
        result = []
        for iss in issues:
            labels = {l["name"] for l in iss.get("labels", [])}
            active = labels & WORKFLOW_LABELS
            if not active:
                continue
            for lbl in ("dev-in-progress", "enriching", "godeploy",
                        "to-test", "to-dev", "enriched", "to-enrich"):
                if lbl in active:
                    state = lbl
                    break
            else:
                state = next(iter(active))
            result.append({
                "number":  iss["number"],
                "title":   iss["title"][:52],
                "state":   state,
                "updated": iss.get("updatedAt", ""),
            })
        return result
    except Exception:
        return []


def _get_session_ticket_count(repo: str) -> int:
    owner_repo = repo.replace("/", "-")
    log_dir    = Path.home() / ".claude" / "projects" / "logs" / owner_repo
    today      = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file   = log_dir / f"{today}.jsonl"
    if not log_file.exists():
        return 0
    count = 0
    try:
        for line in log_file.read_text().strip().split("\n"):
            e = json.loads(line)
            if e.get("phase") == "end" and e.get("status") in ("success", "ok"):
                count += 1
    except Exception:
        pass
    return count


def _get_last_log_events(repo: str, n: int = 6):
    owner_repo = repo.replace("/", "-")
    log_dir    = Path.home() / ".claude" / "projects" / "logs" / owner_repo
    if not log_dir.exists():
        return []
    for lf in reversed(sorted(log_dir.glob("*.jsonl"))):
        try:
            content = lf.read_text().strip()
            if content:
                events = []
                for line in content.split("\n")[-n:]:
                    try:
                        events.append(json.loads(line))
                    except Exception:
                        pass
                return events
        except Exception:
            continue
    return []

# ── Renderers ─────────────────────────────────────────────────────────────────

# State → (color_fn, icon, label)
STATE_STYLE = {
    "enriching":       (yellow,  "⚙ ", "enriching      "),
    "dev-in-progress": (orange,  "⚙ ", "dev-in-progress"),
    "godeploy":        (pink,    "🚀", "godeploy       "),
    "to-test":         (lime,    "🧪", "to-test        "),
    "to-dev":          (blue,    "⏳", "to-dev         "),
    "to-enrich":       (cyan,    "⏳", "to-enrich      "),
    "enriched":        (green,   "✓ ", "enriched       "),
    "deployed":        (green,   "✓ ", "deployed       "),
}

# Phase prefix → color
PHASE_COLOR = {
    "Fabrication":   orange,
    "Deployment":    pink,
    "Enrichment":    cyan,
    "Verification":  lime,
    "Discovery":     blue,
    "Design":        purple,
}

def _phase_color(phase: str):
    for prefix, fn in PHASE_COLOR.items():
        if phase.startswith(prefix):
            return fn(phase)
    return white(phase)


def _render_agents(agents):
    print(f"\n{bg_section('  ACTIVE AGENTS  ')}")
    print(_bar())
    if not agents:
        print(f"  {muted('(no agents running)')}")
        return

    for a in agents:
        mins     = a["elapsed_min"]
        phase    = (a["phase"] or "—")[:38]
        ms_n     = a["milestones"]
        ms_title = (a["last_ms_title"] or "")[:44]
        pid_str  = f"pid {a['pid']}" if a["pid"] else "pid ?"

        ms_str = (
            f"{accent('#' + str(ms_n))} {muted('— ' + ms_title)}" if ms_title
            else (accent(f"#{ms_n}") if ms_n else muted("starting"))
        )

        if a["ghost"]:
            if a["ghost_type"] == "DEAD":
                status_badge = f"  {danger('⚠  GHOST — heartbeat lost (PID dead?)')}"
            else:
                status_badge = f"  {danger(f'⚠  GHOST — no milestone for {a[\"ms_age_min\"]}min')}"
        else:
            status_badge = ""

        # ── Line 1: ticket | agent | session→task | elapsed | pid
        print(
            f"  {bold(yellow('#' + a['ticket']  + ' '))}"
            f"{bold(info(a['agent'][:20]  + ' ')):<28}"
            f"  {muted('session')} {gray(a['session_start'])}"
            f"  {muted('→')}  {muted('task')} {gray(a['task_start'])}"
            f"  {_elapsed_color(mins, str(mins) + 'min')}"
            f"  {muted(pid_str)}"
            f"{status_badge}"
        )
        # ── Line 2: phase | milestone
        print(
            f"  {'':30}"
            f"  {_phase_color(phase):<50}"
            f"  {muted('ms')} {ms_str}"
        )
        # ── Line 3: machine | kill hint
        machine_str = f"{muted('machine')} {gray(a['machine_id'])}  " if a.get("machine_id") else ""
        print(
            f"  {'':30}"
            f"  {machine_str}"
            f"{muted('kill →')} "
            f"{dark_gray('touch .locks/kill-ticket-' + a['ticket'])}"
            f"  {muted('(within 10min)')}"
        )
        print()


def _render_tickets(tickets):
    active  = [t for t in tickets if t["state"] in ("enriching", "dev-in-progress", "godeploy")]
    waiting = [t for t in tickets if t["state"] in ("to-enrich", "enriched", "to-dev", "to-test")]

    if active:
        print(f"\n{bg_section('  IN PROGRESS  ')}")
        print(_bar())
        for t in active:
            style = STATE_STYLE.get(t["state"], (white, "•", t["state"]))
            col, icon, label = style
            print(
                f"  {col(icon)}  {bold(col(label))}"
                f"  {bold(white('#' + str(t['number']))):<8}"
                f"  {white(t['title'])}"
            )

    if waiting:
        print(f"\n{bg_section('  WAITING  ')}")
        print(_bar())
        for t in waiting:
            style = STATE_STYLE.get(t["state"], (gray, "•", t["state"]))
            col, icon, label = style
            print(
                f"  {col(icon)}  {col(label)}"
                f"  {gray('#' + str(t['number'])):<8}"
                f"  {gray(t['title'])}"
            )

    if not active and not waiting:
        print(f"\n  {muted('No active tickets.')}")


# Phase → color for logs
LOG_PHASE_COLOR = {
    "start":            cyan,
    "end":              green,
    "milestone":        accent,
    "error":            red,
    "claim":            yellow,
    "pr_created":       lime,
    "pushed":           lime,
    "branch_created":   blue,
    "implement_start":  orange,
    "implement_complete": orange,
    "verify_result":    lime,
    "label_updated":    purple,
    "poll":             gray,
    "heartbeat":        gray,
}

LOG_AGENT_COLOR = {
    "chief-builder": purple,
    "dev":           orange,
    "worker":        cyan,
}


def _render_logs(events):
    if not events:
        return
    print(f"\n{bg_section('  RECENT ACTIVITY  ')}")
    print(_bar())
    for e in events:
        ts     = (e.get("ts") or "")[11:19]
        agent  = (e.get("agent") or "?")[:14]
        phase  = (e.get("phase") or "?")[:20]
        msg    = (e.get("msg")   or "")[:40]
        status = e.get("status", "?")
        ticket = f"#{e['ticket']}" if e.get("ticket") else "—"

        ok  = status in ("ok", "success", "started")
        err = status == "error"
        status_icon = tick("✓") if ok else (danger("✗") if err else muted("·"))

        a_col = LOG_AGENT_COLOR.get(agent, gray)
        p_col = LOG_PHASE_COLOR.get(phase, white)

        print(
            f"  {muted(ts)}"
            f"  {status_icon}"
            f"  {a_col(agent):<20}"
            f"  {gray(ticket):<6}"
            f"  {p_col(phase):<26}"
            f"  {muted(msg)}"
        )

# ── Main loop ─────────────────────────────────────────────────────────────────

def watch(repo: str, interval: int, repo_root: Path):
    first = True
    while True:
        agents        = _get_lock_data(repo_root)
        tickets       = _get_tickets(repo)
        events        = _get_last_log_events(repo, n=6)
        session_count = _get_session_ticket_count(repo)
        now_ts        = datetime.now(timezone.utc).strftime("%H:%M:%S")

        if first:
            _clear_screen()
            first = False
        else:
            _move_top()

        _header(repo, interval, now_ts, session_count)
        _render_agents(agents)
        _render_tickets(tickets)
        _render_logs(events)

        print(f"\n{_thick_bar()}")
        print(f"  {muted('Next update in')} {yellow(str(interval) + 's')}…")
        sys.stdout.flush()

        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="CAO real-time status watcher")
    parser.add_argument("--interval", type=int, default=30,
                        help="Refresh interval in seconds (default: 30)")
    parser.add_argument("--repo", type=str, default=None,
                        help="owner/repo (auto-detected if omitted)")
    args = parser.parse_args()

    repo = args.repo or _get_repo()
    repo_root = Path(subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True
    ).stdout.strip() or ".")

    print(f"Starting CAO Watch — {repo} (interval: {args.interval}s) …")
    time.sleep(0.4)
    try:
        watch(repo, args.interval, repo_root)
    except KeyboardInterrupt:
        # Check for active agents and offer graceful kill
        agents = _get_lock_data(repo_root)
        if not agents:
            print(f"\n{muted('Watch stopped.')}")
            sys.exit(0)

        print(f"\n\n{_thick_bar()}")
        print(f"  {warn('⚠')}  {bold(white(str(len(agents)) + ' agent(s) still active:'))}")
        for a in agents:
            print(f"    {yellow('#' + a['ticket'])}  {info(a['agent'])}  "
                  f"{gray(a['elapsed_min'])}min  {muted(a['phase'] or '—')}")
        print()
        try:
            ans = input(f"  {white('Send graceful kill to all? [y/N] ')}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans = "n"

        if ans in ("o", "oui", "y", "yes"):
            for a in agents:
                sentinel = repo_root / ".locks" / f"kill-ticket-{a['ticket']}"
                sentinel.touch()
                print(f"  {tick('✓')}  Signal sent → {yellow('#' + a['ticket'])}  "
                      f"{muted('(stopping within 10min)')}")
            stopped_msg = "Watch stopped. Agents will shut down cleanly."
            print(f"\n  {muted(stopped_msg)}")
        else:
            print(f"  {muted('Watch stopped. Agents still running.')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
