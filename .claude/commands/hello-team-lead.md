---
name: hello-team-lead
description: |
  Morning standup — load the current project state and prepare for the day.

  Use /hello-team-lead at the start of your day to:
  - Check open tickets (to-enrich, to-dev, to-test)
  - See what's been deployed
  - Understand blockers or feedback
  - Be ready to discuss and make decisions

  This is the "team lead" perspective: full context of what's happening.
---

# /hello-team-lead — Daily standup & context refresh

At the start of a session, call this to get full context of the project:

```
/hello-team-lead
```

## What it does

1. **Fetches project state from GitHub:**
   - Open tickets by label (to-enrich, enriched, to-dev, to-test)
   - Recent comments and feedback
   - Deployments and current status

2. **Displays summary:**
   ```
   === InstaVid Project Status ===

   TO-ENRICH (waiting for enrichment):
   - #5: Feature X (2 hours ago)
   - #8: Feature Y (1 day ago)

   ENRICHED (waiting for user validation):
   - #3: Feature Z (comments: "need clarification on...")

   TO-DEV (ready to implement):
   - #1: Feature A (validated, ready to code)

   TO-TEST (user is testing):
   - #2: Feature B (URL: https://feat-2.railway.app)

   DEPLOYED:
   - #7: Feature C (merged 2 hours ago)

   === Recent feedback ===
   #3: "Can you explain the database schema?"
   #2: "Testing in production, looks good so far"
   ```

3. **Positions as team-lead:**
   - Ready to discuss any ticket
   - Ready to prioritize
   - Ready to help unblock agents

## Then what?

**Option A: Discuss a specific ticket**
```
/ticket #5
→ Discuss with team-lead here
```

**Option B: Launch automation** (runs once, polls all tickets)
```
/process-tickets
→ Enriches all to-enrich
→ Starts dev on all to-dev
→ Handles feedback on to-test
```

## Context it loads

- CLAUDE.md (project architecture)
- Git log (recent changes)
- All open GitHub issues + comments
- Labels and assignments
- Deployment status

This is your **daily ritual** to stay synchronized with the project.
