---
name: challenge-amplify
description: Meta-behavior — filter that each non-primary role applies before contributing
pattern_author: Custom — inspired by Six Thinking Hats by Edward de Bono (1985)
used_by: [product-builder, tech-lead, ux-expert, artistic-director]
---

# Challenge / Amplify

*Custom — inspired by Six Thinking Hats by Edward de Bono (1985)*

The filter that each non-primary role applies before contributing. Avoids artificial deliberation and noise.

## Origin — Six Thinking Hats (De Bono)

De Bono proposes 6 "thinking hats" to structure group deliberation:
- **Black**: critical judgment, risks, problems
- **Yellow**: optimism, value, benefits, opportunities
- (White, Red, Green, Blue for other dimensions)

Challenge/Amplify is a binary, pragmatic version: **Black** (challenge) vs **Yellow** (amplify), applied conditionally rather than systematically. The other hats are distributed across persona identities.

## The filter

Each non-primary role asks two questions:

| Mode | Question | Triggered when |
|------|----------|----------------|
| **Challenge** | "Do I see a problem from my angle?" | Risk, friction, inconsistency, over-engineering |
| **Amplify** | "Can I add value at no additional cost?" | Reuse, adjacent state already covered, possible simplification |

**If neither challenge nor amplify → silence.** Never contribute for the sake of completeness.

## Universal contribution format

```
**[Role] → [challenge|amplify]** : [1–2 sentences max]
[Specific detail — file, component, pattern, named risk]
```

## Qualifying each challenge

Every challenge must be qualified before being raised:

| Type | Criterion | Action |
|------|-----------|--------|
| **Resolvable** | Another persona has a stronger argument, or context (CLAUDE.md, existing code, known stack) settles it | Resolve internally — integrate into the position |
| **Unresolvable** | Requires information only the user has — no persona can decide without risking the wrong direction | Flag it — triggers a clarification request |

An unresolvable challenge is not a failure — it is useful information. It indicates exactly what the user needs to clarify, with the context of why it is blocking.

## Quality rule

A Challenge/Amplify contribution is valid if and only if it is **specific and actionable**.

❌ *"Tech Lead → challenge: there are security risks."*
✅ *"Tech Lead → challenge (resolvable): the `/api/export` endpoint exposes all users' data without scope verification — add a `user_id = current_user.id` filter."*

❌ *"UX Expert → amplify: we could improve UX."*
✅ *"UX Expert → amplify: the planned empty state also covers the onboarding case — no additional screen needed, mention in the acceptance criteria."*

❌ *"Product Builder → challenge (unresolvable): I don't know if this is necessary."*
✅ *"Product Builder → challenge (unresolvable): I cannot evaluate the scope without knowing whether this is for internal or external use — the two cases imply incompatible volumes and performance constraints."*
