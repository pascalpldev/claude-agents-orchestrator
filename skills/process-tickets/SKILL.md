---
name: process-tickets
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

# /process-tickets — Poll and process GitHub tickets

Core automation workflow. Detects tickets in various states and launches the appropriate agent.

## Context detection

Before processing, detect the current project:
1. Run `git remote get-url origin` to identify the repo
2. Read the project's `CLAUDE.md` for architecture context
3. Check open issues via `gh issue list`

## What it does

### 1. Enrichment workflow

**Detects**: `to-enrich` label + no assignee

```
a. Change label: to-enrich → enriching (lock)
b. Launch team-lead agent:
   - Read ticket body + title
   - Write enrichment plan
   - Post as comment
   - Change label: enriching → enriched
c. User is notified (ticket now "enriched")
```

**If challenged**: User changes back to `to-enrich` + comments feedback

```
a. Team-lead agent detects the change + comments
b. Reads the user's feedback
c. Posts response or clarifying questions
d. Change label: to-enrich → enriched
```

### 2. Dev workflow

**Detects**: `to-dev` label + no assignee

```
a. Change label: to-dev → dev-in-progress (lock)
b. Launch dev agent:
   - Read full ticket + plan comments
   - Create branch: feat/ticket-N-short-name
   - Implement according to plan
   - Verify deployment (health check)
   - Post URL preview
   - Change label: dev-in-progress → to-test
c. User is assigned (ready to test)
```

**If feedback**: User changes to `to-dev` + comments feedback

```
a. Dev agent detects change + feedback comments
b. Either asks clarifications OR fixes directly
c. Commits fix to existing branch
d. Redeploys
e. Change label: dev-in-progress → to-test
```

### 3. Merge workflow

**Detects**: `godeploy` tag on `to-test` ticket

```
a. Change label: to-test → dev-in-progress (lock)
b. Launch dev agent:
   - Create PR: feat/X → dev
   - Run tests (GitHub Actions)
   - If tests pass: auto-merge
   - Change label: dev-in-progress → deployed
c. Ticket is closed or marked deployed
```

## Example execution

```
[On demand or every minute]

1. gh issue list --label "to-enrich" --assignee ""
   → Found: #5, #12

2. For ticket #5:
   - gh issue edit #5 --remove-label "to-enrich" --add-label "enriching"
   - Launch team-lead agent
   - Agent enriches + posts + changes label → enriched

3. gh issue list --label "to-dev" --assignee ""
   → Found: #3

4. For ticket #3:
   - gh issue edit #3 --remove-label "to-dev" --add-label "dev-in-progress"
   - Launch dev agent
   - Agent implements + verifies + posts URL → to-test

5. gh issue list --label "godeploy"
   → Found: #1

6. For ticket #1:
   - Launch merge agent → PR → merge → deployed
```

## Implementation notes

- Each run is atomic (one ticket processed per state)
- States are locked (enriching, dev-in-progress) to prevent collisions
- Agents detect state transitions to handle challenges/feedback
- All changes are via `gh` CLI for auditability
- No hardcoded project name — auto-detected from git remote
