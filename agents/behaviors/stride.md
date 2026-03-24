---
name: stride
description: Security threat modeling — six threat categories, apply only relevant dimensions
pattern_author: Loren Kohnfelder & Praerit Garg, Microsoft (1999)
used_by: [tech-lead, ux-expert]
---

# STRIDE Threat Model

*Loren Kohnfelder & Praerit Garg, Microsoft (1999)*

Six security threat categories. Evaluate only the dimensions relevant to the ticket — do not force all 6.

## Dimensions

| Letter | Threat | Key question |
|--------|--------|--------------|
| **S** | Spoofing | Can someone impersonate a user/system? |
| **T** | Tampering | Can data be altered in transit or at rest? |
| **R** | Repudiation | Can actions be denied / left untraced? |
| **I** | Information disclosure | Is sensitive data exposed? |
| **D** | Denial of Service | Can the service be made unavailable? |
| **E** | Elevation of Privilege | Can a user gain unauthorized rights? |

## Protocol

1. Identify the relevant dimensions for this ticket (often 1–3 out of 6)
2. For each active dimension: is there a concrete attack vector?
3. If yes → mitigation required, integrate into "Risks & impacts" section of the plan

## Output

```
STRIDE applicable: [relevant dimensions, e.g.: I, E]
Identified vectors: [specific list or "(none)"]
Required mitigations: [list or "(none)"]
```
