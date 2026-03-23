# CAO Deployment Guide

**Deploy and scale the Claude Agents Orchestrator workflow across your team.**

This guide covers initial setup, phased rollout, monitoring, and rollback procedures for multi-agent deployments.

---

## Pre-Deployment Checklist

Before launching CAO in your project, verify all prerequisites:

### Infrastructure & Access

- [ ] GitHub repository created with `main` branch
- [ ] GitHub CLI (`gh`) installed and authenticated: `gh auth status`
- [ ] Git repository cloned locally: `git clone <repo>`
- [ ] GitHub Personal Access Token (PAT) with `repo` + `workflow` scopes
  - Generate: https://github.com/settings/tokens/new
  - Store securely: `export GITHUB_TOKEN=xxx` (or in `.env`)

### Claude Code Setup

- [ ] Claude Code installed: `npm list -g @anthropic-ai/claude-code`
- [ ] Plugin installed globally: `/plugins → search "claude-agents-orchestrator" → install`
- [ ] Verify plugin works: type `/cao-` in any session → should autocomplete skills
- [ ] Check `~/.claude/settings.json` has the marketplace config:
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

### Project Configuration

- [ ] All unit tests pass: `npm test` or `pytest tests/` (your stack)
- [ ] Pre-commit hooks installed and passing: `git commit --allow-empty -m "test"` should succeed
- [ ] `CLAUDE.md` created at project root with:
  - Project description and goals
  - Tech stack and architecture overview
  - Critical files and their purpose
  - Coding patterns and conventions
  - Deployment platform config (Railway, Render, Vercel, or none)
- [ ] `cao.config.yml` created with deployment target:
  ```yaml
  deploy:
    platform: railway    # or: render, vercel, none
    project: my-project
    service: web
  ```
- [ ] Branch protection rules on `main`:
  - Require PR reviews before merge
  - Require status checks to pass (CI/CD)
  - Dismiss stale PR approvals
- [ ] `dev` branch exists and is configured as integration branch

### Secrets & Credentials

- [ ] GitHub PAT available (PAT must have `repo` + `workflow` scopes)
- [ ] Deployment platform credentials configured (Railway, Render, etc.)
  - For **Railway**: `railway login` done locally (token in `~/.railway/config.json`)
  - For **Render**: API key available if needed
  - For **Vercel**: `vercel login` done locally
- [ ] `.env` and secrets excluded from git (check `.gitignore`)
- [ ] No hardcoded API keys, tokens, or passwords in code

---

## Phase 1: Initial Deployment (5–10 Agents)

Deploy CAO for your first small cohort and monitor for 1 week before scaling.

### Step 1 — Run Setup Script

In your project root:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)
```

This creates:
- GitHub labels (to-enrich, enriching, enriched, to-dev, dev-in-progress, to-test, deployed, godeploy)
- `dev` branch
- `.githooks/pre-commit` (validates commits)
- `cao.config.yml` (deployment platform config)

**Verify success:**
```bash
gh label list --repo <owner>/<repo>
git branch -a | grep dev
cat cao.config.yml
```

### Step 2 — Validate CLAUDE.md

Edit `CLAUDE.md` at your project root. At minimum, include:

```markdown
# Project Name

## Overview
[1–2 sentences on what this project does]

## Tech Stack
- Language: Python / Node.js / Go / Rust
- Framework: FastAPI / Express / Django / etc.
- Database: PostgreSQL / MongoDB / etc.
- Deployment: Railway / Render / Vercel / Docker

## Critical Files
- `src/main.py` — entry point
- `src/models/` — data models
- `src/api/` — REST endpoints
- `tests/` — test suite
- `requirements.txt` — Python dependencies

## Architecture
[Brief diagram or description of main components]

## Patterns & Conventions
- Use type hints (Python) / TypeScript (Node.js)
- Tests live alongside code: `src/foo.py` → `tests/test_foo.py`
- Pre-commit hook validates code before commit
- Git branches: feature branches off `dev`, merge via PR

