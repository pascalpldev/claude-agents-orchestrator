---
name: cao-worker
description: |
  Start the multi-agent worker loop for automated ticket development.

  Launches up to 20 concurrent agents polling GitHub tickets every 5 minutes.
  Suitable for production-grade automation with high throughput.

argument-hint: "[--agents <N>] [--interval <seconds>] [--ghost-timeout <seconds>]"
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# /cao-worker — Multi-agent polling loop

Starts a persistent worker that runs multiple concurrent agents to process tickets in parallel.

## Configuration

### Polling Interval (Required)

**Minimum polling interval: 5 minutes (300 seconds)**

**Rationale:**
- 20 agents × 5-min interval = 240 label queries/hr
- Well within GitHub's 5000 req/hr rate limit
- Balances latency (max 5 min wait for claim) vs API usage

**Comparison with `/cao-process-tickets`:**
- `/cao-process-tickets --loop` — single agent, looping every 5 min (good for light load, simple setup)
- `/cao-worker` — up to 20 agents in parallel, coordinated via GitHub labels (good for production, high throughput)

### Command-line Arguments

```
--agents <N>
  Number of concurrent worker agents (default: 5, max: 20)
  Start with 5-10 for testing; scale to 20 after monitoring

--interval <seconds>
  Polling interval in seconds (default: 300 = 5 minutes)
  Must be >= 300. Lower values risk GitHub API exhaustion.

--ghost-timeout <seconds>
  Timeout for detecting "ghost" agents (default: 1200 = 20 minutes)
  If an agent doesn't update its lock within this time, claim is released.
```

### Environment Configuration

Set in CLAUDE.md or environment:

```yaml
worker:
  polling_interval_seconds: 300  # 5 minutes (required minimum)
  max_agents: 20                 # safe up to 20 with API caching
  ghost_timeout_seconds: 1200    # 20 minutes
```

**Do not set below 5 minutes.** Lower values risk:
- GitHub API rate limit exhaustion
- Redundant label queries
- Race conditions between agents

### CLAUDE.md Template Section

Add to your project's CLAUDE.md:

```markdown
## Multi-Agent Worker Configuration

**Polling Interval:** 5 minutes (required minimum)
**Max Concurrent Agents:** 10 (safe), 20 (requires API caching)
**Ghost Claim Timeout:** 20 minutes

When using `/cao-worker`:
- Ensure polling_interval ≥ 300 seconds
- Start with 5-10 agents; scale to 20 after monitoring
- Monitor agent logs in `~/.claude/projects/<project>/logs/`
```

## How It Works

### Startup logging

After parsing arguments (`--agents`, `--interval`, `--ghost-timeout`), log the worker startup event:

```
RUN_ID = current timestamp in format YYYYMMDD_HHMMSS_worker
Run: python3 lib/logger.py "{RUN_ID}" "worker" "null" "worker_start" "ok" "worker started" '{"nb_agents":{N},"interval":{INTERVAL}}'
```

### Agent Coordination via Labels

Each worker agent:
1. Queries for tickets with `to-enrich` or `to-dev` labels (no assignee)
2. Claims a ticket by adding a "claimed-by-{worker-id}" label + assignee
3. Processes the ticket (enrichment or dev)
4. Releases the label, changes ticket state

### Ghost Detection

If an agent crashes or hangs:
- Its lock label persists (`claimed-by-{worker-id}`)
- After `ghost_timeout_seconds`, another agent can reclaim
- Prevents tickets from being permanently stuck

### Rate Limiting Strategy

```
Max API calls per hour: 5000 (GitHub limit)
Agents: 20
Per-ticket label queries: ~2 (list + edit)
Per-minute throughput: 20 agents × 12 queries/hr ÷ 60 = 4 queries/min
Total per hour: 240 queries/hr (safe margin)
```

## Usage

### Start 10 agents, 5-minute polling:
```bash
/cao-worker --agents 10
```

### Start 20 agents, custom interval:
```bash
/cao-worker --agents 20 --interval 300
```

### Start with custom ghost timeout:
```bash
/cao-worker --agents 5 --interval 300 --ghost-timeout 900
```

## Monitoring

View worker logs:
```bash
/cao-show-logs --filter "worker" --lines 50
```

Check for stuck tickets:
```bash
gh issue list --repo $OWNER/$REPO --label "claimed-by-*" --state open
```

## Stopping the Worker

To stop the worker loop, update your cron job:
```bash
/cancel-cao
```

Or manually stop via Claude Code interface.

## Implementation Notes

- Each agent runs the standard enrichment/dev workflows
- No additional locking beyond what `/cao-process-tickets` provides
- Suitable for production automation with high ticket throughput
- Requires CLAUDE.md in project root with polling_interval_seconds ≥ 300
