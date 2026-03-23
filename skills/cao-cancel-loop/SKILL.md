---
name: cao-cancel-loop
description: |
  Cancel an active cao-process-tickets loop.
  Deletes the CronCreate task(s) created by /cao-process-tickets --loop.
argument-hint: "[team-lead|dev|all]"
allowed-tools: [Bash]
---

# /cao-cancel-loop — Cancel an active loop

Stops the scheduled polling started by `/cao-process-tickets --loop`.

## What it does

Parse `$ARGUMENTS` to determine which cron to cancel:
- No argument or `all` → cancel all `cao-process-*` crons
- `team-lead` → cancel `cao-process-team-lead`
- `dev` → cancel `cao-process-dev`

Use `CronDelete` to remove the matching task(s), then confirm:

```
✅ Loop cancelled: cao-process-{ROLE}
   Run /cao-process-tickets [role] --loop to restart.
```

If no matching cron found:
```
ℹ️  No active cao loop found for role: {ROLE}
```
