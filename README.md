# Claude Agents Orchestrator

**Automated GitHub ticket management with Claude agents — from idea to deployment.**

Turn Claude Code into a full development team: Claude enriches feature specs, writes code, handles feedback, and merges validated work. You stay in control via GitHub labels and brief discussions.

---

## How it works

```
You create a ticket → label "to-enrich"
        ↓
Claude (Sonnet) writes an enrichment plan as a comment
        ↓
You validate → change label to "to-dev"
        ↓
Claude (Sonnet) creates a branch, implements, opens a PR
        ↓
You test → feedback or tag "godeploy"
        ↓
Claude merges to dev
```

---

## Quickstart (5 minutes)

> **Prerequisite**: plugin installed globally (see [Installation](#installation) below).

```bash
# 1. In your project repo
cd mon-projet
bash ~/.claude/plugins/claude-agents-orchestrator/SETUP.sh

# 2. Create CLAUDE.md at the project root (see template below)

# 3. Create your first ticket
gh issue create --title "Feature: user authentication" --label "to-enrich"
```

Then in Claude Code:
```
/cao-process-tickets
```

Claude posts an enrichment plan as a GitHub comment. Review it on GitHub, change the label to `to-dev`, then run `/cao-process-tickets` again — Claude creates the branch, implements, and opens a PR.

---

## Installation

### Prerequisites

- **Claude Code** — `npm i -g @anthropic-ai/claude-code`
- **GitHub CLI** — `brew install gh` then `gh auth login`
- **Python 3** — pre-installed on macOS and most Linux distros
- **Git**

### Step 1 — Install the plugin (once, global)

Claude Code plugins add skills available in **every** project session. Install once, use everywhere.

**1a.** Add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "claude-agents-orchestrator": {
      "source": {
        "source": "github",
        "repo": "pascalpldev/claude-agents-orchestrator"
      }
    }
  }
}
```

**1b.** In any Claude Code session, run `/plugins`, search for `claude-agents-orchestrator`, and install it.

**1c.** Verify — type `/cao-` in any session and the skills should autocomplete.

### Step 2 — Set up each project (per project)

In your project repo, run the setup script to create GitHub labels and the `dev` branch:

```bash
bash ~/.claude/plugins/claude-agents-orchestrator/SETUP.sh
```

Or manually:

```bash
gh label create "to-enrich" --color "e2a5ff"
gh label create "enriching" --color "ffd700"
gh label create "enriched" --color "90ee90"
gh label create "to-dev" --color "87ceeb"
gh label create "dev-in-progress" --color "ff6347"
gh label create "to-test" --color "ffa500"
gh label create "deployed" --color "32cd32"
gh label create "godeploy" --color "9370db"
```

### Step 3 — Create your project's CLAUDE.md

At the root of each project, create a `CLAUDE.md` so agents understand the codebase:

```markdown
# Project name

## Objective
What this project does in 2-3 sentences.

## Architecture
Stack, key files, entry point.

## Dev commands
- Install: `npm install`
- Start: `npm run dev`
- Test: `npm test`
```

This file is the first thing agents read — keep it accurate.

---

## Daily usage

| When | Command | What happens |
|------|---------|--------------|
| Start of session | `/cao-hello-team-lead` | Overview of all open tickets and their status |
| Load a ticket | `/cao-get-ticket #5` | Discuss a specific ticket with the team-lead |
| Run automation | `/cao-process-tickets` | Enriches / implements / merges based on labels |
| Check agent logs | `/cao-show-logs` | Timeline of what agents did (phases, durations, errors) |
| End of session | `/cao-save-session` | Persists context to CLAUDE.md + memory files |

---

## Skills reference

| Skill | Role |
|-------|------|
| `/cao-hello-team-lead` | Morning standup — project status at a glance |
| `/cao-get-ticket #N` | Load a specific ticket and discuss it with Claude |
| `/cao-process-tickets` | Core automation — poll and process all tickets |
| `/cao-show-logs` | Read structured logs from agent runs |
| `/cao-save-session` | Persist session context for future conversations |
| `/cao-maintain-context` | Audit and update CLAUDE.md + memory files |

---

## Ticket states (GitHub labels)

| Label | Meaning |
|-------|---------|
| `to-enrich` | Ready for enrichment (planning) |
| `enriching` | Team-lead agent running — locked |
| `enriched` | Plan ready, waiting for your validation |
| `to-dev` | Validated, ready to implement |
| `dev-in-progress` | Dev agent running — locked |
| `to-test` | Code ready, PR open, ready to test |
| `deployed` | Merged to dev |
| `godeploy` | Signal: trigger merge to dev |

