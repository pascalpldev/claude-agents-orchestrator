---
name: fmea
description: Failure Mode and Effects Analysis — structured risk table for production-critical paths only
pattern_author: U.S. Military, MIL-P-1629 (1949) — adapted for software
used_by: [tech-lead]
---

# FMEA — Failure Mode and Effects Analysis

*U.S. Military, MIL-P-1629 (1949) — adapted for software*

For each critical path: what fails, what is the probability, what is the impact, what is the detection/mitigation.

## When to invoke it

Only if the ticket touches a critical path: payment, authentication, user data, external integration, data migration, critical background job.

Do not apply to standard CRUD tickets or UI changes with no data impact.

## Format

| Component | Failure mode | Probability | Impact | Mitigation |
|-----------|-------------|-------------|--------|------------|
| ... | ... | L/M/H | L/M/H | ... |

## Protocol

1. List the critical components affected by the ticket
2. For each one: identify plausible failure mode(s)
3. Evaluate probability × impact (document only M×M and above)
4. Propose a mitigation for each retained risk
5. If rollback is required: state it explicitly

Do not create an exhaustive table — only non-trivial and actionable risks.

## Output

FMEA table (format above) + rollback strategy if applicable.
