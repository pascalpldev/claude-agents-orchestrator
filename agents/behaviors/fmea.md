---
name: fmea
description: Failure Mode and Effects Analysis — structured risk table for production-critical paths only
pattern_author: U.S. Military, MIL-P-1629 (1949) — adapté pour le logiciel
used_by: [tech-lead]
---

# FMEA — Failure Mode and Effects Analysis

*U.S. Military, MIL-P-1629 (1949) — adapté pour le logiciel*

Pour chaque chemin critique : qu'est-ce qui échoue, quelle probabilité, quel impact, quelle détection/mitigation.

## Quand l'invoquer

Uniquement si le ticket touche un chemin critique : paiement, authentification, données utilisateur, intégration externe, migration de données, job background critique.

Ne pas appliquer sur des tickets CRUD standards ou des changements UI sans impact données.

## Format

| Composant | Mode d'échec | Probabilité | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| ... | ... | L/M/H | L/M/H | ... |

## Protocole

1. Lister les composants critiques touchés par le ticket
2. Pour chacun : identifier le(s) mode(s) d'échec plausibles
3. Évaluer probabilité × impact (ne documenter que M×M et au-dessus)
4. Proposer une mitigation pour chaque risque retenu
5. Si rollback nécessaire : le préciser explicitement

Ne pas créer une table exhaustive — seulement les risques non-triviaux et actionnables.

## Output

Table FMEA (format ci-dessus) + stratégie de rollback si applicable.
