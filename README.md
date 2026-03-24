# Claude Agents Orchestrator

**Automated GitHub ticket management with Claude agents — from idea to deployment.**

Turn Claude Code into a full development team: the Chief Builder enriches feature specs with multi-persona deliberation, a Dev agent writes code, handles feedback, and merges validated work. You stay in control via GitHub labels and brief discussions.

---

## How it works

```
You create a ticket → label "to-enrich"
        ↓
Chief Builder deliberates (4 roles internally) → enrichment plan as comment
        ↓
You validate → change label to "to-dev"   (or auto-promoted if scope is simple)
        ↓
Dev agent creates branch, implements, opens PR
        ↓
You test → feedback or tag "godeploy"
        ↓
Dev agent merges to dev
```

---

## Quickstart (5 minutes)

```bash
# 1. Run setup (once per project)
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)

# 2. Create CLAUDE.md at the project root (see template below)

# 3. Create your first ticket
gh issue create --title "Feature: user authentication" --label "to-enrich"
```

Then in Claude Code:
```
/cao-process-tickets
```

The Chief Builder posts an enrichment plan as a GitHub comment. Review it, change the label to `to-dev`, then run `/cao-process-tickets` again — the Dev agent creates the branch, implements, and opens a PR.

---

## Installation

### Prerequisites

- **Claude Code** — `npm i -g @anthropic-ai/claude-code`
- **GitHub CLI** — `brew install gh` then `gh auth login`
- **Python 3** — pre-installed on macOS and most Linux distros
- **Git**

### Step 1 — Install the plugin (once, global)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)
```

Verify — in any Claude Code session, type `/cao-` and the skills should autocomplete.

### Step 2 — Create your project's CLAUDE.md

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
| Start of session | `/cao-hello-chief-builder` | Overview of open tickets and project state |
| Load a ticket | `/cao-get-ticket #5` | Discuss a specific ticket with the Chief Builder |
| Run automation | `/cao-process-tickets` | Enriches / implements / merges based on labels |
| Instant snapshot | `/cao-status` | Active tickets, running agents, recent logs |
| Full log history | `/cao-show-logs` | Timeline of what agents did (phases, durations, errors) |

---

## Skills reference

| Skill | Role |
|-------|------|
| `/cao-hello-chief-builder` | Morning standup — project status at a glance |
| `/cao-get-ticket #N` | Load a specific ticket and discuss it with Claude |
| `/cao-process-tickets` | Core automation — poll and process all tickets |
| `/cao-status` | Instant snapshot: active tickets, agents, last logs |
| `/cao-show-logs` | Full structured log history by ticket or agent |
| `/cao-watch` | Live monitoring of running agents |
| `/cao-kill` | Force graceful stop of a running agent |

---

## Ticket states (GitHub labels)

| Label | Meaning |
|-------|---------|
| `to-enrich` | Ready for enrichment (planning) |
| `enriching` | Chief Builder running — locked |
| `enriched` | Plan ready, waiting for your validation |
| `to-dev` | Validated, ready to implement |
| `dev-in-progress` | Dev agent running — locked |
| `to-test` | Code ready, PR open, ready to test |
| `deployed` | Merged to dev |
| `godeploy` | Signal: trigger merge to dev |
| `autonomous` | Skip human gate — Chief Builder goes all the way without stopping |

---

## The Chief Builder

The Chief Builder is not a single agent — it's four roles deliberating internally before producing a single output.

### Four roles

| Role | Responsibility |
|------|---------------|
| **Product Builder** | Challenges scope, applies YAGNI, surfaces the real problem behind the request |
| **Tech Lead** | Architecture decisions, failure modes, patterns, security, performance |
| **UX/UI Expert** | User flows, interaction states, friction reduction, discoverability |
| **Artistic Director** | Visual systems, brand coherence, distinctive design |

### Deliberation model

For each ticket, the Chief Builder runs up to **2 cycles of 3 waves**:

1. **Wave 1** — Primary persona (most relevant to the ticket) reads the ticket and forms an initial position
2. **Wave 2** — Other personas react to the primary's position (not the raw ticket) — each applies Challenge/Amplify
3. **Wave 3** — If a challenge changed the direction, re-deliberation on the revised position

If a challenge can't be resolved internally (requires information only you have), the agent posts a clarification comment and waits. A second cycle triggers only if the direction changed significantly in Cycle 1.

