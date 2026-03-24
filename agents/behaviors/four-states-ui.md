---
name: four-states-ui
description: Every UI component needs all four states — empty, loading, error, ideal
pattern_author: Scott Hurff, Designing Products People Love (2015)
used_by: [ux-expert, artistic-director]
---

# The Four States of UI

*Scott Hurff, Designing Products People Love (2015)*

Every UI component must be designed for all 4 states. The **empty** and **error** states are systematically under-designed and cause the most user frustration.

## The 4 states

| State | Description | Questions |
|-------|-------------|-----------|
| **Empty** | No data (first use, filter at zero, everything deleted) | What does the user see? Is there a CTA or guidance? |
| **Loading** | Data is being fetched | Spinner, skeleton, or optimistic UI? Acceptable perceived delay? |
| **Error** | Something failed (network, validation, permission) | Actionable message? Can the user retry? Do they know why? |
| **Ideal** | The normal, populated state | Often the only designed state — insufficient on its own. |

## Checklist

For each interactive component in scope:

- [ ] Empty state defined?
- [ ] Loading state defined?
- [ ] Error state defined (actionable message)?
- [ ] Success/confirmation defined if the action is destructive or asynchronous?
- [ ] Edge cases: very long strings, zero items, max items, slow network?

## Output

List of missing states per component + recommendation. If all states are covered → silence.
