---
name: cao-watch
description: |
  Vue temps réel des agents en cours — se rafraîchit automatiquement sans changer d'interface.
  Affiche : agents actifs (ticket, durée, phase, dernier milestone), tickets en attente, activité récente.

  Usage :
  - /cao-watch              → refresh toutes les 30s
  - /cao-watch --interval 10 → refresh toutes les 10s
argument-hint: "[--interval <secondes>]"
allowed-tools: [Bash]
---

# /cao-watch — Vue temps réel

Lance le watcher en continu dans le terminal courant. Se réécrit en place (pas de scroll).

## Parse arguments

```
INTERVAL = 30  # default

For each token in $ARGUMENTS:
  "--interval <n>" → INTERVAL = n
```

## Lancement

```bash
_REPO_ROOT="$(git rev-parse --show-toplevel)"

python3 "${_REPO_ROOT}/lib/status_watcher.py" --interval {INTERVAL}
```

Le script tourne jusqu'à Ctrl+C. Il affiche et rafraîchit en place :

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CAO Watch — owner/repo  ⟳ 30s  Ctrl+C pour quitter
 Dernière màj : 14:32:05
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 AGENTS ACTIFS
────────────────────────────────────────────────────
  #42   proud-falcon         12min   Fabrication — Tests        milestone #3
  #17   swift-eagle           3min   Enrichissement             milestone #1

 EN ATTENTE
────────────────────────────────────────────────────
  ⏳ to-dev              #38    Fix: Auth timeout
  ⏳ to-enrich           #41    Feature: Dark mode

 ACTIVITÉ RÉCENTE
────────────────────────────────────────────────────
  14:31:42  dev           #42    milestone           Fabrication — Tests  milestone #3
  14:28:10  chief-builder #17    start               ticket #17 — Feature…
  14:25:00  dev           #42    implement_complete  implementation done

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 Prochaine màj dans 30s…
```

## Notes

- Agents actifs = lus depuis `.locks/*.lock` (local)
- Tickets = lus depuis GitHub via `gh issue list` (réseau)
- Logs = lus depuis `~/.claude/projects/logs/<repo>/<date>.jsonl`
- Un agent marqué `⚠ GHOST?` n'a pas mis à jour son heartbeat depuis > 20min
- Pour arrêter : Ctrl+C dans le terminal, ou fermer l'onglet Claude Code
