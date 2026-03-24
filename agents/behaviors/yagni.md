---
name: yagni
description: You Ain't Gonna Need It — scope reduction, identify speculative features to cut or defer
pattern_author: Kent Beck, Extreme Programming Explained (1999)
used_by: [product-builder, tech-lead]
---

# YAGNI — You Ain't Gonna Need It

*Kent Beck, Extreme Programming Explained (1999)*

Ne construis pas ce qui n'est pas explicitement nécessaire maintenant. Chaque fonctionnalité spéculative est une dette de maintenance future et une décision irréversible déguisée en flexibilité.

## Questions

- Si on shippait la version la plus simple possible, qu'est-ce qui manquerait concrètement à l'utilisateur ?
- Qu'est-ce qui est construit "au cas où" et pourrait être différé ou supprimé ?
- Quelle est la version MVP qui valide l'hypothèse centrale ?
- Combien de lignes de code disparaissent si on retire cette partie ?

## Protocole

1. Identifier les éléments "just in case" dans le scope
2. Pour chacun : si on le retirait, quel est l'impact utilisateur immédiat ?
3. Lister les candidats au report (ticket de suivi, sans coût maintenant)
4. Proposer la version YAGNI avec delta de scope explicite

## Output

```
Version YAGNI : [description en 1 phrase]
Delta retiré : [ce qui est coupé et pourquoi]
Candidats au report : [liste ou "(aucun)"]
```
