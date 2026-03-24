---
name: progressive-disclosure
description: Show only what's needed now — advanced options appear when needed, don't front-load complexity
pattern_author: Jakob Nielsen, Nielsen Norman Group (1994)
used_by: [ux-expert]
---

# Progressive Disclosure

*Jakob Nielsen, Nielsen Norman Group (1994)*

Only display what is necessary for the current step. Advanced options appear when they are needed. Do not front-load complexity.

## When to invoke it

- Forms with > 4 fields
- Interfaces with "advanced" or rarely used options
- Multi-step flows where all information is presented upfront
- Configuration settings with basic / advanced levels

## Questions

- How many fields/options are needed at the moment of the first interaction?
- Which elements can appear only after a user action?
- Is there a "simple" version and an "advanced" version of this flow?
- Is the current complexity justified by the frequency of use?

## Protocol

1. Identify elements visible on load
2. For each one: is it necessary for the primary first action?
3. Those that are not → candidates for progressive disclosure
4. Propose the "level 1" version (primary action) and "level 2" version (advanced options)

## Output

```
Level 1 (visible immediately): [list of elements]
Level 2 (on demand / context): [list of elements]
Recommended simplification: [description]
```
