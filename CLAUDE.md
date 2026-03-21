# Claude Agents Orchestrator — Automated GitHub Ticket Management

**This kit provides a reusable workflow for managing GitHub tickets with Claude agents.**

Use this in any project to automate enrichment, development, testing, and deployment of features via GitHub issues.

## Quick Start

```bash
# 1. Install the plugin once (see README for settings.json config)
# In Claude Code: /plugins → install claude-agents-orchestrator

# 2. In each project: create labels + dev branch
bash ~/.claude/plugins/claude-agents-orchestrator/SETUP.sh

# 3. Create CLAUDE.md at the project root (see README for template)

# 4. Create your first ticket
gh issue create --title "Feature: ..." --label "to-enrich"

# 5. Run the automation
# In Claude Code:
/cao-process-tickets
```

## What This Kit Provides

### Skills (Global — use in any Claude Code session)

- **`/cao-hello-team-lead`** — Daily standup, load project state
- **`/cao-get-ticket #N`** — Load a GitHub ticket for discussion
- **`/cao-process-tickets`** — Poll tickets and process them (enrichment → dev → test → merge)
- **`/cao-show-logs`** — Read structured logs from agent runs
- **`/cao-save-session`** — Persist session context for future conversations
- **`/cao-maintain-context`** — Audit and update CLAUDE.md + memory files

### Templates (Per-project)

- Issue templates (bug report, feature request)
- Pull request template
- GitHub Actions CI workflow (optional)

### Documentation

- This guide (CLAUDE.md)
- WORKFLOW.md — detailed process documentation
- SETUP.sh — automated setup script

---

## The Workflow (Overview)

```
[1] Create ticket with label "to-enrich"
    ↓
[2] Team-lead enriches (plan + details)
    ↓
[3] You validate → change to "to-dev"
    ↓
[4] Dev implements → posts URL preview → "to-test"
    ↓
[5] You test → tag "godeploy"
    ↓
[6] Auto-merge to dev branch
```

### Ticket States (Labels)

| Label | Meaning |
|-------|---------|
| `to-enrich` | Ready for enrichment (planning) |
| `enriching` | Team-lead agent running (locked) |
| `enriched` | Plan proposed, waiting for your validation |
| `to-dev` | Validated, ready to implement |
| `dev-in-progress` | Dev agent running (locked) |
| `to-test` | Code ready, preview URL posted, ready for testing |
| `deployed` | Merged to dev branch |
| `godeploy` | Tag: signal production deployment |

### Who Does What

| Step | Actor | Tool |
|------|-------|------|
| Create ticket | You | `gh issue create` |
| Enrichment | Claude (Sonnet) | `/cao-process-tickets` or `/ticket` |
| Validation | You | GitHub UI or `gh` CLI |
| Development | Claude (Haiku) | `/cao-process-tickets` |
| Testing | You | URL preview |
| Merge | Claude | `/cao-process-tickets` (detects godeploy tag) |

---

## Setup for a New Project

### 1. Initialize Workflow

```bash
./SETUP.sh "my-project-name"
```

This creates:
- GitHub labels
- Main/dev branches
- `.github/` templates
- Customized CLAUDE.md

### 2. Customize CLAUDE.md

Edit `CLAUDE.md` in your project with:
- Project objective
- Tech stack
- Architecture overview
- Critical files
- Patterns & conventions

(Don't include workflow details — that's what this kit handles)

### 3. Ready

Skills are available globally — no per-project setup needed.

---

## Using the Workflow

### Create a Ticket

```bash
gh issue create \
  --title "Feature: User authentication" \
  --body "Users should be able to log in with email/password" \
  --label "to-enrich"
```

### Option A: Discuss First (Conversational)

```
/ticket #5
→ Loads ticket with fresh context
→ You discuss with team-lead
→ "Ok enrichis le ticket"
→ Agent enriches automatically
```

### Option B: Auto-enrich (Automatic)

```
/cao-process-tickets
→ Detects "to-enrich" + no assignee
→ Launches team-lead agent
→ Agent enriches + changes label → "enriched"
```

### Validate Enrichment

On GitHub:
```
Review the enrichment plan
├─ If OK: change label to "to-dev"
└─ If challenge: comment + change back to "to-enrich"
   → Agent relaunches, responds to feedback
```

### Auto-develop

```
/cao-process-tickets
→ Detects "to-dev" + no assignee
→ Launches dev agent
→ Agent: create branch → implement → verify → post URL
→ Changes label → "to-test"
```

### Test & Deploy

On GitHub:
```
Test the preview URL
├─ If bug: comment feedback, change to "to-dev"
│  → Dev agent relaunches, fixes
└─ If OK: tag "godeploy"
   → Auto: create PR → merge → label "deployed"
```

---

## Key Concepts

### State Machine via Assignation

- **Not assigned** = cronjob/automation can process
- **Assigned to you** = you're reviewing

**Workflow:**
1. You create ticket (not assigned)
2. Agent enriches → you assign yourself (review mode)
3. You validate → you unassign (release to dev)
4. Agent develops → agent re-assigns you (ready to test)
5. You test → you unassign if feedback (release to retry)

### Locked States

Labels `enriching`, `dev-in-progress` prevent multiple agents from processing the same ticket.

### Feedback Loops

If you change label back (to-enrich, to-dev), the agent detects it and re-reads your feedback comments.

---

## Scheduled Tasks (Optional)

For true 24/7 automation, create a scheduled task in Claude Code:

```
/anthropic-skills:schedule
  taskId: "poll-tickets"
  cronExpression: "*/1 * * * *"  # every minute
  prompt: "/cao-process-tickets"
```

Or use Railway/Fly.io cron for production.

---

## Troubleshooting

**"Ticket stuck in enriching"**
- Check if agent hit an error
- Manually change label back to "to-enrich"
- Run `/cao-process-tickets` again

**"Multiple agents processing same ticket"**
- Locked states (enriching, dev-in-progress) should prevent this
- If it happens, manually reset label to previous state

**"Agent doesn't see my feedback"**
- Make sure you changed the label (that signals a state change)
- Agent re-reads comments when label changes

---

## Customization

### Adjust States

Edit the labels in `SETUP.sh` if you want different states.

### Adjust Agent Models

By default:
- **Enrichment**: Sonnet (reasoning, planning)
- **Development**: Haiku (implementation, cost savings)

Change in `/cao-process-tickets` skill if needed.

### Per-Project Config

Create `~/.claude/projects/<project>/memory/workflow-config.md`:
```
# Workflow Config for My Project

## Enrichment Prompts
- Include: architecture review, API design
- Focus on: performance, security

## Dev Prompts
- Enforce: 100% test coverage
- Deploy to: Railway staging only (not prod)

## Review Criteria
- Code review checklist
- Deployment requirements
```

---

## Integration with Your Projects

### Option 1: Submodule

```bash
cd my-project
git submodule add https://github.com/pascalpldev/claude-agents-orchestrator.git .claude-workflow
```

### Option 2: Template (Copy)

```bash
cp -r claude-agents-orchestrator/* my-project/
```

### Option 3: Reference

Just reference this kit in your README:
```
## Development Workflow

This project uses [Claude Agents Orchestrator](https://github.com/pascalpldev/claude-agents-orchestrator).

See the kit's documentation for how to use the automation.
```

---

## Contributing

Issues, PRs welcome. This kit is meant to evolve.

---

**Ready? Create your first ticket with `to-enrich` label and run `/cao-process-tickets`!**