---

## Git workflow

```
main   ← production (stable)
dev    ← integration (validated features accumulate here)
  └─ feat/ticket-5-feature-name   ← created automatically per ticket
```

- Claude creates `feat/ticket-N-short-name` from `dev`
- On `godeploy`: Claude opens a PR `feat/X` → `dev` and merges it
- You merge `dev` → `main` when ready for production

---

## Agent logs

Agents write structured logs to `~/.claude/projects/logs/<project>/YYYY-MM-DD.jsonl`.

```
/cao-show-logs                  # today's runs, grouped by ticket
/cao-show-logs --ticket 5       # full history for ticket #5
/cao-show-logs --errors         # only error events
/cao-show-logs --last 10        # last 10 log entries
```

Each entry records: timestamp, agent, ticket, phase, status, duration, and contextual data.

---

## Context management

### CLAUDE.md — project source of truth (in the repo)

Update it when a new phase completes, a dependency is added, a pattern changes, or a key file is renamed.

### Memory files — personal context (local only)

Stored in `~/.claude/projects/<project>/memory/` — never committed.

Run `/cao-save-session` at the end of each session. It updates CLAUDE.md and memory files only when justified.

| Memory type | What goes here |
|-------------|---------------|
| `project` | Decisions, phases, deadlines |
| `feedback` | How Claude should/shouldn't behave |
| `user` | Your role, preferences, expertise |
| `reference` | External systems (Linear, Notion, Grafana) |

---

## Optional: Schedule automation

To run `/cao-process-tickets` automatically every minute:

```
/anthropic-skills:schedule
  taskId: "poll-tickets"
  cronExpression: "*/1 * * * *"
  prompt: "/cao-process-tickets"
```

---

## Optional: Preview URLs

The dev agent posts a preview URL per branch when available. This depends on your hosting:

| Platform | Preview per branch? |
|----------|---------------------|
| Railway | ✅ Auto-deploys per branch |
| Render | ✅ Preview environments per PR |
| Vercel / Netlify | ✅ Native preview URLs |
| Fly.io | ⚠️ Possible with scripting |
| None | ✅ Still works — agent skips the URL step |

If using Railway, configure the MCP in `~/.claude/.mcp.json` (never in this repo):

```json
{
  "mcpServers": {
    "railway": {
      "command": "npx",
      "args": ["@railway/mcp"],
      "env": { "RAILWAY_API_TOKEN": "YOUR_TOKEN_HERE" }
    }
  }
}
```

---

## MCP configuration

Agents use the **GitHub MCP** and optionally the **Railway MCP** instead of `gh` CLI. Configure both in `~/.claude/.mcp.json` (local only, never committed):

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "YOUR_TOKEN_HERE" }
    },
    "railway": {
      "command": "npx",
      "args": ["@railway/mcp"],
      "env": { "RAILWAY_API_TOKEN": "YOUR_TOKEN_HERE" }
    }
  }
}
```

The Railway block is optional — omit it if you don't use Railway.

### Why MCP instead of `gh` CLI?

| | GitHub MCP | `gh` CLI |
|---|---|---|
| Structured data | Returns typed objects | Returns text to parse |
| Reliability | No shell escaping issues | Fragile with special characters |
| Composability | Works inside any agent | Requires a bash context |
| PR creation | `create_pull_request` | `gh pr create` |
| Search | `search_code` across the repo | `gh search code` |

SETUP.sh still uses `gh` CLI for label creation — that runs outside of agents, where MCP is not available.

---

## Troubleshooting

**Ticket stuck in `enriching` or `dev-in-progress`**
→ Check logs: `/cao-show-logs --errors`
→ Manually reset label to previous state (`to-enrich` or `to-dev`)

**Agent doesn't see my feedback**
→ Change the label after commenting — the label change is the signal

**Skills not showing up**
→ Run `/plugins` and verify `claude-agents-orchestrator` is installed

---

## Requirements

- **Claude Code** (CLI)
- **GitHub CLI** (`gh`) authenticated
- **Python 3** — pre-installed on macOS and most Linux distros
- A GitHub repo with `main` and `dev` branches

---

## Security

No secrets, API keys, or project-specific config in this repo. Sensitive values go in:
- `~/.claude/.mcp.json` — MCP tokens (local, never committed)
- `~/.claude/projects/<project>/memory/` — personal context (local, never committed)
- `.env` in each project (gitignored)

---

## License

MIT
