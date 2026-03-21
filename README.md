# Claude Workflow Kit

**Automated GitHub ticket management with Claude agents — from idea to deployment.**

This kit turns Claude Code into a full development team: Claude enriches feature specs, writes code, handles feedback, and merges validated work. You stay in control via GitHub labels and brief discussions.

---

## What it does

```
You create a ticket (GitHub issue, label "to-enrich")
        ↓
Claude (Sonnet) writes an enrichment plan as a comment
        ↓
You validate → change label to "to-dev"
        ↓
Claude (Haiku) creates a branch, implements, posts a preview URL
        ↓
You test → feedback or tag "godeploy"
        ↓
Claude creates a PR, merges to dev
```

### Skills provided

| Skill | Trigger | Role |
|-------|---------|------|
| `/hello-team-lead` | Start of day | Project standup — see all open tickets and their status |
| `/get-ticket #N` | Anytime | Load a specific ticket and discuss it with Claude |
| `/process-tickets` | On demand / every minute | Poll all tickets and launch the right agent for each state |
| `/save-session` | End of session | Update CLAUDE.md and memory files to persist context |

### Ticket states (GitHub labels)

| Label | Meaning |
|-------|---------|
| `to-enrich` | Ready for enrichment (planning) |
| `enriching` | Team-lead agent running — locked |
| `enriched` | Plan ready, waiting for your validation |
| `to-dev` | Validated, ready to implement |
| `dev-in-progress` | Dev agent running — locked |
| `to-test` | Code ready, preview URL posted |
| `deployed` | Merged to dev |
| `godeploy` | Signal: trigger production merge |

---

## Installation

### 1. Install the plugin (Claude Code)

Add this to your `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "claude-workflow-kit": {
      "source": {
        "source": "github",
        "repo": "pascalpldev/claude-workflow-kit"
      }
    }
  }
}
```

Then in Claude Code, install the `claude-workflow-kit` plugin. The skills will be available globally across all your projects.

> The plugin auto-detects the current project from `git remote` — no per-project configuration needed.

### 2. Set up GitHub labels

In each project repo, create the required labels:

```bash
gh label create "to-enrich" --color "#0075ca"
gh label create "enriching" --color "#e4e669"
gh label create "enriched" --color "#0e8a16"
gh label create "to-dev" --color "#d93f0b"
gh label create "dev-in-progress" --color "#e4e669"
gh label create "to-test" --color "#0075ca"
gh label create "deployed" --color "#6f42c1"
gh label create "godeploy" --color "#b60205"
```

Or run the provided setup script:

```bash
./SETUP.sh
```

### 3. Set up your project's CLAUDE.md

At the root of each project, create a `CLAUDE.md` with:

```markdown
# Project name

## Objective
What this project does in 2-3 sentences.

## Architecture
Stack, key files, entry point.

## Dev workflow
See [Claude Workflow Kit](https://github.com/pascalpldev/claude-workflow-kit).
```

This file is what agents read first — keep it accurate.

### 4. Optional: Schedule automation

To run `/process-tickets` automatically every minute without manual intervention, create a scheduled task in Claude Code:

```
/anthropic-skills:schedule
  taskId: "poll-tickets"
  cronExpression: "*/1 * * * *"
  prompt: "/process-tickets"
```

---

## Git workflow

This kit assumes a two-branch model:

```
main   ← production (stable)
dev    ← integration (validated features accumulate here)
  └─ feat/ticket-5-feature-name   ← created automatically per ticket
```

**What happens automatically:**
- Claude creates `feat/ticket-N-short-name` branches from `dev`
- When you tag `godeploy`, Claude opens a PR from `feat/X` → `dev` and merges it
- You then merge `dev` → `main` when ready for production (manually, or with your CI/CD)

**You keep control of:**
- `main` → production deploys are yours to trigger
- Validation of enrichment plans before dev starts
- Acceptance testing before merge (`godeploy` tag)

---

## Context management (CLAUDE.md + memories)

Claude agents work best when project context is up to date. The convention in this kit:

### CLAUDE.md — project source of truth

Update it when:
- A new phase or major feature is completed
- A new dependency or API is added
- A critical pattern or constraint changes
- Key files are renamed or restructured

Do **not** put secrets, personal info, or team-specific configs here. It lives in the repo.

### Memory files — personal/session context

Stored in `~/.claude/projects/<project>/memory/` — local only, never committed.

Use `/save-session` at the end of each work session. It will:
1. Detect what changed in the conversation
2. Update `CLAUDE.md` if justified
3. Write or update memory files for context that should persist across sessions
4. Show you a summary of what was updated

Memory types:

| Type | What goes here |
|------|---------------|
| `project` | Decisions, objectives, phases, deadlines |
| `feedback` | How you want Claude to behave — corrections and validated approaches |
| `user` | Your role, preferences, technical level |
| `reference` | External systems (Linear, Notion, Grafana, Slack channels) |

### What developers should maintain

- **After each session**: run `/save-session`
- **After a major change**: review and update `CLAUDE.md`
- **When Claude behaves unexpectedly**: note it as a `feedback` memory

---

## Is Railway required?

**No.** Railway is one option for hosting preview URLs per branch — but it is not required by the kit.

The `/process-tickets` skill expects agents to post a **preview URL** after deployment. Where that URL comes from depends on your infrastructure:

| Platform | Preview per branch? | Notes |
|----------|--------------------|----|
| Railway | ✅ Yes | Auto-deploys per branch, custom domains |
| Render | ✅ Yes | Preview environments per PR |
| Fly.io | ⚠️ Manual | Possible but requires scripting |
| Vercel / Netlify | ✅ Yes | Native preview URLs per branch |
| None | ✅ Still works | Agent skips URL posting, still merges |

If you use Railway, the Railway MCP can be configured globally in `~/.claude/.mcp.json`:

```json
{
  "mcpServers": {
    "railway": {
      "command": "npx",
      "args": ["@railway/mcp"],
      "env": {
        "RAILWAY_API_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

> Tokens go in `~/.claude/.mcp.json` — **never in this repo or any project repo**.

---

## Requirements

- **Claude Code** (CLI)
- **GitHub CLI** (`gh`) — authenticated with `gh auth login`
- A GitHub repo with `main` and `dev` branches
- No specific deployment platform required

---

## Security

This repo contains **no secrets, no API keys, no project-specific configuration**.

All sensitive values go in:
- `~/.claude/.mcp.json` — MCP tokens (local, never committed)
- `~/.claude/projects/<project>/memory/` — personal context (local, never committed)
- `.env` files in each project (local, gitignored)

---

## License

MIT
