---
name: cao-process-tickets
description: |
  Poll GitHub tickets and process them through the enrichment and dev workflows.

  This is the core automation skill — runs on demand or every minute via scheduled task.
  It detects tickets in various states and automatically launches enrichment or dev agents.

  States handled:
  - to-enrich + no assignee → team-lead enriches
  - enriching → team-lead relaunches if challenge/feedback detected
  - to-dev + no assignee → dev agent implements
  - to-test → dev agent relaunches if feedback detected
  - godeploy tag → create PR and merge
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# /cao-process-tickets — Poll and process GitHub tickets

Core automation workflow. Detects tickets in various states and launches the appropriate agent.

## Context detection

Before processing:
1. Run `git remote get-url origin` to extract OWNER and REPO
2. Read the project's `CLAUDE.md` for architecture context
3. Fetch open issues using GitHub MCP `list_issues` (owner: $OWNER, repo: $REPO, state: open)

## What it does

### 1. Enrichment workflow

**Detects**: `to-enrich` label + no assignee

```
a. Lock: use GitHub MCP issue_write to change label to-enrich → enriching
b. Launch team-lead agent:
   - Agent reads ticket via issue_read
   - Writes enrichment plan
   - Posts as comment via add_issue_comment
   - Changes label enriching → enriched via issue_write
c. User is notified (ticket now "enriched")
```

**If challenged**: User changes back to `to-enrich` + comments feedback

```
a. team-lead agent re-reads comments via issue_read
b. Responds to feedback
c. Changes label to-enrich → enriched via issue_write
```

### 2. Dev workflow

**Detects**: `to-dev` label + no assignee

```
a. Lock: use GitHub MCP issue_write to change label to-dev → dev-in-progress
b. Launch dev agent:
   - Agent reads full ticket + plan via issue_read
   - Creates branch, implements, pushes (bash)
   - Creates PR via create_pull_request MCP
   - Posts preview URL via add_issue_comment
   - Changes label dev-in-progress → to-test via issue_write
c. User is ready to test
```

**If feedback**: User changes to `to-dev` + comments feedback

```
a. dev agent detects change + feedback via issue_read
b. Fixes and commits to existing branch (bash)
c. Changes label dev-in-progress → to-test via issue_write
```

### 3. Merge workflow

**Detects**: `godeploy` tag on `to-test` ticket

```
a. Lock: use GitHub MCP issue_write to change label to-test → dev-in-progress
b. Launch dev agent (godeploy mode):
   - Finds PR via list_pull_requests MCP
   - Verifies mergeable via pull_request_read MCP
   - Merges via merge_pull_request MCP
   - Changes label dev-in-progress → deployed via issue_write
```

## Example execution

```
[On demand or every minute]

1. GitHub MCP list_issues (label: to-enrich)
   → Found: #5, #12

2. For ticket #5:
   - issue_write: to-enrich → enriching (lock)
   - Launch team-lead agent → enriches + posts → enriched

3. GitHub MCP list_issues (label: to-dev)
   → Found: #3

4. For ticket #3:
   - issue_write: to-dev → dev-in-progress (lock)
   - Launch dev agent → implements + pushes → to-test

5. GitHub MCP list_issues (label: godeploy)
   → Found: #1

6. For ticket #1:
   - issue_write: to-test → dev-in-progress (lock)
   - Launch dev agent (godeploy mode) → merge_pull_request → deployed
```

## Implementation notes

- Each run is atomic (one ticket processed per state)
- States are locked (enriching, dev-in-progress) to prevent collisions
- Agents detect state transitions to handle challenges/feedback
- All GitHub operations use GitHub MCP (never `gh` CLI)
- Git operations (checkout, commit, push) remain bash — they are local operations
- No hardcoded project name — auto-detected from git remote
