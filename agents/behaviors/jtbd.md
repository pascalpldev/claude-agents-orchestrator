---
name: jtbd
description: Jobs-to-be-Done — reformulate request as user job before evaluating scope or solution
pattern_author: Clayton Christensen, The Innovator's Solution (2003)
used_by: [product-builder, tech-lead]
---

# Jobs-to-be-Done (JTBD)

*Clayton Christensen, The Innovator's Solution (2003)*

Les utilisateurs n'ont pas besoin de fonctionnalités — ils ont un "job" à accomplir. Les features ne sont qu'un moyen d'y parvenir. Si le ticket prescrit une solution sans expliquer le problème, c'est un signal d'alarme.

## Questions

- Quel job l'utilisateur "hire" cette fonctionnalité pour accomplir ?
- Qu'est-ce qu'il fait aujourd'hui à la place, et pourquoi c'est insuffisant ?
- Comment "done" ressemble pour lui — quel est l'outcome émotionnel ?
- Quand cette situation se présente-t-elle concrètement dans son quotidien ?

## Format JTBD Statement

*"Quand [situation], je veux [motivation] pour [outcome attendu]."*

Exemple : *"Quand je reviens sur le tableau après 3 jours d'absence, je veux voir immédiatement ce qui a changé pour ne pas avoir à relire tout l'historique."*

## Protocole

1. Rédiger le JTBD statement en une phrase
2. Vérifier que la solution proposée dans le ticket accomplit ce job
3. Si non → challenger le scope ou poser une question de cadrage
4. Si oui → utiliser le statement pour élaguer les éléments qui n'y contribuent pas

## Output

```
JTBD : "Quand X, l'utilisateur veut Y pour Z."
Alignement avec le ticket : [oui / partiel / non — explication si partiel ou non]
```
