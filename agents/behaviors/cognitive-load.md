---
name: cognitive-load
description: Working memory is limited — reduce user decisions and mental effort by default
pattern_author: John Sweller (1988)
used_by: [ux-expert, artistic-director]
---

# Cognitive Load Theory

*John Sweller (1988)*

La mémoire de travail est limitée. Chaque élément, décision ou étape supplémentaire coûte un effort mental à l'utilisateur. **Réduire par défaut.**

## Questions directrices

- Quelles décisions l'utilisateur est-il obligé de prendre ? Peuvent-elles être éliminées ou différées ?
- Quelle information est affichée dont l'utilisateur n'a pas besoin à ce moment précis ?
- Le chemin par défaut peut-il nécessiter zéro décision active ?
- Y a-t-il des termes techniques ou du jargon qui forcent l'utilisateur à réfléchir ?

## Protocole

1. Lister toutes les décisions explicites demandées à l'utilisateur dans le flow
2. Pour chacune : peut-elle être éliminée (default intelligent), différée (progressive disclosure), ou automatisée ?
3. Lister les éléments d'interface présents mais non nécessaires au moment où ils apparaissent

## Output

```
Décisions éliminables : [liste ou "(aucune)"]
Éléments à différer : [liste ou "(aucun)"]
Recommandation : [1 phrase sur la simplification principale]
```
