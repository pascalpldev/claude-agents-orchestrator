# Multi-Agent Parallel Development for CAO — Revised Design (v2)

**Date:** 2026-03-22 (Revised after technical analysis)
**Status:** Design Document (Architecture & Concurrency Fixes Applied)
**Author:** Claude Code Session + Subagent Technical Review
**Target Scale:** 5-20 concurrent agents
**Scope:** Enable multiple Claude agents to work on different GitHub tickets in parallel with complete isolation and safety guarantees

---

## Executive Summary

This is a **revised design** that incorporates critical fixes from technical analysis:

**Key improvements over v1:**
- ✅ **Atomic claim mechanism** (git-based, not GitHub comments)
- ✅ **DB-backed migration tracking** (not fragile text files)
- ✅ **Atomic graceful shutdown** (reverse operation order)
- ✅ **Idempotent migration enforcement** (prevents data corruption)
- ✅ **Verified resumability** (branch HEAD validation)

**Design now safe for:** 5-20 concurrent agents
**Previously unsafe for:** 3+ agents (race conditions, data corruption)

---

## Problem Statement

**Original Issue (v1):** Sequential processing bottleneck
- Tickets processed one-at-a-time
- N tickets = N × hours_per_ticket

**Desired:** Parallel processing
- 5 agents on 5 tickets simultaneously
- 5 × speedup (linear)

**v1 Risks Identified & Fixed:**
- Race conditions in claim mechanism ✅ → git-based atomic lock
- Data corruption from async migrations ✅ → DB-backed tracking
- Ticket lockup on shutdown ✅ → reverse operation order
- Silent schema mismatches ✅ → migration idempotency enforcement

---

## Architecture Overview

### Directory Structure

```
/Users/pascalliu/Sites/claude-workflow-kit/
  ├─ main branch                    (production)
  ├─ dev branch                     (integration)
  │
  └─ .claude/
     └─ workers/                    ← All agent working directories
        ├─ dev-proud-falcon/        ← Agent Dev#1 (full clone)
        │  ├─ .git/
        │  ├─ src/
        │  ├─ package.json
        │  ├─ node_modules/         (agent's own dependencies)
        │  ├─ .agent-db/
        │  │  └─ app.db             (SQLite, isolated per agent)
        │  └─ .agent-checkpoint/
        │     └─ latest.json        (latest checkpoint)
        │
        ├─ dev-quiet-squirrel/      ← Agent Dev#2 (full clone)
        │
        ├─ team-lead-swift-panda/   ← Agent TL#1 (minimal clone)
        │  ├─ .git/
        │  └─ src/                  (code read-only, for enrichment)
        │
        └─ team-lead-bright-salmon/ ← Agent TL#2 (minimal clone)
```

### Session Layout (Terminal Tabs)

```
Terminal Tab 1: /cao-worker dev --loop         (Agent: dev-proud-falcon)
Terminal Tab 2: /cao-worker dev --loop         (Agent: dev-quiet-squirrel)
Terminal Tab 3: /cao-worker dev --loop         (Agent: dev-lazy-badger)
Terminal Tab 4: /cao-worker team-lead --loop   (Agent: team-lead-swift-panda)
Terminal Tab 5: /cao-worker team-lead --loop   (Agent: team-lead-bright-salmon)
```

User sees all agent logs in real-time across tabs.

### Isolation Guarantees

✅ **Working directory isolation:** Each agent has own directory (zero file conflicts)
✅ **Dependency isolation:** Each agent has own `node_modules` (zero npm conflicts)
✅ **Database isolation:** Each agent has own SQLite instance (zero data conflicts)
✅ **Git isolation:** Each agent has own git index and checked-out branch
✅ **Claim isolation:** Atomic git-based lock (zero claim race conditions)
✅ **No shared state:** Agents only coordinate via GitHub (PRs) and git (branch state)

---

## Component: Worker (`/cao-worker`)

### Workflow: Infinite Loop

Each agent runs this loop until manually interrupted (`Ctrl+C`):

#### [1] Initialize

```
On first launch:
  ├─ Detect role: dev | team-lead
  ├─ Generate unique agent name:
  │  ├─ Use docker-style names (e.g., "proud-falcon")
  │  ├─ Prepend role: "dev-proud-falcon"
  │  └─ Verify: mkdir .claude/workers/{agent-name}/
  │     ├─ ✅ Success → use this directory
  │     ├─ ❌ EEXIST → retry with new name
  │
  ├─ Set working directory: cd .claude/workers/{agent-name}/
  ├─ Clone repo: git clone <repo> . (if first launch)
  ├─ Check out dev: git checkout dev
  ├─ Initialize DB:
  │  ├─ Create .agent-db/{agent-name}.db (SQLite)
  │  ├─ Apply all migrations:
  │  │  └─ [See revised migration system below]
  │  └─ Load seed data (if any)
  │
  └─ Log: "🤖 Agent {agent-name} initialized"
```

