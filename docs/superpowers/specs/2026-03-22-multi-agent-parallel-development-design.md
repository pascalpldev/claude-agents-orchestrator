# Multi-Agent Parallel Development for CAO

**Date:** 2026-03-22
**Status:** Design Document (Awaiting Review)
**Author:** Claude Code Session
**Scope:** Enable multiple Claude agents to work on different GitHub tickets in parallel with complete isolation

---

## Executive Summary

This document describes a **multi-agent worker pool architecture** for the Claude Agents Orchestrator (CAO). Instead of sequential ticket processing (one agent at a time), multiple agents work in parallel—each in their own isolated working directory, database, and git state.

**Key design decisions:**
- Each agent creates its own full repo clone in `.claude/workers/{agent-name}/`
- Docker-style agent names with collision detection (e.g., `dev-proud-falcon`)
- Independent DB instances per agent (each applies migrations at startup)
- Claim/lock system via GitHub comments + labels
- Graceful shutdown with checkpoint/resume capability
- Ghost claim detection (30 min timeout + git activity check)

---

## Problem Statement

**Current CAO limitation:** Sequential processing
```
Ticket #5 (dev) → Agent Dev#1 works → completes →
Ticket #6 (dev) → Agent Dev#2 works → completes →
Ticket #7 (dev) → Agent Dev#3 works → ...

Time: N hours for 3 tickets
```

**Desired:** Parallel processing
```
Ticket #5 (dev) → Agent Dev#1 ┐
Ticket #6 (dev) → Agent Dev#2 ├─ All in parallel
Ticket #7 (dev) → Agent Dev#3 ┘

Time: ~1/3 hours per ticket (linear speedup)
```

**Additional goals:**
- Support multiple enrichment agents (team-leads) enriching tickets simultaneously
- Support multiple dev agents implementing different features in parallel
- Handle database isolation (no migration conflicts)
- Handle dependency conflicts (each agent has own `node_modules`)
- Enable graceful interruption and resume from checkpoints

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
✅ **No shared state:** Agents only coordinate via GitHub (comments, labels, PRs)

---

## Component: Worker (`/cao-worker`)

### Workflow: Infinite Loop

Each agent runs this loop until manually interrupted (`Ctrl+C`):

#### [1] Initialize

```
On first launch:
  ├─ Detect role: dev | team-lead
  ├─ Generate unique agent name:
  │  ├─ Generate: docker-style name (e.g., "proud-falcon")
  │  ├─ Prepend role: "dev-proud-falcon" or "team-lead-proud-falcon"
  │  └─ Verify: mkdir .claude/workers/{agent-name}/
  │     ├─ ✅ Success → use this directory
  │     ├─ ❌ EEXIST → retry with new name (e.g., "dev-quiet-squirrel")
  │
  ├─ Set working directory: cd .claude/workers/{agent-name}/
  ├─ Clone repo: git clone <repo> . (if first launch)
  ├─ Check out dev: git checkout dev
  ├─ Initialize DB:
  │  ├─ Create .agent-db/{agent-name}.db (SQLite)
  │  ├─ Apply all migrations: for file in migrations/*.sql; do sqlite .agent-db/{agent-name}.db < $file; done
  │  └─ Load seed data (if any)
  │
  └─ Log: "🤖 Agent {agent-name} initialized in {agent-dir}"
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
  ├─ Remove tickets with recent "interrupted" comment (from ghost claim cleanup)
  └─ Sort by created_at (FIFO: oldest first)

Select: first available ticket (or `none` if empty)

Log: "🤖 Agent {agent-name} found ticket #{N}: {title}" or "No tickets available, waiting..."
```

#### [3] Claim

```
Atomic claim operation:
  ├─ [3a] Post GitHub comment:
  │       "🤖 Agent {agent-name} claimed at {ISO timestamp}"
  │
  ├─ [3b] Add label: "dev-in-progress" (or "enriching" for team-lead)
  │
  ├─ [3c] Wait 2 seconds (let GitHub sync)
  │
  ├─ [3d] Re-read ticket:
  │       ├─ Count "claimed" comments (excluding older "interrupted" comments)
  │       ├─ If this agent is first "claimed" comment:
  │       │  └─ ✅ Proceed to [4] EXECUTE
  │       │
  │       └─ If another agent is first "claimed":
  │          ├─ Post comment: "🤖 Agent {agent-name} desisting (another agent claimed first)"
  │          ├─ Remove label: "dev-in-progress"
  │          └─ Return to [2] POLL (try next ticket)
  │
  ├─ [3e] Double-check label exists (race condition safety)
  │       └─ If label missing → desist and retry [2]
  │
  └─ Log: "🤖 Agent {agent-name} claimed ticket #{N}"
```

