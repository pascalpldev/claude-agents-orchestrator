---
name: yagni
description: You Ain't Gonna Need It — scope reduction, identify speculative features to cut or defer
pattern_author: Kent Beck, Extreme Programming Explained (1999)
used_by: [product-builder, tech-lead]
---

# YAGNI — You Ain't Gonna Need It

*Kent Beck, Extreme Programming Explained (1999)*

Do not build what is not explicitly needed right now. Every speculative feature is future maintenance debt and an irreversible decision disguised as flexibility.

## Questions

- If we shipped the simplest possible version, what would the user concretely be missing?
- What is being built "just in case" and could be deferred or removed?
- What is the MVP version that validates the core hypothesis?
- How many lines of code disappear if we remove this part?

## Protocol

1. Identify "just in case" elements in the scope
2. For each one: if removed, what is the immediate user impact?
3. List deferral candidates (follow-up ticket, no cost now)
4. Propose the YAGNI version with an explicit scope delta

## Output

```
YAGNI version: [description in 1 sentence]
Removed delta: [what is cut and why]
Deferral candidates: [list or "(none)"]
```