#### [2] Poll

```
List available tickets:
  ├─ If dev agent:
  │  └─ gh issue list --label "to-dev" --search "no:assignee"
  │
  └─ If team-lead agent:
     └─ gh issue list --label "to-enrich" --search "no:assignee"

Filter candidates:
  ├─ Remove tickets with "dev-in-progress" or "enriching" label
  ├─ Remove tickets that have a `.claimed-by` file in dev branch
  │  (means another agent currently has atomic lock)
  └─ Sort by created_at (FIFO: oldest first)

Select: first available ticket (or `none` if empty)

Log: "🤖 Agent {agent-name} found ticket #{N}" or "No tickets available, waiting..."
```

#### [3] Claim (Revised: Git-Atomic Lock)

**CHANGE FROM v1:** Instead of GitHub comments + labels, use git-based atomic lock.

```
Atomic claim operation (via git):

[3a] Create local claim file:
     └─ echo "{\"agent\": \"$AGENT_NAME\", \"claimed_at\": \"$(date -Iseconds)\"}" > .claimed-by-$AGENT_NAME

[3b] Add and commit claim file:
     ├─ git add .claimed-by-$AGENT_NAME
     ├─ git commit -m "claim: ticket #$N by agent $AGENT_NAME"
     │
     └─ git push origin dev
        ├─ ✅ Push succeeds → claim WON (atomic operation)
        ├─ ❌ Push fails (branch moved/conflict) → claim LOST
        │  ├─ Rollback locally: git reset --hard origin/dev
        │  └─ Return to [2] POLL (try next ticket)

[3c] Verify claim still valid:
     ├─ Check if .claimed-by-$AGENT_NAME still exists in HEAD
     ├─ Check if any other .claimed-by-* files exist
     │  ├─ If yes → another agent beat us → desist
     │  └─ If no → we're alone → proceed

[3d] Add label "dev-in-progress" (for visibility in GitHub UI)
     └─ gh issue edit #N --add-label "dev-in-progress"

└─ Log: "🤖 Agent {agent-name} claimed ticket #{N} via atomic git lock"
```

**Why this is better:**
- ✅ Git push is atomic (all-or-nothing)
- ✅ No GitHub API eventual consistency issues
- ✅ No 2-second wait needed
- ✅ Claim history visible in git log
- ✅ Scales to 20+ agents (git handle conflicts gracefully)

#### [4] Execute

**For DEV agents:**
```
Implement feature:
  ├─ git checkout -b feat/ticket-{N}-{short-name} (from HEAD, which has .claimed-by file)
  ├─ Delete the .claimed-by file from working directory (not needed on feature branch)
  │  └─ rm .claimed-by-$AGENT_NAME (don't commit this to feature branch)
  │
  ├─ Read CLAUDE.md and ticket description
  ├─ Implement feature (write code)
  ├─ Apply migrations (if needed):
  │  └─ [See revised migration system below]
  │
  ├─ Run tests: npm test
  ├─ Commit changes: git commit -m "feat: {description} (#N)"
  ├─ Push branch: git push origin feat/ticket-{N}-{short-name}
  ├─ Create PR: gh pr create --base dev --head feat/ticket-{N}-{short-name}
  │
  └─ Log: "🤖 Agent {agent-name} created PR for ticket #{N}"
```

**For TEAM-LEAD agents:**
```
Enrich ticket:
  ├─ Read ticket description and related discussions
  ├─ Read relevant code (src/ directory)
  ├─ Analyze: architecture, dependencies, test coverage
  ├─ Write enrichment plan:
  │  ├─ Acceptance criteria
  │  ├─ Implementation approach
  │  ├─ Risk assessment
  │  └─ Estimated effort
  │
  ├─ Post GitHub comment: "{enrichment plan}"
  ├─ Change label: "to-enrich" → "enriched"
  │
  └─ Log: "🤖 Agent {agent-name} enriched ticket #{N}"
```

#### [5] Success Path