## Deployment
- Platform: Railway (change if different)
- Service: `web` (change if different)
- Env vars: see Railway dashboard or `railway variables`
```

**Commit CLAUDE.md:**
```bash
git add CLAUDE.md cao.config.yml
git commit -m "chore: add CAO config and project documentation"
git push origin dev
```

### Step 3 — Create Your First Ticket

In your project, create a simple feature or bug fix to test the workflow:

```bash
gh issue create \
  --title "Feature: Add user authentication" \
  --body "Implement JWT-based login and session management for API endpoints." \
  --label "to-enrich"
```

**Verify:** The ticket appears in GitHub with `to-enrich` label and no assignee.

### Step 4 — Test Enrichment Phase

In Claude Code, run:

```
/cao-process-tickets team-lead
```

**Expected behavior:**
1. Detects ticket with `to-enrich` label
2. Changes label to `enriching` (lock)
3. Launches team-lead agent (Sonnet model)
4. Agent reads ticket, writes enrichment plan as comment
5. Changes label to `enriched`
6. Skill completes: `✅ Processed: #N`

**If it fails:**
- Check GitHub token is set: `echo $GITHUB_TOKEN` (should not be empty)
- Read agent logs: `/cao-show-logs --errors`
- Check CLAUDE.md syntax and critical files exist

### Step 5 — Validate Enrichment & Move to Dev

On GitHub, review the enrichment plan comment:
- Is it clear and actionable?
- Does it match your vision?
- Are there gaps or issues?

**If OK:** Change label from `enriched` → `to-dev`

**If not OK:** Add a comment with feedback and change label back to `to-enrich`. Agent will re-read feedback and revise.

### Step 6 — Test Dev Phase

In Claude Code, run:

```
/cao-process-tickets dev
```

**Expected behavior:**
1. Detects ticket with `to-dev` label
2. Changes label to `dev-in-progress` (lock)
3. Launches dev agent (Sonnet model for this phase)
4. Agent creates feature branch: `feat/ticket-N-...`
5. Agent implements code, commits, pushes
6. Agent creates PR: `Closes #N` with preview URL comment
7. Changes label to `to-test`

**If it fails:**
- Check git credentials: `git remote -v`
- Review agent logs: `/cao-show-logs --ticket <N>`
- Look for git push errors

### Step 7 — Test & Tag for Deploy

On GitHub:
1. Review the PR opened by the dev agent
2. Click the preview URL in the PR comment
3. Test the feature manually
4. If it works: **On the original ticket**, add the `godeploy` label

**If bugs found:**
1. Add a comment with feedback on the ticket
2. Change label back to `to-dev`
3. Agent re-launches, reads feedback, fixes, and re-opens PR

### Step 8 — Merge & Deploy

In Claude Code, run:

```
/cao-process-tickets dev
```

**Expected behavior:**
1. Detects `godeploy` label on `to-test` ticket
2. Finds the associated PR
3. Verifies PR is mergeable (all checks pass)
4. Merges PR into `dev` branch
5. Changes label to `deployed`

**Verify on GitHub:**
- PR is merged
- Commit is visible in `dev` branch history
- GitHub Actions (if configured) runs deployment tests

### Step 9 — Monitor for 1 Week

After the first successful workflow:

1. **Create 5–10 more tickets** with real features/bugs
2. **Run the workflow daily** or enable loop mode:
   ```
   /cao-process-tickets --loop --interval 5
   ```
   This polls every 5 minutes and processes ready tickets automatically.

3. **Monitor in Claude Code:**
   - Check logs daily: `/cao-show-logs --errors`
   - Review agent performance: `/cao-show-logs --last 20`
   - Note any patterns in errors or slowdowns

4. **Track metrics:**
   - Time from enrichment to deployment (target: 1–2 hours)
   - Success rate (% of tickets completed without errors)
   - Most common failure modes

---

## Phase 2: Monitoring & Observability

