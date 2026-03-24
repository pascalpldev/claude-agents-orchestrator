---
name: progressive-disclosure
description: Show only what's needed now — advanced options appear when needed, don't front-load complexity
pattern_author: Jakob Nielsen, Nielsen Norman Group (1994)
used_by: [ux-expert]
---

# Progressive Disclosure

*Jakob Nielsen, Nielsen Norman Group (1994)*

N'afficher que ce qui est nécessaire pour l'étape courante. Les options avancées apparaissent quand elles sont nécessaires. Ne pas front-loader la complexité.

## Quand l'invoquer

- Formulaires avec > 4 champs
- Interfaces avec des options "avancées" ou rarement utilisées
- Flows multi-étapes où toute l'information est présentée dès le début
- Paramètres de configuration avec niveaux basic / avancé

## Questions

- Combien de champs/options sont nécessaires au moment de la première interaction ?
- Quels éléments peuvent apparaître seulement après une action de l'utilisateur ?
- Y a-t-il une version "simple" et une version "avancée" de ce flow ?
- La complexité actuelle est-elle justifiée par la fréquence d'utilisation ?

## Protocole

1. Identifier les éléments visibles dès le chargement
2. Pour chacun : est-il nécessaire à la première action principale ?
3. Ceux qui ne le sont pas → candidats à la disclosure progressive
4. Proposer la version "niveau 1" (action principale) et "niveau 2" (options avancées)

## Output

```
Niveau 1 (visible d'emblée) : [liste d'éléments]
Niveau 2 (sur demande / contexte) : [liste d'éléments]
Simplification recommandée : [description]
```
