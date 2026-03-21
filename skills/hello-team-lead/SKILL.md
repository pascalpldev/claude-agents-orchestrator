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
allowed-tools: [Read, Glob, Grep, Bash]
---

# /hello-team-lead — Daily standup & context refresh

At the start of a session, call this to get full context of the project.

## What it does

1. **Detect current project** from `git remote get-url origin`
2. **Read project CLAUDE.md** for architecture context
3. **Fetch project state from GitHub:**
   - Open tickets by label (to-enrich, enriched, to-dev, to-test, deployed)
   - Recent comments and feedback
   - Current branch status

4. **Display summary:**
   ```
   === Project Status: <project-name> ===

   TO-ENRICH (waiting for enrichment):
   - #5: Feature X (2 hours ago)

   ENRICHED (waiting for validation):
   - #3: Feature Z (comments: "need clarification on...")

   TO-DEV (ready to implement):
   - #1: Feature A (validated, ready to code)

   TO-TEST (user is testing):
   - #2: Feature B (preview URL posted)

   DEPLOYED:
   - #7: Feature C (merged 2 hours ago)

   === Recent feedback ===
   #3: "Can you explain the database schema?"
   ```

5. **Position as team-lead:**
   - Ready to discuss any ticket
   - Ready to prioritize
   - Ready to help unblock agents

## Then what?

**Option A: Discuss a specific ticket**
```
/get-ticket #5
→ Discuss with team-lead here
```

**Option B: Launch automation**
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

This is your **daily ritual** to stay synchronized with the project.