Once Phase 1 completes successfully, set up structured monitoring to detect issues early.

### Log Aggregation

Logs are stored locally at `~/.claude/projects/logs/<project-slug>/` as JSONL files (one per agent run).

**View today's logs:**
```bash
/cao-show-logs
```

**View logs for a specific ticket:**
```bash
/cao-show-logs --ticket 5
```

**View only errors:**
```bash
/cao-show-logs --errors
```

**View last 20 runs:**
```bash
/cao-show-logs --last 20
```

### Log Entry Format

Each run produces a JSONL file with entries like:

```json
{
  "timestamp": "2026-03-23T14:30:15Z",
  "run_id": "20260323_143015_tl_5",
  "ticket": 5,
  "agent": "team-lead",
  "phase": "start",
  "status": "started",
  "message": "ticket #5 — Feature: User auth"
}
```

**Key fields:**
- `timestamp` — ISO 8601 time
- `run_id` — unique identifier for each agent run
- `ticket` — GitHub issue number
- `agent` — "team-lead" or "dev"
- `phase` — lifecycle phase (start, context_loaded, analysis_complete, push, pr_created, end, etc.)
- `status` — "started", "ok", "error", "success"
- `message` — human-readable detail or error message

### Dashboards & Alerts

For production deployments, export logs to a centralized system:

**Option 1: Local Dashboard (Simple)**
```bash
# Count successful runs this week
/cao-show-logs --last 100 | grep '"status":"success"' | wc -l

# Count errors this week
/cao-show-logs --errors | wc -l

# Average time per run
/cao-show-logs --last 20
# → Look at "end" rows and sum durations
```

**Option 2: Remote Logging (Advanced)**
Stream logs to a service (e.g., ELK, Datadog, Loki):

1. Add a post-run hook in agent code to send logs to your backend:
   ```bash
   # Agent writes to local JSONL, then:
   curl -X POST https://logs.myservice.com/api/logs \
     -H "Authorization: Bearer $LOG_TOKEN" \
     -d @~/.claude/projects/logs/<project>/run.jsonl
   ```

2. Set up alerting:
   - Alert on error rate > 10% in 1 hour
   - Alert on average run duration > 5 minutes
   - Alert on "ghost detection" times > 30 minutes

### Health Checks

Run a quick health check before scaling:

```bash
# Verify workflow state machine
gh issue list --repo <owner>/<repo> --state open --json number,labels \
  | python3 -c "
    import sys, json
    issues = json.load(sys.stdin)
    enriching = sum(1 for i in issues if any(l['name'] == 'enriching' for l in i['labels']))
    dev_in_progress = sum(1 for i in issues if any(l['name'] == 'dev_in_progress' for l in i['labels']))
    print(f'Enriching: {enriching} | Dev in progress: {dev_in_progress}')
    if enriching > 5 or dev_in_progress > 5:
      print('⚠️  WARNING: Too many locked tickets. Check for stuck agents.')
  "
```

---

## Phase 3: Scale to 10–20 Agents

Once monitoring is stable, scale to larger concurrent workloads.

### Enable Loop Mode with Longer Intervals

Instead of manual runs, set up continuous polling:

```bash
# Every 10 minutes, process all workflows
/cao-process-tickets --loop --interval 10

# Or, role-specific:
/cao-process-tickets team-lead --loop --interval 10
/cao-process-tickets dev --loop --interval 10
```

This is ideal for 24/7 automation with Railway crons or scheduled Claude sessions.

### Parallel Agents

CAO is designed for safe parallel execution:
- **Enrichment agents** (team-lead) work on different `to-enrich` tickets concurrently
- **Dev agents** (dev) work on different `to-dev` tickets concurrently
- **Locked states** (`enriching`, `dev-in-progress`) prevent race conditions

**Safe to run in parallel:**
```bash
# In one window:
/cao-process-tickets team-lead --loop --interval 5

# In another window (same or different session):
/cao-process-tickets dev --loop --interval 5
```

