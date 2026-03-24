---
name: four-states-ui
description: Every UI component needs all four states — empty, loading, error, ideal
pattern_author: Scott Hurff, Designing Products People Love (2015)
used_by: [ux-expert, artistic-director]
---

# The Four States of UI

*Scott Hurff, Designing Products People Love (2015)*

Tout composant UI doit être conçu pour les 4 états. Les états **empty** et **error** sont systématiquement sous-designés et causent le plus de frustration utilisateur.

## Les 4 états

| État | Description | Questions |
|------|-------------|-----------|
| **Empty** | Pas de données (premier usage, filtre à zéro, tout supprimé) | Qu'est-ce que l'utilisateur voit ? Y a-t-il un CTA ou une guidance ? |
| **Loading** | Données en cours de chargement | Spinner, skeleton, ou UI optimiste ? Délai perçu acceptable ? |
| **Error** | Quelque chose a échoué (réseau, validation, permission) | Message actionnable ? L'utilisateur peut-il réessayer ? Sait-il pourquoi ? |
| **Ideal** | L'état normal, peuplé | Souvent le seul état designé — insuffisant seul. |

## Checklist

Pour chaque composant interactif dans le scope :

- [ ] Empty state défini ?
- [ ] Loading state défini ?
- [ ] Error state défini (message actionnable) ?
- [ ] Success/confirmation défini si action destructive ou asynchrone ?
- [ ] Edge cases : strings très longues, zéro éléments, max éléments, réseau lent ?

## Output

Liste des états manquants par composant + recommandation. Si tous les états sont couverts → silence.
