# /cao-worker — Multi-Agent Automated Ticket Development

Start a persistent worker that runs multiple concurrent agents to process GitHub tickets in parallel.

## Overview

`/cao-worker` is the production-grade automation skill for processing tickets automatically. It uses the `WorkerOrchestrator` class to coordinate:

1. **Polling** - Detect tickets with "to-dev" label (ready for implementation)
2. **Claiming** - Atomic assignment to prevent race conditions
3. **Working** - Run implementation with heartbeat-based lifecycle
4. **Integration** - Create PR, update labels, notify on GitHub

## Quick Start

### Start worker with default settings (5 agents, 5-minute polling):

```bash
/cao-worker
```

### Start with custom agent count:

```bash
/cao-worker --agents 10
```

### Start with custom polling interval (must be >= 300 seconds):

```bash
/cao-worker --agents 5 --interval 300
```

## Configuration

### Command-line Arguments

```
--agents <N>
  Number of concurrent worker agents (default: 5, max: 20)
  - 5-10: Good for testing and low-medium load
  - 10-20: Production scale (requires API caching)

--interval <seconds>
  Polling interval in seconds (default: 300 = 5 minutes)
  - Minimum: 300 seconds (to respect GitHub API rate limits)
  - With 20 agents: ~240 API calls/hour (safe)

--ghost-timeout <seconds>
  Timeout for detecting "ghost" agents (default: 1200 = 20 minutes)
  - If an agent's lock isn't updated within this time, claim is released
  - Prevents tickets from being stuck indefinitely
```

### Environment Variables

Set in your project's CLAUDE.md or environment:

```yaml
worker:
  polling_interval_seconds: 300    # Must be >= 300
  max_agents: 10                   # Safe for most projects
  ghost_timeout_seconds: 1200      # 20 minutes
```

## How It Works

### The Workflow

Each agent cycle:

1. **Poll** - Query for all issues with "to-dev" label and no assignee
2. **Claim** - Attempt to assign the first available ticket to self
   - If successful, add "dev-in-progress" and "agent/{name}" labels
   - If fails (race), try next ticket
3. **Notify** - Post a comment on the ticket indicating work started
4. **Work** - Run the implementation with heartbeat monitoring
   - Worker creates a lock file with heartbeat timestamps
   - If heartbeat isn't updated within `ghost_timeout`, claim is released
5. **PR** - Create pull request from feature branch to dev
   - Push working branch
   - Create PR via gh CLI
   - Post PR URL as comment
6. **Cleanup** - Remove "dev-in-progress" label, add "to-test", unassign

### Atomic Claiming

Claims are atomic to prevent race conditions:

- Multiple agents poll simultaneously
- First to assign ticket to self wins
- Others detect the assignee and move to next ticket
- Ghost detection prevents stuck claims

### Rate Limiting

With GitHub's 5000 requests/hour limit:

```
20 agents × 5-min interval = 240 API calls/hour
Safe margin maintained for other operations
```

## API Reference

### WorkerOrchestrator Class

```python
from lib.worker_main import WorkerOrchestrator

# Create orchestrator
orchestrator = WorkerOrchestrator(
    agent_name="swift-eagle",        # Or None to auto-generate
    repo="owner/repo",               # Or None to detect from git
    polling_interval=300,            # Seconds (minimum 300)
    project_root=Path.cwd()         # Project root for migrations
)

# Run one cycle
result = orchestrator.run_one_cycle()
# Returns: {
#     "status": "completed" | "no_tickets" | "no_claims" | "error",
#     "ticket": <int>,  # If claimed
#     "error": <str>    # If status == "error"
# }
```

### Methods

#### `poll_for_tickets() -> List[int]`

Query GitHub for all open "to-dev" tickets with no assignee.

Returns list of issue numbers.

#### `try_claim_and_work(ticket_id: int) -> bool`

Atomic claim and work cycle:
1. Assign to self
2. Add labels
3. Create working branch
4. Run work cycle
5. Create PR
6. Cleanup

Returns True if successful, False if claim failed.

#### `_assign_to_self(ticket_id: int) -> bool`

Assign ticket to current user (atomic claim).

Returns True if assignment succeeded.

#### `_create_working_branch(ticket_id: int) -> str`

Create a feature branch (format: `feature/ticket-{id}-{agent-name}`).

#### `_implement_feature(ticket_id: int, branch_name: str) -> None`

Placeholder for feature implementation. Override in subclass for custom logic.

