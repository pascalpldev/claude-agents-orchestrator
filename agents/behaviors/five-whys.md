---
name: five-whys
description: Root cause analysis — ask why 5 times before accepting a prescribed solution
pattern_author: Taiichi Ohno, Toyota Production System (1978)
used_by: [product-builder]
---

# 5 Whys

*Taiichi Ohno, Toyota Production System (1978)*

Demander "pourquoi" cinq fois pour passer du symptôme à la cause racine. Évite de construire des solutions au mauvais problème.

## Quand l'invoquer

- Le ticket prescrit une solution technique sans expliquer le problème utilisateur
- La demande semble être un workaround plutôt qu'une vraie solution
- Le scope semble disproportionné par rapport à ce qui est décrit

## Protocole

Partir de la demande telle qu'elle est formulée, puis :

1. Pourquoi a-t-on besoin de ça ?
2. Pourquoi [réponse 1] est-il un problème ?
3. Pourquoi [réponse 2] se produit-il ?
4. Pourquoi [réponse 3] n'est-il pas déjà résolu ?
5. Pourquoi [réponse 4] — c'est la cause racine.

S'arrêter avant 5 si la cause racine est identifiée clairement.

## Output

```
Cause racine : [description]
La solution proposée dans le ticket : [adresse / n'adresse pas / adresse partiellement] la cause racine
Recommandation : [procéder / reformuler le scope / poser une question de cadrage]
```
