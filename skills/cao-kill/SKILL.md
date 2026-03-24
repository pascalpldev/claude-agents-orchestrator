---
name: cao-kill
description: |
  Arrêt propre d'un agent en cours sur un ticket spécifique.
  L'agent détecte le signal à sa prochaine milestone et remet le ticket en état initial.

  Usage :
  - /cao-kill #42     → arrêt propre de l'agent travaillant sur le ticket #42
  - /cao-kill --all   → arrêt propre de tous les agents actifs
argument-hint: "<#N | --all>"
allowed-tools: [Bash]
---

# /cao-kill — Arrêt propre d'un agent

Dépose un fichier sentinel que l'agent détecte à sa prochaine checkpoint (au plus dans 5 min).
L'agent nettoie lui-même : remet le label, poste un commentaire, supprime son lock.

## Parse arguments

```
TICKET = ""
ALL    = false

For each token in $ARGUMENTS:
  "--all"     → ALL = true
  "#<N>" / "<N>" → TICKET = N (strip "#")
```

Si ni TICKET ni ALL fourni → afficher l'aide et les agents actifs.

## Context

```bash
REPO_ROOT=$(git rev-parse --show-toplevel)
LOCKS_DIR="${REPO_ROOT}/.locks"
```

## Exécution

### Kill d'un ticket spécifique

```bash
SENTINEL="${LOCKS_DIR}/kill-ticket-${TICKET}"

if [ ! -f "${LOCKS_DIR}/ticket-${TICKET}.lock" ]; then
  echo "⚠  Aucun agent actif sur le ticket #${TICKET} (.lock absent)"
  echo "   Utilisez /cao-status pour voir les agents en cours."
  exit 0
fi

touch "$SENTINEL"
echo "✅ Signal de kill déposé pour le ticket #${TICKET}"
echo "   L'agent s'arrêtera proprement à sa prochaine checkpoint (≤ 5min)."
echo "   Surveiller avec : /cao-watch"
```

### Kill de tous les agents (--all)

```bash
LOCKS=$(ls "${LOCKS_DIR}"/ticket-*.lock 2>/dev/null)

if [ -z "$LOCKS" ]; then
  echo "Aucun agent actif."
  exit 0
fi

COUNT=0
for LOCK in $LOCKS; do
  TICKET_N=$(basename "$LOCK" .lock | sed 's/ticket-//')
  touch "${LOCKS_DIR}/kill-ticket-${TICKET_N}"
  echo "  Signal déposé → ticket #${TICKET_N}"
  COUNT=$((COUNT + 1))
done

echo ""
echo "✅ ${COUNT} signal(s) de kill déposé(s)."
echo "   Les agents s'arrêteront à leur prochaine checkpoint (≤ 5min)."
```

## Notes

- Le kill est **coopératif** : l'agent exécute son propre cleanup avant de s'arrêter
  - Remet le ticket en `to-dev` (ou `to-enrich` selon l'agent)
  - Poste un commentaire GitHub
  - Supprime son `.lock` file
- Si l'agent est ghost (heartbeat > 20min), le sentinel ne sera jamais lu —
  utiliser `/cao-status` pour identifier les ghosts et réinitialiser manuellement les labels
- Délai maximum avant arrêt : 5 minutes (intervalle entre deux `_milestone_if_due`)