```
On successful completion:
  ├─ Post GitHub comment: "🤖 Agent {agent-name} completed ticket #{N}"
  │
  ├─ Back on dev branch:
  │  ├─ git checkout dev
  │  ├─ Delete claim file: rm .claimed-by-$AGENT_NAME (if it still exists)
  │  ├─ git add --all
  │  ├─ git commit -m "release-claim: ticket #N completed" (if anything changed)
  │  ├─ git push origin dev
  │  │
  │  └─ Update label: "dev-in-progress" → "to-test"
  │
  └─ Log: "✅ Ticket #{N} complete. Claim released. Agent ready for next ticket."
```

#### [6] Graceful Shutdown (Revised: Reverse Order)

```
When agent receives SIGINT (Ctrl+C):
  ├─ Check current state:
  │  ├─ If idle (waiting for next ticket):
  │  │  └─ Exit immediately
  │  │
  │  └─ If mid-work (executing ticket):
  │     ├─ [IMPORTANT: REVERSE ORDER FROM v1]
  │     │
  │     ├─ STEP 1: Change label immediately
  │     │          "dev-in-progress" → "to-dev"
  │     │          (signals: this ticket is available for next agent)
  │     │
  │     ├─ STEP 2: Push current branch
  │     │          git push origin feat/ticket-{N}-{short-name}
  │     │
  │     ├─ STEP 3: Post checkpoint comment
  │     │          (nice-to-have, but not critical)
  │     │
  │     ├─ STEP 4: Release claim on dev branch
  │     │          git checkout dev
  │     │          rm .claimed-by-$AGENT_NAME
  │     │          git add -A && git commit -m "release-claim: interrupted"
  │     │          git push origin dev
  │     │
  │     └─ Log: "🤖 Agent {agent-name} interrupted. Claim released. Checkpoint saved."
  │
  └─ Exit gracefully
```

**Why reverse order matters:**
- If label change fails → at least claim is released on dev, ticket remains available
- If checkpoint post fails → not critical, label already changed
- Worst case: ticket in "to-dev" without checkpoint comment (agent can retry)
- Best case: everything succeeds

#### [7] Loop

```
After completing or releasing a ticket:
  ├─ Return to [2] POLL
  └─ Repeat forever (until Ctrl+C)
```

---

## Component: Migration System (Revised)

### v1 Problem
```
Text file tracking: .agent-migrations-applied.txt
  ├─ Can be corrupted mid-write
  ├─ No checksums
  ├─ Not atomic with DB changes
  ├─ Can diverge from reality
```

### v2 Solution: Database-Backed Migration Tracking

#### Setup: First Migration (0000)

```sql
-- migrations/0000-init-migration-tracking.sql
-- This migration MUST be applied first by all agents

CREATE TABLE IF NOT EXISTS _migrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,          -- '0001-init-schema.sql'
  checksum TEXT NOT NULL,              -- SHA256 hash
  applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  applied_by TEXT,                     -- Agent name

  UNIQUE(name, checksum)               -- Prevent duplicate application
);

CREATE INDEX idx_migrations_name ON _migrations(name);
```

#### Migration Application Logic

```
[1] Load all migration files from migrations/ directory
    └─ Sort by name (0001, 0002, 0003, etc.)

[2] For each migration file:
    ├─ Calculate checksum: sha256sum {migration_file}
    ├─ Query: SELECT * FROM _migrations WHERE name = '{file}'
    │
    ├─ If exists in DB:
    │  ├─ Verify checksum matches
    │  │  ├─ ✅ Match → skip (already applied)
    │  │  ├─ ❌ Mismatch → FATAL ERROR (migration file was modified)
    │  │     └─ Log: "FATAL: Migration {file} was modified after application. This is unsafe."
    │  │        Post GitHub comment on ticket with error
    │  │        Exit with error code
    │  │
    │  └─ If not exists in DB → apply it:
    │     ├─ BEGIN TRANSACTION
    │     ├─ Read migration file into SQL statements
    │     ├─ Execute each statement
    │     ├─ INSERT INTO _migrations (name, checksum, applied_by)
    │     ├─ COMMIT TRANSACTION
    │     │
    │     └─ [If any error: ROLLBACK automatically]

[3] Log: "✅ All migrations applied. Agent DB is ready."
```

