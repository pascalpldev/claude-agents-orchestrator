---
name: stride
description: Security threat modeling — six threat categories, apply only relevant dimensions
pattern_author: Loren Kohnfelder & Praerit Garg, Microsoft (1999)
used_by: [tech-lead, ux-expert]
---

# STRIDE Threat Model

*Loren Kohnfelder & Praerit Garg, Microsoft (1999)*

Six catégories de menaces sécurité. N'évaluer que les dimensions pertinentes au ticket — ne pas forcer les 6.

## Dimensions

| Lettre | Menace | Question clé |
|--------|--------|--------------|
| **S** | Spoofing | Quelqu'un peut-il usurper l'identité d'un user/système ? |
| **T** | Tampering | Les données peuvent-elles être altérées en transit ou au repos ? |
| **R** | Repudiation | Les actions peuvent-elles être niées / non traçables ? |
| **I** | Information disclosure | Des données sensibles sont-elles exposées ? |
| **D** | Denial of Service | Le service peut-il être rendu indisponible ? |
| **E** | Elevation of Privilege | Un user peut-il obtenir des droits non autorisés ? |

## Protocole

1. Identifier les dimensions pertinentes pour ce ticket (souvent 1–3 sur 6)
2. Pour chaque dimension active : existe-t-il un vecteur d'attaque concret ?
3. Si oui → mitigation requise, intégrer dans "Risques & impacts" du plan

## Output

```
STRIDE applicable : [dimensions pertinentes, ex: I, E]
Vecteurs identifiés : [liste spécifique ou "(aucun)"]
Mitigations requises : [liste ou "(aucune)"]
```