Both can run safely — they operate on different state sets.

### Rate Limiting & Throttling

If you exceed GitHub API rate limits (5000 requests/hour):

1. **Check current limit:**
   ```bash
   gh api rate_limit
   ```

2. **Reduce polling frequency:**
   ```bash
   /cao-process-tickets --loop --interval 30  # Check every 30 min instead of 5
   ```

3. **Configure GitHub CLI caching:**
   ```bash
   gh config set http_unix_socket ""  # Ensure fresh API calls
   ```

### Model Scaling

By default, Phase 1 uses **Sonnet** for both enrichment and dev. For cost optimization at scale:

Edit `cao.config.yml`:
```yaml
agents:
  enrichment_model: sonnet    # or: opus, haiku (see CAO docs)
  dev_model: haiku            # cheaper for implementation
```

Or override in `/cao-process-tickets` skill before launching agents.

**Cost comparison (rough, as of 2026):**
- **Opus**: $15 / 1M input, $60 / 1M output (best quality, expensive)
- **Sonnet**: $3 / 1M input, $15 / 1M output (recommended default)
- **Haiku**: $0.80 / 1M input, $4 / 1M output (fast, cost-effective for coding)

Typical workflow costs:
- Enrichment (team-lead): 20–50 KB output → ~$0.30–0.75 per ticket
- Development (dev): 50–200 KB output → ~$0.75–3.00 per ticket

---

## Rollback Procedure

If issues arise (bugs in agent logic, GitHub API problems, or stuck state), follow this procedure:

### Scenario 1: Agent Errors (Enrichment or Dev)

**Symptoms:**
- Agent crashes with an error message
- Label stays in `enriching` or `dev-in-progress` state
- Ticket is locked and won't progress

**Fix:**
```bash
# 1. Read the error in the logs
/cao-show-logs --errors

# 2. If error is transient (API timeout, etc.), reset and retry:
gh issue edit <number> \
  --remove-label enriching --add-label to-enrich
  # OR
  # --remove-label dev-in-progress --add-label to-dev

# 3. Run the workflow again:
/cao-process-tickets

# 4. If error persists, check CLAUDE.md and agent code for the root cause
```

### Scenario 2: Stuck in Dev Phase (PR Won't Merge)

**Symptoms:**
- PR created but CI checks fail
- Label is `to-test` but you can't merge

**Fix:**
```bash
# 1. Review the PR and CI errors on GitHub
gh pr view <pr_number>

# 2. Reset the ticket:
gh issue edit <number> --remove-label to-test --add-label to-dev

# 3. Add a comment on the ticket with feedback:
gh issue comment <number> -b "CI checks failing. Fix: [specific guidance]"

# 4. Run dev workflow again:
/cao-process-tickets dev
```

### Scenario 3: Deployment Failures

**Symptoms:**
- PR merged but deployment to Railway/Render/Vercel fails
- App crashes in production

**Fix:**
```bash
# 1. Check deployment logs on your platform
railway logs --service web    # Railway
# or
render-cli logs --service web  # Render

# 2. Roll back the deployment:
railway rollback               # Railway
# or manually revert commit:
git revert <commit-sha>
git push origin dev

# 3. Reset the ticket:
gh issue edit <number> \
  --remove-label deployed \
  --add-label to-test

# 4. Add comment with bug details and re-run dev
gh issue comment <number> -b "Deployment failed: [error]. Please fix: [details]"
/cao-process-tickets dev
```

### Scenario 4: Mass Lockup (Multiple Stuck Tickets)

**Symptoms:**
- Many tickets stuck in `enriching` or `dev-in-progress`
- No agents seem to be processing them

