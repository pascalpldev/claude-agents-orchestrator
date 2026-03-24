---
name: cao-status
description: |
  Snapshot instantané de l'état du projet — tickets actifs, agents en cours, derniers logs.

  Usage :
  - /cao-status            → vue complète
  - /cao-status --tickets  → tickets GitHub uniquement (labels)
  - /cao-status --agents   → agents actifs (.lock files) uniquement
  - /cao-status --logs     → derniers événements de log
argument-hint: "[--tickets|--agents|--logs]"
allowed-tools: [Read, Glob, Grep, Bash]
---

# /cao-status — Snapshot d'état

Donne une vue instantanée de ce qui se passe : tickets en cours, agents actifs, dernières activités.

## Parse arguments

```
MODE = "all"
For each token in $ARGUMENTS:
  "--tickets" → MODE = "tickets"
  "--agents"  → MODE = "agents"
  "--logs"    → MODE = "logs"
```

## Context

```bash
REMOTE=$(git remote get-url origin 2>/dev/null)
OWNER=$(echo "$REMOTE" | sed 's|.*github\.com[:/]||' | cut -d'/' -f1)
REPO=$(echo "$REMOTE" | sed 's|.*github\.com[:/]||' | cut -d'/' -f2 | sed 's|\.git$||')
REPO_ROOT=$(git rev-parse --show-toplevel)
```

## Section 1 — Tickets actifs (si MODE = all | tickets)

Récupérer tous les tickets ouverts avec un label de workflow actif :

```bash
gh issue list --repo "$OWNER/$REPO" --state open \
  --json number,title,labels,assignees,updatedAt \
  --limit 50
```

Filtrer et afficher par état :

```
## Tickets en cours

| # | Titre | État | Assigné | Mis à jour |
|---|-------|------|---------|------------|
| #N | ... | enriching | — | il y a 3min |
| #N | ... | dev-in-progress | @user | il y a 12min |

## En attente

| # | Titre | État |
|---|-------|------|
| #N | ... | to-enrich |
| #N | ... | to-dev |
| #N | ... | to-test |

## Récemment terminés (deployed)
[3 derniers tickets deployed, avec date]
```

Tickets sans label de workflow → ignorer.

## Section 2 — Agents actifs (si MODE = all | agents)

Lire les `.lock` files dans `.locks/` :

```bash
ls "$REPO_ROOT/.locks/"*.lock 2>/dev/null || echo "(aucun agent actif)"
```

Pour chaque `.lock` file trouvé, afficher :

```bash
python3 - <<'EOF'
import json, time, glob, os
from datetime import datetime
from pathlib import Path

locks_dir = Path(os.environ.get('REPO_ROOT', '.')) / '.locks'
now = time.time()

locks = list(locks_dir.glob('*.lock')) if locks_dir.exists() else []
if not locks:
    print("Aucun agent actif (.locks/ vide ou absent)")
else:
    print(f"{'Ticket':<10} {'Agent':<20} {'Depuis':<12} {'Phase':<25} {'Milestones':<10} {'État'}")
    print("-" * 90)
    for lock_file in sorted(locks):
        try:
            d = json.loads(lock_file.read_text())
            elapsed = int(now - d['claimed_at'])
            hb_age = int(now - d['last_heartbeat'])
            mins = elapsed // 60
            phase = d.get('current_phase', '—')
            milestones = d.get('milestone_count', 0)
            # Ghost if heartbeat > 20min
            state = '⚠️  GHOST?' if hb_age > 1200 else '✅ actif'
            ticket = lock_file.stem.replace('ticket-', '#')
            agent = d.get('agent', '?')[:18]
            print(f"{ticket:<10} {agent:<20} {mins:>3}min{'':<7} {phase:<25} {milestones:<10} {state}")
        except Exception as e:
            print(f"{lock_file.name}: erreur lecture ({e})")
EOF
```

## Section 3 — Derniers logs (si MODE = all | logs)

```bash
LOG_DIR="$HOME/.claude/projects/logs/${OWNER}-${REPO}"
LOG_FILE=$(ls "$LOG_DIR"/*.jsonl 2>/dev/null | sort | tail -1)

if [ -z "$LOG_FILE" ]; then
  echo "Aucun log trouvé dans $LOG_DIR"
else
  # Derniers 20 événements, formatés
  python3 - <<'PYEOF'
import json, sys
from pathlib import Path

log_file = Path(sys.argv[1])
lines = log_file.read_text().strip().split('\n')[-20:]

print(f"{'Heure':<10} {'Agent':<14} {'Ticket':<8} {'Phase':<22} {'Status':<8} Message")
print("-" * 85)
for line in lines:
    try:
        e = json.loads(line)
        ts = e['ts'][11:19]  # HH:MM:SS
        agent = (e.get('agent') or '?')[:12]
        ticket = f"#{e['ticket']}" if e.get('ticket') else '—'
        phase = (e.get('phase') or '?')[:20]
        status = e.get('status', '?')[:7]
        msg = e.get('msg', '')[:40]
        icon = '✅' if status in ('ok','success','started') else '❌'
        print(f"{ts:<10} {agent:<14} {ticket:<8} {phase:<22} {icon} {status:<6} {msg}")
    except Exception:
        pass
PYEOF
  "$LOG_FILE"
fi
```

## Output final

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CAO Status — {OWNER}/{REPO}
 {DATE} {TIME}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Section 1 — Tickets]

[Section 2 — Agents actifs]

[Section 3 — Derniers logs]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Si toutes les sections sont vides : afficher `✅ Rien en cours — projet au repos.`
