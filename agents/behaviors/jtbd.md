---
name: jtbd
description: Jobs-to-be-Done — reformulate request as user job before evaluating scope or solution
pattern_author: Clayton Christensen, The Innovator's Solution (2003)
used_by: [product-builder, tech-lead]
---

# Jobs-to-be-Done (JTBD)

*Clayton Christensen, The Innovator's Solution (2003)*

Users do not need features — they have a "job" to accomplish. Features are merely a means to get there. If the ticket prescribes a solution without explaining the problem, that is a red flag.

## Questions

- What job is the user "hiring" this feature to accomplish?
- What do they do today instead, and why is that insufficient?
- What does "done" look like for them — what is the emotional outcome?
- When does this situation concretely arise in their daily life?

## JTBD Statement format

*"When [situation], I want [motivation] so that [expected outcome]."*

Example: *"When I return to the board after 3 days away, I want to immediately see what has changed so I don't have to re-read the entire history."*

## Protocol

1. Write the JTBD statement in one sentence
2. Verify that the solution proposed in the ticket accomplishes this job
3. If not → challenge the scope or ask a framing question
4. If yes → use the statement to prune elements that do not contribute to it

## Output

```
JTBD: "When X, the user wants Y in order to Z."
Alignment with the ticket: [yes / partial / no — explanation if partial or no]
```
