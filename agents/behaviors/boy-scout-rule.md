---
name: boy-scout-rule
description: Leave code cleaner than found — flag adjacent technical debt addressable in the same PR
pattern_author: Robert C. Martin, Clean Code (2008)
used_by: [tech-lead]
---

# Boy Scout Rule

*Robert C. Martin, Clean Code (2008)*

"Leave the code cleaner than you found it." When touching a file, flag adjacent technical debt that deserves to be addressed in the same PR.

## Strict constraints

- Only if it is within the natural scope of the change (same file or module)
- Only if it does not create additional risk
- Only if the effort is proportionate (< 20% of the estimated primary scope)

This behavior is **always in Amplify mode** — never in Challenge.

## Protocol

1. For each file touched by the ticket: is there obvious technical debt?
2. If yes: is it within the natural scope? Is the effort < 20% of the ticket?
3. If yes → flag as an amplification under "Role contributions"
4. If no → silence (do not create scope creep)

## Output

```
Boy Scout → amplify: [file] — [description of the debt] addressable in this PR.
Estimated effort: [XS / S]. Additional risk: none.
```