#### [4] Execute

**For DEV agents:**
```
Implement feature:
  ├─ git checkout -b feat/ticket-{N}-{short-name}
  ├─ Read CLAUDE.md and ticket description
  ├─ Implement feature (write code)
  ├─ Run migrations (if needed): sqlite .agent-db/{agent-name}.db < migrations/new.sql
  ├─ Run tests: npm test (or equivalent)
  ├─ Commit changes: git commit -m "feat: {description} (#N)"
  ├─ Push branch: git push origin feat/ticket-{N}-{short-name}
  ├─ Create PR: gh pr create --base dev --head feat/ticket-{N}-{short-name} \
                  --title "ticket #{N}: {title}" \
                  --body "{description + test results}"
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
  ├─ Post GitHub comment: "🤖 Agent {agent-name} completed ticket #{N} at {timestamp}"
  │
  ├─ Update label:
  │  ├─ If dev: "dev-in-progress" → "to-test" (ready for human test)
  │  └─ If team-lead: "enriching" → "enriched" (plan ready for review)
  │
  └─ Log: "✅ Ticket #{N} complete. Agent ready for next ticket."
```

#### [6] Graceful Shutdown (Ctrl+C)

```
When agent receives SIGINT (Ctrl+C):
  ├─ Check current state:
  │  ├─ If idle (waiting for next ticket):
  │  │  └─ Exit immediately
  │  │
  │  └─ If mid-work (executing ticket):
  │     ├─ Generate checkpoint (see Checkpoint/Resume section)
  │     ├─ Push current branch: git push origin feat/ticket-{N}-{short-name}
  │     ├─ Post checkpoint comment (see format below)
  │     ├─ Change label: "dev-in-progress" → "to-dev" (signals: ready to resume)
  │     ├─ Log: "🤖 Agent {agent-name} interrupted. Checkpoint saved for ticket #{N}."
  │     │
  │     └─ Exit gracefully
  │
  └─ (No cleanup needed: next agent will detect checkpoint and resume)
```

#### [7] Loop

```
After completing or desisting on a ticket:
  ├─ Return to [2] POLL
  └─ Repeat forever (until Ctrl+C)
```

---

## Component: Claim/Lock System

### GitHub-Based Lock (Comment + Label)

**Claim format (posted as GitHub comment):**
```
🤖 Agent {agent-name} claimed at {ISO 8601 timestamp}
```

**Example:**
```
🤖 Agent dev-proud-falcon claimed at 2026-03-22T10:30:45Z
```

**How it works:**
1. Agent posts claim comment
2. Agent adds "dev-in-progress" label
3. Agent re-reads ticket to verify sole claim (first claim comment wins)
4. If another agent claimed first: agent posts "desisting" comment and retries

### Desist Format

**When agent loses claim race:**
```
🤖 Agent {agent-name} desisting (another agent claimed first at {timestamp})
```

---

## Component: Checkpoint/Resume System

### Checkpoint Format (GitHub Comment)

When agent is interrupted mid-work, it saves checkpoint as a GitHub comment:

```json
{
  "type": "checkpoint",
  "agent": "dev-proud-falcon",
  "ticket": 5,
  "timestamp": "2026-03-22T10:30:45Z",
  "status": "interrupted",
  "branch": "feat/ticket-5-auth",
  "commits": [
    "abc123: Implement login() function",
    "def456: Add password validation",
    "ghi789: Handle edge cases"
  ],
  "done": [
    "✅ Implement login() in auth.ts",
    "✅ Add password validation",
    "✅ Handle error cases",
    "✅ Add basic unit tests"
  ],
  "todo": [
    "⬜ Add integration tests with DB",
    "⬜ Update API documentation",
    "⬜ Add migration script"
  ],
  "files_modified": [
    "src/auth.ts",
    "src/types.ts",
    "tests/auth.test.ts"
  ],
  "next_step": "Add integration tests with DB to verify auth flow works end-to-end",
  "notes": "Login function complete and unit tested. DB connection works. Ready for integration tests."
}
```

**Posted as markdown code block:**
```
🤖 Agent dev-proud-falcon interrupted, checkpoint saved

[JSON above]
```

### Resume Logic

When a new agent picks up an interrupted ticket:

