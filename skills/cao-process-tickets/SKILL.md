---
name: cao-process-tickets
description: |
  Poll GitHub tickets and process them through the enrichment and dev workflows.

  Accepts an optional role filter and loop mode:
  - /cao-process-tickets                    → process all workflows, once
  - /cao-process-tickets chief-builder      → enrichment only (to-enrich → enriched)
  - /cao-process-tickets dev                → dev + merge only (to-dev → to-test, godeploy → deployed)
  - /cao-process-tickets --loop             → process all, then schedule every 5 minutes
  - /cao-process-tickets dev --loop         → dev only, looping every 5 minutes
  - /cao-process-tickets --ghost-buster     → clean up dead agents first, then process
argument-hint: "[chief-builder|dev|all] [--loop] [--interval <minutes>] [--ghost-buster]"
allowed-tools: [Read, Glob, Grep, Bash, Agent]
---

# /cao-process-tickets — Poll and process GitHub tickets

Core automation workflow. Detects tickets in various states and launches the appropriate agent.

## Parse arguments

Parse `$ARGUMENTS` before doing anything:

```
ROLE         = "all"    # default
LOOP         = false
INTERVAL     = 5        # minutes, default
GHOST_BUSTER = false

For each token in $ARGUMENTS:
  "chief-builder"    → ROLE = "chief-builder"
  "dev"              → ROLE = "dev"
  "all"              → ROLE = "all"
  "--loop"           → LOOP = true
  "--interval <n>"   → INTERVAL = n
  "--ghost-buster"   → GHOST_BUSTER = true
```

If `--loop` is set: announce it at the start.
```
🔄 Loop mode active — role: {ROLE}, interval: {INTERVAL}min
```

## Phase 0 — Ghost buster (si --ghost-buster)

Si GHOST_BUSTER = true, exécuter **avant tout traitement de ticket** :

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
python3 "${REPO_ROOT}/lib/ghost_buster.py" \
  --repo "$OWNER/$REPO" \
  --locks-dir "${REPO_ROOT}/.locks"
```

Traite tous les ghosts détectés (local + remote) séquentiellement, affiche un résumé,
puis continue vers le traitement normal des tickets.

Si aucun ghost trouvé → affiche `👻 Ghost buster — aucun ghost détecté.` et continue.

## Context detection

Before processing:
1. Run `git remote get-url origin` to extract OWNER and REPO
2. Read the project's `CLAUDE.md` for architecture context
3. Fetch open issues: `gh issue list --repo $OWNER/$REPO --state open --json number,title,labels,assignees`

## Workflows to execute

Run only the workflows matching ROLE:

| ROLE | Workflows to run |
|------|-----------------|
| `all` | 1 + 2 + 3 |
| `chief-builder` | 1 only |
| `dev` | 2 + 3 |

### 1. Enrichment workflow (chief-builder)

Skip if ROLE = "dev".

**Detects**: `to-enrich` label + no assignee

```
a. Lock: gh issue edit N --add-label "enriching" --remove-label "to-enrich"
b. Launch chief-builder agent:
   - Reads ticket via gh issue view
   - Writes enrichment plan
   - Posts as comment via gh issue comment
   - Changes label enriching → enriched
```

**If challenged**: `to-enrich` + feedback comment
```
a. chief-builder agent re-reads comments
b. Responds to feedback
c. Changes label to-enrich → enriched
```

### 2. Dev workflow (dev)

Skip if ROLE = "chief-builder".

**Detects**: `to-dev` label + no assignee

```
a. Lock: gh issue edit N --add-label "dev-in-progress" --remove-label "to-dev"
b. Launch dev agent:
   - Reads full ticket + plan
   - Creates branch, implements, pushes
   - Creates PR via gh pr create
   - Changes label dev-in-progress → to-test
```

**If feedback**: `to-dev` + feedback comment
```
a. dev agent detects change + feedback
b. Fixes, commits, changes label → to-test
```

### 3. Merge workflow (dev)

Skip if ROLE = "chief-builder".

**Detects**: `godeploy` label on `to-test` ticket

```
a. Lock: gh issue edit N --add-label "dev-in-progress" --remove-label "to-test"
b. Launch dev agent (godeploy mode):
   - Finds PR via gh pr list
   - Verifies mergeable via gh pr view
   - Merges via gh pr merge
   - Changes label → deployed
