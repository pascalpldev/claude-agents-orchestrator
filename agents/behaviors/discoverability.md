---
name: discoverability
description: Make the interface self-explanatory — the user knows what to do, where they are, and can get started without external help
references:
  - "Don Norman — The Design of Everyday Things (1988): affordances, signifiers, feedback"
  - "Jakob Nielsen — Usability heuristics #1 (visibility of status) and #6 (recognition > recall)"
---

# Discoverability

The user should never have to guess what an element does, nor read documentation to get started.

## The three axes

| Axis | Question | Symptoms of a problem |
|------|----------|-----------------------|
| **Explicit interface** | Does the user know what each element does without trying it? | Icons without labels, buttons without action verbs, vague placeholders, states without explanation |
| **Visible process** | Does the user know where they are and what comes next? | Multi-step flows without a stepper, actions without feedback, silent results, spinner without a message |
| **Onboarding** | Does first contact lead to a quick success without external help? | Inert empty state, technical jargon at startup, unclear primary action, no guidance on what can be done |

## Protocol

1. Identify entry points: first screen, empty state, primary action
2. For each interactive element: is its role obvious without thinking?
3. List implicit elements (orphaned icons, actions without feedback, undefined terms)
4. Propose a targeted fix: tooltip, label, status message, instructive empty state

## Common fixes

| Problem | Fix |
|---------|-----|
| Icon without label | Add tooltip on hover + visible label if space allows |
| "OK" or "Submit" button | Precise action verb: "Create project", "Send invitation" |
| `"Email"` placeholder | Instructive placeholder: `"name@example.com"` or hint below the field |
| Action without feedback | Confirmation message or visible success state (even 2 seconds) |
| Neutral empty state | Instructive empty state: explain what to do, suggest the primary action |
| Hidden stepper | Visible progress indicator (step X of N) |

## Output

```
Implicit elements: [list, or "(none)"]
Unguided entry points: [list, or "(none)"]
Recommendations: [1 line per item]
```

**Rule**: Silence if the interface is already self-explanatory. Do not contribute if no discovery path is broken.