**Emergency reset:**
```bash
# 1. Stop any running loops (kill Claude sessions or run /cancel-cao)

# 2. Reset ALL enriching tickets back to to-enrich:
gh issue list --repo <owner>/<repo> --state open --label enriching \
  --json number --jq '.[] | .number' | while read n; do
  gh issue edit "$n" --remove-label enriching --add-label to-enrich
done

# 3. Reset ALL dev-in-progress back to to-dev:
gh issue list --repo <owner>/<repo> --state open --label dev-in-progress \
  --json number --jq '.[] | .number' | while read n; do
  gh issue edit "$n" --remove-label dev-in-progress --add-label to-dev
done

# 4. Clean up orphaned branches (feature branches with no PR):
git fetch origin
git branch -r | grep feat/ | while read branch; do
  if ! gh pr list --repo <owner>/<repo> --head "${branch#origin/}" --json number | grep -q number; then
    git push origin --delete "${branch#origin/}"
  fi
done

# 5. Check logs to find the root issue:
/cao-show-logs --errors --last 50

# 6. Once fixed, restart workflows:
/cao-process-tickets
```

### Scenario 5: Clear All Logs (Start Fresh)

If logs are corrupted or you want a clean slate:

```bash
# Find log directory
LOG_DIR="${HOME}/.claude/projects/logs/$(git remote get-url origin | sed 's|^.*github\.com[:/]||' | sed 's|\.git$||' | sed 's|/|-|g')"

# Backup (just in case)
cp -r "$LOG_DIR" "${LOG_DIR}.backup-$(date +%s)"

# Clear
rm -rf "${LOG_DIR}"

# Logs will be recreated on next agent run
```

---

## Rollback to a Previous Version

If the CAO plugin has a bug and breaks your workflow:

```bash
# 1. Check which plugin version is installed:
cd ~/.claude/plugins
ls -la claude-agents-orchestrator/

# 2. Go back to a known-good commit:
cd ~/.claude/plugins/claude-agents-orchestrator
git log --oneline | head -20
git checkout <commit-sha>

# 3. Or reinstall the plugin from a specific release:
# Edit ~/.claude/settings.json and pin the version:
{
  "extraKnownMarketplaces": {
    "claude-agents-orchestrator": {
      "source": {
        "source": "github",
        "repo": "pascalpldev/claude-agents-orchestrator",
        "ref": "v1.0.0"
      }
    }
  }
}

# 4. Re-run /cao-process-tickets to verify
```

---

## Success Criteria

Your deployment is successful when:

### Functional Criteria

- [ ] All pre-deployment checks pass (tests, hooks, CLAUDE.md valid)
- [ ] First ticket completes the full workflow: enrich → dev → test → merge
- [ ] Agent enrichment plans are clear and actionable
- [ ] Dev agent code changes are tested and working
- [ ] Merges to `dev` are clean (no conflicts)
- [ ] GitHub Actions (if configured) passes all checks

### Performance Criteria

- [ ] Enrichment time: < 2 minutes per ticket
- [ ] Development time: < 5 minutes per simple ticket, < 15 minutes for complex ones
- [ ] Merge time: < 1 minute
- [ ] Overall cycle time: < 30 minutes from "to-enrich" to "deployed"

### Reliability Criteria

- [ ] Success rate: ≥ 95% of tickets complete without manual intervention
- [ ] Error rate: < 5% of runs (occasional transient GitHub API timeouts OK)
- [ ] No race conditions: no two agents processing the same ticket
- [ ] Ghost detection: locked tickets (`enriching`, `dev-in-progress`) revert within 30 minutes if agent crashes
- [ ] API limits: no GitHub rate limit exhaustion (stay < 80% of 5000/hour quota)

### Operational Criteria

- [ ] Logs are readable and complete (check `/cao-show-logs`)
- [ ] Runbooks exist and are followed (this document)
- [ ] On-call team knows how to access logs and rollback
- [ ] Alerts are set up for errors and slow runs

---

## Monitoring Commands Reference

Keep these commands handy for day-to-day operations:

### View & Debug

```bash
# Today's logs
/cao-show-logs

# Errors only
/cao-show-logs --errors

# Specific ticket history
/cao-show-logs --ticket 5

# Last 20 agent runs
/cao-show-logs --last 20

# Team-lead agent only
/cao-show-logs --agent team-lead
```