**Key safety features:**
- ✅ Atomic per-migration (BEGIN/COMMIT)
- ✅ Checksum validation (detects modification)
- ✅ Idempotent tracking (can't apply twice)
- ✅ Queryable state (see what's applied)
- ✅ Resume-safe (resume just re-runs this logic)

#### Idempotent Migration Requirements

All migrations MUST be idempotent. Template:

```sql
-- ✅ GOOD: Idempotent patterns

CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';
  -- (SQLite allows this; idempotent in SQLite)

-- For insertions, use UPSERT:
INSERT INTO system_config (key, value) VALUES ('version', '2.0')
ON CONFLICT(key) DO UPDATE SET value='2.0';

-- ❌ BAD: Non-idempotent (don't use these)

CREATE TABLE users (...);  -- Fails on re-run

DROP TABLE IF EXISTS old_table;
  -- (While safe, indicates destructive change; avoid)

INSERT INTO users VALUES (1, 'alice');
  -- (Not idempotent; use UPSERT instead)
```

**Code review checklist:**
```
☑️ All CREATE TABLE use IF NOT EXISTS
☑️ All CREATE INDEX use IF NOT EXISTS
☑️ All INSERT use ON CONFLICT DO UPDATE or IF NOT EXISTS
☑️ No DROP operations (they're destructive)
☑️ Schema additions only (add columns, never rename or delete)
☑️ Foreign keys properly defined
☑️ Migration file name is sequential (0001, 0002, 0003...)
```

---

## Component: Checkpoint/Resume System (Revised)

### Checkpoint Format (GitHub Comment)

When agent is interrupted mid-work, it saves checkpoint as a GitHub comment:

```json
{
  "type": "checkpoint",
  "agent": "dev-proud-falcon",
  "ticket": 5,
  "timestamp": "2026-03-22T10:30:45Z",
  "status": "ready_to_resume",
  "branch": "feat/ticket-5-auth",

  "commits": [
    "abc123: Implement login() function",
    "def456: Add password validation"
  ],

  "done": [
    "✅ Implement login() in auth.ts",
    "✅ Add password validation",
    "✅ Handle error cases"
  ],

  "todo": [
    "⬜ Add integration tests with DB",
    "⬜ Update API documentation"
  ],

  "files_modified": [
    "src/auth.ts",
    "src/types.ts"
  ],

  "migrations_applied": [
    "0000-init-migration-tracking.sql",
    "0001-init-schema.sql",
    "0002-add-auth-tokens.sql"
  ],

  "next_step": "Add integration tests for login flow",
  "notes": "Login function complete. DB schema ready. Tests can start."
}
```

### Resume Logic (Revised: Branch Validation)

When a new agent picks up an interrupted ticket:

```
[1] Read checkpoint from GitHub comment
    └─ Parse JSON

[2] Verify branch state matches checkpoint:
    ├─ git fetch origin
    ├─ Get actual HEAD commit SHA: git rev-parse origin/feat/ticket-{N}-{short-name}
    ├─ Extract expected commit from checkpoint: checkpoints.commits[0]
    │
    ├─ If actual_sha != expected_sha:
    │  ├─ POST error comment: "❌ Resume failed: branch has diverged. Branch HEAD: {actual_sha}, expected: {expected_sha}"
    │  ├─ Change label back: "to-dev"
    │  └─ EXIT with error (manual intervention needed)
    │
    └─ If match → proceed

[3] Git operations:
    ├─ git pull origin dev (fetch latest)
    ├─ git checkout feat/ticket-{N}-{short-name}
    │
    └─ Apply new migrations (if any landed since interrupt)
       ├─ [Run migration system from above]
       └─ If any migration failed → EXIT, don't continue

[4] Read next_step from checkpoint
    └─ Resume implementation from that point

[5] On completion:
    ├─ Post update comment: "🤖 Agent {agent-name} resumed ticket #{N} and completed it"
    ├─ Merge PR (same as normal flow)
    └─ Release claim
```

---

## Component: Ghost Claim Detection (Revised)

### Problem
Agent crashes without posting "interrupted" comment. Claim remains on dev branch.

### Solution: 60-Minute Timeout + Heartbeat

```
When agent polls for tickets:
  ├─ Check if any .claimed-by-* files exist in dev branch
  ├─ For each claim file found:
  │  ├─ Get commit timestamp: git log -1 --format=%cI .claimed-by-{agent}
  │  ├─ Check if > 60 minutes old
  │  ├─ Check git activity on associated branch:
  │  │  ├─ git log feat/ticket-{N}-* --since="60 minutes ago"
  │  │  ├─ If no commits in 60 min AND
  │  │  ├─ No associated feature branch exists AND
  │  │  ├─ No checkpoint comment
  │  │  └─ → GHOST CLAIM DETECTED
  │  │
  │  └─ Cleanup:
  │     ├─ git checkout dev
  │     ├─ git rm .claimed-by-{agent}
  │     ├─ git commit -m "cleanup: ghost claim detected for {agent}"
  │     ├─ git push origin dev
  │     ├─ Post GitHub comment: "🤖 Ghost claim cleaned up. Ticket #{N} is available."
  │     └─ Change label back: "dev-in-progress" → "to-dev"
  │
  └─ Now ticket is available for new claim
```

**Heartbeat (Optional, for faster recovery):**
If implemented, agent posts comment every 20 minutes:
```
"🤖 Agent {agent-name} heartbeat: still working on ticket #{N} (elapsed: 20 min)"
```

This prevents false ghost detection on slow work.

---

## Setup & Initialization

### First-Time Setup (User)

```bash
# 1. Ensure migrations directory exists
mkdir -p migrations

# 2. Create first migration (0000): migration tracking
cat > migrations/0000-init-migration-tracking.sql << 'EOF'
CREATE TABLE IF NOT EXISTS _migrations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  checksum TEXT NOT NULL,
  applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  applied_by TEXT
);
CREATE INDEX idx_migrations_name ON _migrations(name);
EOF

# 3. Create worker base directory
mkdir -p ~/.claude/workers

# 4. Done! Each agent will auto-create its own directory on first launch
```

### Agent First Launch

```bash
# Terminal 1
/cao-worker dev --loop

# Agent auto-generates name (dev-proud-falcon), creates directory, clones repo
# Applies all migrations from migrations/
# Ready to poll for tickets
```

---

## Implementation Sequence

### Phase 1: Git-Based Claim System (2 hours)
- [ ] Replace comment+label with .claimed-by file
- [ ] Implement git push atomicity check
- [ ] Test with 2 concurrent agents

### Phase 2: Database Migration Tracking (1 hour)
- [ ] Create migration 0000 with _migrations table
- [ ] Implement checksum-based validation
- [ ] Add migration sorting + sequential check

### Phase 3: Graceful Shutdown & Resume (1.5 hours)
- [ ] Reverse operation order (label first, then checkpoint)
- [ ] Add branch HEAD validation on resume
- [ ] Test interrupt + resume workflow

### Phase 4: Idempotent Migrations (30 minutes)
- [ ] Create migration template
- [ ] Add code review checklist
- [ ] Document requirements in CLAUDE.md

### Phase 5: Safety & Scale Testing (2 hours)
- [ ] Test with 3 concurrent agents
- [ ] Test with 5 concurrent agents
- [ ] Stress test: rapid claim/release cycles

**Total: ~7 hours** to production-ready for 5-20 agents

---

## Success Criteria

✅ **Atomicity:** Git-based claim prevents duplicate work
✅ **Data safety:** DB-backed migration tracking prevents corruption
✅ **Resume safety:** Branch HEAD validation prevents silent corruption
✅ **Scale:** 5-20 agents work without race conditions
✅ **Observability:** Agent logs visible in real-time across tabs
✅ **Backward compat:** `/cao-process-tickets` (original) still works
✅ **No breaking changes:** Existing projects unaffected

---

## Risk Mitigation Summary

| Original Risk | v1 Issue | v2 Fix |
|---|---|---|
| Claim race condition | Comment ordering ambiguous | Git-atomic push |
| Migration corruption | Text file tracking | DB-backed with checksums |
| Ticket lockup | Shutdown not atomic | Reverse operation order |
| Resume silent failures | No branch validation | HEAD commit verification |
| Idempotency violation | Not enforced | Template + checklist |
| Ghost claims | 30 min timeout | 60 min timeout + heartbeat |

---

## References

- Original Design (v1): `2026-03-22-multi-agent-parallel-development-design.md`
- Technical Analysis: `/docs/superpowers/analysis/`
  - Failure Modes: 12 issues found, 6 CRITICAL
  - Database Risks: 10 issues found, 5 HIGH
  - Concurrency Risks: 8 issues found, 5 CRITICAL
- This Revision (v2): Incorporates all CRITICAL fixes, quick-fixes for operational issues

---

## Glossary

- **Atomic claim:** Git push succeeds entirely or fails entirely (no partial state)
- **Idempotent migration:** Can be applied multiple times with same result
- **Checkpoint:** Saved agent state (branch, commits, todo list, next step)
- **Ghost claim:** Claim file exists but agent crashed (no active work)
- **Heartbeat:** Periodic signal that agent is still active
- **Claim file:** `.claimed-by-{agent-name}` committed to dev branch as atomic lock