```
[1] Read checkpoint from GitHub comment
[2] Git operations:
    ├─ git pull origin dev (fetch latest, apply any new migrations)
    ├─ git checkout feat/ticket-{N}-{short-name} (checkout branch from checkpoint)
    ├─ Apply new migrations (if any landed since interrupt):
    │  └─ for file in migrations/*.sql; do sqlite .agent-db/{agent-name}.db < $file; done
    │
    └─ Verify branch state matches checkpoint

[3] Read next_step and notes
[4] Continue coding from next_step
[5] Post update comment: "🤖 Agent {agent-name} resumed ticket #{N} from checkpoint"
[6] On completion: merge PR, same as normal flow
```

---

## Component: Ghost Claim Detection

### Problem

Agent Dev#1 claims ticket but then crashes (no graceful shutdown).
Without detection, ticket stays locked forever.

### Solution: 30-Minute Timeout + Git Activity Check

When agent reads available tickets, it checks for ghost claims:

```
For each ticket with "dev-in-progress" label:
  ├─ Read last "claimed" comment timestamp
  ├─ If last comment > 30 minutes old:
  │  ├─ Check git activity:
  │  │  ├─ git log feat/ticket-{N}-{short-name} --since="30 minutes ago"
  │  │  ├─ If no commits in last 30 min AND
  │  │  ├─ No "interrupted" comment AND
  │  │  ├─ Label "dev-in-progress" still present
  │  │  └─ → GHOST CLAIM DETECTED
  │  │
  │  └─ Cleanup ghost:
  │     ├─ Post comment: "🤖 Ghost claim detected (agent {original-agent} inactive for 30+ min). Releasing."
  │     ├─ Remove label: "dev-in-progress" → back to "to-dev"
  │     └─ This ticket is now available for new claim
  │
  └─ If recent activity → skip (legitimate claim in progress)
```

---

## Database Strategy

### Isolated SQLite per Agent

Each agent maintains its own SQLite database:

```
.claude/workers/dev-proud-falcon/.agent-db/app.db
.claude/workers/dev-quiet-squirrel/.agent-db/app.db
.claude/workers/team-lead-swift-panda/.agent-db/app.db
```

### Migration Application

**On agent startup:**
```
[1] Pull latest dev branch: git pull origin dev
[2] Detect new migrations:
    ├─ Compare local migrations/ with agent's applied migrations (from .agent-migrations-applied.txt)
    ├─ Identify unapplied migrations
    │
    └─ Apply each new migration:
       ├─ sqlite .agent-db/{agent-name}.db < migrations/0001-init-schema.sql
       ├─ sqlite .agent-db/{agent-name}.db < migrations/0002-add-users-table.sql
       └─ sqlite .agent-db/{agent-name}.db < migrations/0003-add-auth-tokens.sql

[3] Record applied migrations:
    └─ echo "0001-init-schema.sql
             0002-add-users-table.sql
             0003-add-auth-tokens.sql" > .agent-migrations-applied.txt
```

**No migration conflicts:** Each agent applies sequentially to its own DB.

---

## Git Workflow

### Branch Strategy

```
main                                    (production, stable)
  ↑
  └─ (user merges when ready)

dev                                     (integration, validated features)
  ├─ feat/ticket-5-auth           (Agent Dev#1, PR created)
  ├─ feat/ticket-6-payments       (Agent Dev#2, PR created)
  └─ feat/ticket-7-notifications  (Agent Dev#3, PR created)
```

### Per-Agent Workflow

**Agent Dev#1:**
```
1. git checkout -b feat/ticket-5-auth (from dev)
2. Implement feature
3. git push origin feat/ticket-5-auth
4. gh pr create --base dev (PR opened)
5. On godeploy label: gh pr merge feat/ticket-5-auth (merge to dev)
```

Each agent works on isolated branch → no conflicts during implementation.

**PRs merge to dev only.** User merges `dev` → `main` for production.

---

## Team-Lead Agent Specifics

### Minimal Setup

Team-lead agents don't need full build environment:

```
.claude/workers/team-lead-swift-panda/
  ├─ .git/
  ├─ src/                     (code read-only)
  ├─ docs/                    (documentation)
  ├─ README.md
  │
  ├─ NO node_modules          (skip: not needed)
  ├─ NO .agent-db/            (skip: not needed)
  └─ NO migrations/           (skip: team-lead doesn't test)
```

**Enrichment workflow:**
```
[1] Read ticket and requirements
[2] Read relevant code (src/)
[3] Analyze architecture
[4] Write enrichment plan (acceptance criteria, approach, risks, effort)
[5] Post as GitHub comment
[6] Change label: "to-enrich" → "enriched"
[7] Done (no code execution, no DB, no tests)
```

---

## Dev Agent Specifics

### Full Setup

Dev agents need complete build environment:

```
.claude/workers/dev-proud-falcon/
  ├─ .git/
  ├─ src/
  ├─ tests/
  ├─ package.json
  ├─ node_modules/           (full dependency tree)
  ├─ .agent-db/              (SQLite with migrations applied)
  └─ .agent-migrations-applied.txt
```

**Development workflow:**
```
[1] Create feature branch
[2] Implement code
[3] Apply migrations (if any schema changes)
[4] Run tests: npm test
[5] Commit and push
[6] Create PR
[7] On "godeploy": merge to dev (auto or user-triggered)
```

---

## Edge Cases & Error Handling

### Case 1: Claim Race

**Scenario:** Two agents both see same ticket, both claim simultaneously.

**Resolution:**
```
Agent A: posts "claimed" comment, adds label
Agent B: posts "claimed" comment, adds label

Both re-read ticket:
  ├─ Agent A sees it posted first (older timestamp) → proceeds
  └─ Agent B sees Agent A posted first → desists
```

**Result:** Agent A wins, Agent B retries with next ticket.

---

### Case 2: Ghost Claim (Agent Crash)

**Scenario:** Agent Dev#1 crashes mid-work, no "interrupted" comment posted.

**Detection:** Another agent notices:
- Last "claimed" comment > 30 min old
- No recent commits on branch
- No "interrupted" comment
→ Ghost claim!

**Resolution:**
```
Cleanup agent:
  ├─ Post: "Ghost claim detected. Releasing."
  ├─ Remove: "dev-in-progress" label
  └─ Next agent can claim ticket
```

---

### Case 3: Dependency Conflict

**Scenario:** Agent A adds `npm install axios`, Agent B adds `npm install lodash` simultaneously.

**Prevention:**
```
✅ Each agent has own node_modules
✅ No shared state
✅ When branches merge to dev, dependency conflicts resolved manually (or via script)
```

**Current approach:** Accept conflicts, resolve at merge time (or implement dependency merge script later).

---

### Case 4: Failed PR Merge

**Scenario:** Agent creates PR, but merge fails (conflicts, test failure).

**Resolution:**
```
Agent detects merge failed:
  ├─ Remains in "to-test" state (PR not auto-merged)
  ├─ Wait for user feedback in PR comments
  ├─ If conflicts: user comments → agent resumes work
  └─ If critical: ticket changed back to "to-dev" → next agent can pick up
```

---

## Setup & Initialization

### First-Time Setup (User)

```bash
# 1. Create base directory structure
mkdir -p ~/.claude/workers

# 2. Each terminal will auto-create its worker directory on first launch
# No pre-setup needed!
```

### Agent First Launch

```bash
# Terminal 1
/cao-worker dev --loop

# Agent auto-generates name (dev-proud-falcon), creates directory, clones repo
```

---

## Implementation Sequence

### Phase 1: Core Worker Skill
- [ ] Create `/cao-worker` skill
- [ ] Implement [1] Initialize, [2] Poll, [3] Claim
- [ ] Implement [4] Execute (basic)
- [ ] Implement [5] Success & [6] Graceful Shutdown
- [ ] Test with 1 agent (dev role)

### Phase 2: Checkpoint/Resume
- [ ] Implement checkpoint format (GitHub comment)
- [ ] Implement resume logic
- [ ] Test interrupt + resume workflow

### Phase 3: Ghost Claim Detection
- [ ] Implement 30-min timeout check
- [ ] Implement git activity verification
- [ ] Test ghost claim cleanup

### Phase 4: Team-Lead Variant
- [ ] Implement minimal setup for team-lead
- [ ] Implement enrichment workflow
- [ ] Test with 1 team-lead agent

### Phase 5: Integration & Scale
- [ ] Test 3 dev agents in parallel
- [ ] Test 2 team-lead agents in parallel
- [ ] Test edge cases (race conditions, timeouts)
- [ ] Validate DB isolation
- [ ] Validate PR merge workflow

---

## Success Criteria

✅ **Isolation:** 3 agents work on 3 different tickets simultaneously with zero conflicts
✅ **Checkpoint:** Agent can gracefully interrupt and resume from checkpoint
✅ **Ghost detection:** Stuck tickets auto-recovered after 30 min
✅ **Speed:** Parallel execution is ~3x faster than sequential (linear speedup)
✅ **Observability:** User sees all agent activity in terminal tabs in real-time
✅ **No breaking changes:** `/cao-process-tickets` (original) still works

---

## References

- CAO CLAUDE.md: Project overview
- CAO README.md: Installation and usage
- GitHub API: Comment posting, label management, PR creation
- Git worktree: Not used (using full clones instead)