### GitHub State

```bash
# List all tickets by label
gh issue list --repo <owner>/<repo> --label to-enrich
gh issue list --repo <owner>/<repo> --label enriched
gh issue list --repo <owner>/<repo> --label to-dev
gh issue list --repo <owner>/<repo> --label dev-in-progress
gh issue list --repo <owner>/<repo> --label to-test
gh issue list --repo <owner>/<repo> --label deployed

# View a ticket with full context
gh issue view 5 --repo <owner>/<repo>

# List all PRs opened by agents
gh pr list --repo <owner>/<repo> --state all --author app/claude
```

### Git Status

```bash
# List all agent-created branches
git branch -a | grep feat/

# View recent commits on dev
git log dev --oneline --graph -10

# Check for orphaned branches (feature branches with no PR)
git fetch origin
git branch -r | grep feat/
```

### Workflow Control

```bash
# Start the automation (one-time run)
/cao-process-tickets

# Start looping: check every 5 minutes
/cao-process-tickets --loop

# Stop looping
/cancel-cao

# Enrich only (one-time)
/cao-process-tickets team-lead

# Dev only (one-time)
/cao-process-tickets dev

# Dev with longer interval
/cao-process-tickets dev --loop --interval 30
```

---

## Troubleshooting Matrix

| Issue | Cause | Fix |
|-------|-------|-----|
| "No logs found" | First run, or project not configured | Run `/cao-process-tickets` once to generate logs |
| Ticket stuck in `enriching` | Agent crashed or timed out | Reset label: `gh issue edit --remove-label enriching --add-label to-enrich` |
| Ticket stuck in `dev-in-progress` | PR merge failed or agent error | Check PR status; reset label and add feedback comment |
| PR won't merge (CI failing) | Code doesn't pass tests | Add comment with fix guidance; reset to `to-dev` |
| High error rate (> 10%) | API issues or bad CLAUDE.md | Check `/cao-show-logs --errors`; review CLAUDE.md syntax |
| Slow enrichment (> 5 min) | Context files too large | Trim CLAUDE.md or move non-critical files outside of it |
| API rate limit hit | Too many concurrent agents | Increase `--interval` or reduce number of parallel runs |
| GitHub token expired | Auth failure | Update `GITHUB_TOKEN` environment variable or `gh auth login` |

---

## Next Steps

Once Phase 3 is stable:

1. **Automate fully**: Deploy CAO as a scheduled Railway/Fly.io cron job
2. **Monitor continuously**: Set up alerts in your observability platform (Datadog, NewRelic, etc.)
3. **Iterate on prompts**: Fine-tune team-lead and dev agent instructions based on feedback
4. **Expand scope**: Use CAO for maintenance tasks, dependency updates, and security patches

---

## FAQ

**Q: Can I run multiple CAO instances in parallel?**
A: Yes, safely. Different agents can run on different state labels (enriching, dev-in-progress, godeploy). Locked states prevent collisions.

**Q: What if my deployment platform (Railway, Render, Vercel) doesn't support automated deploys?**
A: Set `platform: none` in `cao.config.yml`. Agents will merge to `dev` but skip platform-specific deployment steps.

**Q: Can I change models or adjust agent behavior?**
A: Yes. Edit `cao.config.yml` to specify models; edit agent prompt files (`agents/team-lead.md`, `agents/dev.md`) to tweak behavior.

**Q: How do I scale beyond 20 agents?**
A: Use Railway/Fly.io scheduled tasks to spawn multiple parallel `/cao-process-tickets` runs in different Claude Code sessions. Monitor API quotas closely.

**Q: What if a ticket requires human review?**
A: Add a comment on the ticket and keep it in the current state. Human reviewer changes the label and runs `/cao-process-tickets` to resume.

---

**Last Updated:** 2026-03-23
**CAO Version:** 1.0+
**Maintained by:** Claude Agents Orchestrator Team
