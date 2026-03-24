---
name: cognitive-load
description: Working memory is limited — reduce user decisions and mental effort by default
pattern_author: John Sweller (1988)
used_by: [ux-expert, artistic-director]
---

# Cognitive Load Theory

*John Sweller (1988)*

Working memory is limited. Every additional element, decision, or step costs the user mental effort. **Reduce by default.**

## Guiding questions

- What decisions is the user required to make? Can they be eliminated or deferred?
- What information is displayed that the user does not need at that precise moment?
- Can the default path require zero active decisions?
- Are there technical terms or jargon that force the user to think?

## Protocol

1. List all explicit decisions required from the user in the flow
2. For each one: can it be eliminated (smart default), deferred (progressive disclosure), or automated?
3. List interface elements that are present but not needed at the moment they appear

## Output

```
Eliminable decisions: [list or "(none)"]
Elements to defer: [list or "(none)"]
Recommendation: [1 sentence on the primary simplification]
```
