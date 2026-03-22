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
3. Fetch open issues: `gh issue list --repo $OWNER/$REPO --state open --json number,title,labels,assignees`

## What it does

### 1. Enrichment workflow

**Detects**: `to-enrich` label + no assignee

```
a. Lock: gh issue edit N --add-label "enriching" --remove-label "to-enrich"
b. Launch team-lead agent:
   - Agent reads ticket via gh issue view
   - Writes enrichment plan
   - Posts as comment via gh issue comment
   - Changes label enriching → enriched
c. User is notified (ticket now "enriched")
```

**If challenged**: User changes back to `to-enrich` + comments feedback

```
a. team-lead agent re-reads comments via gh issue view
b. Responds to feedback
c. Changes label to-enrich → enriched
```

### 2. Dev workflow

**Detects**: `to-dev` label + no assignee

```
a. Lock: gh issue edit N --add-label "dev-in-progress" --remove-label "to-dev"
b. Launch dev agent:
   - Agent reads full ticket + plan via gh issue view
   - Creates branch, implements, pushes (git)
   - Creates PR via gh pr create
   - Posts preview URL via gh issue comment
   - Changes label dev-in-progress → to-test
c. User is ready to test
```

**If feedback**: User changes to `to-dev` + comments feedback

```
a. dev agent detects change + feedback via gh issue view
b. Fixes and commits to existing branch (git)
c. Changes label dev-in-progress → to-test
```

### 3. Merge workflow

**Detects**: `godeploy` tag on `to-test` ticket

```
a. Lock: gh issue edit N --add-label "dev-in-progress" --remove-label "to-test"
b. Launch dev agent (godeploy mode):
   - Finds PR via gh pr list
   - Verifies mergeable via gh pr view
   - Merges via gh pr merge
   - Changes label dev-in-progress → deployed
```

## Example execution

```
[On demand or every minute]

1. gh issue list --label "to-enrich"
   → Found: #5, #12

2. For ticket #5:
   - gh issue edit: to-enrich → enriching (lock)
   - Launch team-lead agent → enriches + posts → enriched

3. gh issue list --label "to-dev"
   → Found: #3

4. For ticket #3:
   - gh issue edit: to-dev → dev-in-progress (lock)
   - Launch dev agent → implements + pushes → to-test

5. gh issue list --label "godeploy"
   → Found: #1

6. For ticket #1:
   - gh issue edit: to-test → dev-in-progress (lock)
   - Launch dev agent (godeploy mode) → gh pr merge → deployed
```

## Implementation notes

- Each run is atomic (one ticket processed per state)
- States are locked (enriching, dev-in-progress) to prevent collisions
- Agents detect state transitions to handle challenges/feedback
- GitHub operations use `gh` CLI for issues/PRs; GitHub MCP for `search_code` and CI (`actions_*`)
- Git operations (checkout, commit, push) remain bash — they are local operations
- No hardcoded project name — auto-detected from git remote