#### `_create_pull_request(ticket_id: int, branch_name: str) -> str`

Push branch and create PR to dev branch.

Returns PR URL.

#### `cleanup_labels_after_pr(repo: str, ticket_id: int, agent_name: str)`

Remove "dev-in-progress" and "agent/{name}" labels, add "to-test".

## Integration with Other Components

### Worker (Heartbeat Lifecycle)

WorkerOrchestrator uses the `Worker` class for heartbeat management during long-running work.

```python
self.worker.run_work_cycle(
    ticket_id=123,
    work_func=self._implement_feature
)
```

### GitHub Notifier (API Operations)

Uses github_notifier for resilient GitHub operations with retry:

```python
add_labels_with_retry(repo, issue_number, ["label1", "label2"])
remove_labels_with_retry(repo, issue_number, ["label1"])
post_comment(repo, issue_number, "body text")
cleanup_labels_after_pr(repo, issue_number, agent_name)
```

### Schema Validator (Resume Safety)

The Worker validates database schema before resuming work to prevent unsafe state.

### Agent Namer (Unique Identification)

Auto-generates memorable agent names (e.g., "proud-falcon"):

```python
from lib.agent_namer import generate_agent_name
name = generate_agent_name()  # Returns random "adjective-animal"
```

## Monitoring & Debugging

### View Worker Logs

```bash
/cao-show-logs --filter "worker" --lines 100
```

### Check for Stuck Tickets

```bash
gh issue list --repo owner/repo --label "dev-in-progress" --state open
gh issue list --repo owner/repo --label "claimed-by-*" --state open
```

### Manually Release a Stuck Ticket

```bash
gh issue edit 123 --repo owner/repo \
  --remove-label "dev-in-progress" \
  --remove-label "agent/agent-name"
```

## Troubleshooting

### "Worker finds tickets but never claims"

- Check if all tickets are already assigned
- Verify "to-dev" label exists
- Check if current user can be assigned

**Solution:**
```bash
gh issue list --repo owner/repo --label to-dev --assignee none
```

### "Ghost claims not being released"

- Check `ghost_timeout_seconds` configuration
- Verify lock files are being updated

**Solution:**
```bash
ls -la .locks/
```

### "API rate limit exhausted"

- Reduce polling frequency (increase `--interval`)
- Reduce number of agents (decrease `--agents`)

### Worker never processes second ticket

- First ticket may still be in progress
- Check if "to-test" label was added correctly
- Verify PR was created

## Performance Tuning

### For Low Load (< 5 tickets/hour)

```bash
/cao-worker --agents 3 --interval 600
```

### For Medium Load (5-20 tickets/hour)

```bash
/cao-worker --agents 5 --interval 300
```

### For High Load (> 20 tickets/hour)

```bash
/cao-worker --agents 15 --interval 300
```

## Architecture

```
WorkerOrchestrator (main orchestrator)
  ├── Worker (heartbeat lifecycle)
  ├── GitHubNotifier (API operations)
  ├── SchemaValidator (resume safety)
  └── AgentNamer (unique names)
```

### Lifecycle per Ticket

```
1. Poll for "to-dev" tickets
   ↓
2. Claim via assignment (atomic)
   ↓
3. Create working branch
   ↓
4. Notify claim on GitHub
   ↓
5. Run work cycle with heartbeat
   ↓
6. Create PR
   ↓
7. Cleanup labels + add "to-test"
```

## Best Practices

1. **Start Small** - Begin with 3-5 agents, scale up after monitoring
2. **Monitor Actively** - Check logs and stuck tickets regularly
3. **Set Appropriate Interval** - Don't go below 5 minutes (300 seconds)
4. **Handle Failures** - Implement proper error handling in work_func
5. **Test Locally** - Test with `/cao-process-tickets --loop` before `/cao-worker`

## See Also

- `/cao-process-tickets` — Single-agent looping (simpler, good for testing)
- `/cao-show-logs` — View worker logs
- `/cao-cancel-loop` — Stop the worker
- CLAUDE.md — Project configuration

## Implementation Details

The WorkerOrchestrator integrates:

- **worker.py** - Heartbeat-based claim lifecycle
- **github_notifier.py** - Resilient GitHub operations with retry
- **schema_validator.py** - Database schema validation for resume safety
- **agent_namer.py** - Unique agent name generation
- **heartbeat.py** - Ghost claim detection

Full source: `lib/worker_main.py`

Test coverage: `tests/test_worker_integration.py`