**The deliberation is visible in the output** — you see who challenged what, how it was resolved, and why.

### Intent detection

The Chief Builder detects your intent from the ticket text and adapts its behavior:

| Intent | Trigger | Output |
|--------|---------|--------|
| `feature` *(default)* | Standard request | Full implementation plan |
| `exploratory` | "propose", "ideas", "what do you think about" | 2–3 options with trade-offs |
| `risk-only` | "what is the risk", "risks of" | Risk table only, no plan |
| `bug` | "bug", "no longer works", "broken" | Root cause verification → fix plan or explanation |
| `directive` | "integrate X", "add Y" (clear imperative) | Direct plan, no scope challenge |
| `propose` | "propose solutions", "don't challenge" | Options without questioning the why |

### Clarification loop

When the Chief Builder can't commit to a direction without risking the wrong outcome, it posts a clarification comment — **with the scenarios it has considered and a default direction** — then resets the label to `to-enrich` and assigns the ticket to you.

It keeps clarifying until it can work in a single direction. Once confirmed, it produces the full plan.

### Auto-promote to `to-dev`

For tickets with a single clear direction, no breaking changes, and complexity S or M, the Chief Builder skips the `enriched` gate and promotes directly to `to-dev`. Use the `autonomous` label to bypass all human gates.

---

## Git workflow

```
main   ← production (stable)
dev    ← integration (validated features accumulate here)
  └─ feat/ticket-5-feature-name   ← created automatically per ticket
```

- Dev agent creates `feat/ticket-N-short-name` from `dev`
- On `godeploy`: Dev agent opens a PR `feat/X` → `dev` and merges it
- You merge `dev` → `main` when ready for production

---

## How to give feedback on a plan

After the Chief Builder posts an enrichment plan:

1. **If OK** → change label to `to-dev` (or it's already there if auto-promoted)
2. **If not OK** → add a comment with your feedback, change label back to `to-enrich`

The agent re-reads your feedback, re-deliberates with it as a new constraint, and updates the plan. It never rewrites a plan wholesale for a single challenged point — it addresses each point specifically.

---

## Agent logs

Agents write structured logs to `~/.claude/projects/logs/<project>/YYYY-MM-DD.jsonl`.

```
/cao-show-logs                   # today's runs, grouped by ticket
/cao-show-logs --ticket 5        # full history for ticket #5
/cao-show-logs --errors          # only error events
/cao-show-logs --last 10         # last 10 log entries
/cao-status                      # instant snapshot of current state
```

---

## Context management

### CLAUDE.md — project source of truth (in the repo)

Update it when a new phase completes, a dependency is added, a pattern changes, or a key file is renamed. Agents read it at every run — keep it accurate.

### Memory files — personal context (local only)

Stored in `~/.claude/projects/<project>/memory/` — never committed.

| Memory type | What goes here |
|-------------|---------------|
| `project` | Decisions, phases, deadlines |
| `feedback` | How Claude should/shouldn't behave |
| `user` | Your role, preferences, expertise |
| `reference` | External systems (Linear, Notion, Grafana) |

---

## Optional: Schedule automation

To run `/cao-process-tickets` automatically, ask Claude to create a scheduled task:

```
Create a cron job that runs /cao-process-tickets every minute
```

Claude Code will use its built-in scheduling system (`CronCreate`) to set this up.

---

## Optional: Preview URLs

The Dev agent posts a preview URL per branch when available.

| Platform | Preview per branch? |
|----------|---------------------|
| Railway | ✅ Auto-deploys per branch |
| Render | ✅ Preview environments per PR |
| Vercel / Netlify | ✅ Native preview URLs |
| Fly.io | ⚠️ Possible with scripting |
| None | ✅ Still works — agent skips the URL step |

---

## MCP configuration

Configure GitHub MCP (and optionally Railway MCP) in `~/.claude/.mcp.json` (local only, never committed):

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

---

## Troubleshooting

**Ticket stuck in `enriching` or `dev-in-progress`**
→ `/cao-show-logs --errors` to read the error
→ Manually reset label to previous state (`to-enrich` or `to-dev`)
→ Or run `/cao-kill <ticket-N>` to force graceful stop

**Agent doesn't see my feedback**
→ Change the label after commenting — the label change is the signal

**Chief Builder keeps asking clarification questions**
→ It detected ambiguity it can't resolve internally — answer the question or add the `autonomous` label to skip gates

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
