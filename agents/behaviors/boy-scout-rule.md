---
name: boy-scout-rule
description: Leave code cleaner than found — flag adjacent technical debt addressable in the same PR
pattern_author: Robert C. Martin, Clean Code (2008)
used_by: [tech-lead]
---

# Boy Scout Rule

*Robert C. Martin, Clean Code (2008)*

"Laisse le code plus propre que tu ne l'as trouvé." Quand on touche un fichier, signaler la dette technique adjacente qui mérite d'être adressée dans le même PR.

## Contraintes strictes

- Seulement si c'est dans le scope naturel du changement (même fichier ou module)
- Seulement si ça ne crée pas de risque additionnel
- Seulement si l'effort est proportionné (< 20% du scope principal estimé)

Ce behavior est **toujours en mode Amplify** — jamais en Challenge.

## Protocole

1. Pour chaque fichier touché par le ticket : y a-t-il de la dette technique évidente ?
2. Si oui : est-ce dans le scope naturel ? L'effort est-il < 20% du ticket ?
3. Si oui → signaler comme amplification dans "Apports des rôles"
4. Si non → silence (ne pas créer de scope creep)

## Output

```
Boy Scout → amplify : [fichier] — [description de la dette] adressable dans ce PR.
Effort estimé : [XS / S]. Risque additionnel : aucun.
```
