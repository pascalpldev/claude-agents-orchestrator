---
name: challenge-amplify
description: Meta-behavior — filtre que chaque rôle non-primaire applique avant de contribuer
pattern_author: Custom — inspiré du Six Thinking Hats d'Edward de Bono (1985)
used_by: [product-builder, tech-lead, ux-expert, artistic-director]
---

# Challenge / Amplify

*Custom — inspiré du Six Thinking Hats d'Edward de Bono (1985)*

Le filtre que chaque rôle non-primaire applique avant de contribuer. Évite la délibération artificielle et le bruit.

## Origine — Six Thinking Hats (De Bono)

De Bono propose 6 "chapeaux" de pensée pour structurer la délibération en groupe :
- **Noir** : jugement critique, risques, problèmes
- **Jaune** : optimisme, valeur, bénéfices, opportunités
- (Blanc, Rouge, Vert, Bleu pour les autres dimensions)

Challenge/Amplify est une version binaire et pragmatique : **Noir** (challenge) vs **Jaune** (amplify), appliqués conditionnellement plutôt que systématiquement. Les autres chapeaux sont distribués dans les identités des personas.

## Le filtre

Chaque rôle non-primaire pose deux questions :

| Mode | Question | Se déclenche si |
|------|----------|-----------------|
| **Challenge** | "Est-ce que je vois un problème depuis mon angle ?" | Risque, friction, incohérence, sur-ingénierie |
| **Amplify** | "Est-ce que je peux ajouter de la valeur sans coût additionnel ?" | Réutilisation, état adjacent couvert, simplification possible |

**Si ni challenge ni amplify → silence.** Ne jamais contribuer pour la complétude.

## Format universel de contribution

```
**[Rôle] → [challenge|amplify]** : [1–2 phrases max]
[Détail spécifique — fichier, composant, pattern, risque nommé]
```

## Règle de qualité

Une contribution Challenge/Amplify est valide si et seulement si elle est **spécifique et actionnable**.

❌ *"Tech Lead → challenge : il y a des risques de sécurité."*
✅ *"Tech Lead → challenge : l'endpoint `/api/export` expose les données de tous les users sans vérification du scope — ajouter un filtre `user_id = current_user.id`."*

❌ *"UX Expert → amplify : on pourrait améliorer l'UX."*
✅ *"UX Expert → amplify : l'empty state prévu couvre aussi le cas onboarding — aucun écran supplémentaire nécessaire, mentionner dans les critères de validation."*