```

## After processing

### Summary

Always output a brief summary:
```
✅ Processed: [list of tickets handled, or "nothing to process"]
⏭️  Skipped (locked): [tickets in enriching/dev-in-progress, if any]
```

### Loop scheduling — drain then sleep

If LOOP = true, appliquer la logique **drain then sleep** :

```
ANY_PROCESSED = (au moins un ticket a été traité dans ce run)

Si ANY_PROCESSED = true :
  → Re-lancer immédiatement sans délai
  → CronCreate(
      taskId: "cao-process-{ROLE}",
      cronExpression: "* * * * *",     ← toutes les minutes (immédiat au sens cron)
      prompt: "/cao-process-tickets {ROLE} --loop --interval {INTERVAL}"
    )
  → Output: "🔁 Ticket traité — re-poll immédiat"

Si ANY_PROCESSED = false (file vide) :
  → Dormir INTERVAL minutes
  → CronCreate(
      taskId: "cao-process-{ROLE}",
      cronExpression: "*/{INTERVAL} * * * *",
      prompt: "/cao-process-tickets {ROLE} --loop --interval {INTERVAL}"
    )
  → Output: "💤 File vide — prochain poll dans {INTERVAL}min"
```

**Principe** : l'agent vide la file tant qu'il y a du travail, puis dort seulement quand il ne trouve rien. Zéro poll inutile entre deux tickets consécutifs.

After CronCreate:
- Si succès, log :
  ```
  RUN_ID = current timestamp in format YYYYMMDD_HHMMSS_loop
  Run: python3 lib/logger.py "{RUN_ID}" "worker" "null" "worker_start" "ok" "loop scheduled" '{"role":"{ROLE}","interval":{INTERVAL},"any_processed":{ANY_PROCESSED}}'
  ```
- Si échec, log :
  ```
  Run: python3 lib/logger.py "{RUN_ID}" "worker" "null" "schedule_error" "error" "CronCreate failed" '{"role":"{ROLE}"}'
  ```

Then output:
```
⏱️  Next run: [immédiat | dans {INTERVAL}min] (cron: cao-process-{ROLE})
   Stop with: /cancel-cao or ask Claude to delete cron "cao-process-{ROLE}"
```

## Example sessions

**One-shot, all roles:**
```
/cao-process-tickets
→ Enriches #5, implements #3, merges #1
→ Done.
```

**Loop — plusieurs tickets en attente (drain) :**
```
/cao-process-tickets --loop
→ 🔄 Loop mode — role: all, interval: 5min

run 1 : traite #5 (to-enrich) → ✅ Processed: #5 → 🔁 re-poll immédiat
run 2 : traite #3 (to-dev)    → ✅ Processed: #3 → 🔁 re-poll immédiat
run 3 : traite #1 (godeploy)  → ✅ Processed: #1 → 🔁 re-poll immédiat
run 4 : rien                  → 💤 file vide → ⏱️ prochain poll dans 5min
```

**Loop — file vide au démarrage :**
```
/cao-process-tickets --loop
→ 🔄 Loop mode — role: all, interval: 5min
→ Nothing to process
→ 💤 file vide — ⏱️ prochain poll dans 5min
```

**Loop — intervalle personnalisé :**
```
/cao-process-tickets dev --loop --interval 10
→ 🔄 Loop mode — role: dev, interval: 10min
→ Nothing to process
→ 💤 file vide — ⏱️ prochain poll dans 10min
```

## Implementation notes

- Each run is atomic (one ticket processed per state)
- Locked states (enriching, dev-in-progress) prevent collisions between roles running in parallel
- GitHub operations use `gh` CLI; GitHub MCP for `search_code` and CI `actions_*`
- Git operations (checkout, commit, push) remain bash
- OWNER/REPO auto-detected from git remote
