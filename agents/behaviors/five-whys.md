---
name: five-whys
description: Root cause analysis — ask why 5 times before accepting a prescribed solution
pattern_author: Taiichi Ohno, Toyota Production System (1978)
used_by: [product-builder]
---

# 5 Whys

*Taiichi Ohno, Toyota Production System (1978)*

Ask "why" five times to move from symptom to root cause. Avoids building solutions to the wrong problem.

## When to invoke it

- The ticket prescribes a technical solution without explaining the user problem
- The request appears to be a workaround rather than a real solution
- The scope seems disproportionate relative to what is described

## Protocol

Start from the request as it is stated, then:

1. Why do we need this?
2. Why is [answer 1] a problem?
3. Why does [answer 2] occur?
4. Why is [answer 3] not already resolved?
5. Why [answer 4] — that is the root cause.

Stop before 5 if the root cause is clearly identified.

## Output

```
Root cause: [description]
The solution proposed in the ticket: [addresses / does not address / partially addresses] the root cause
Recommendation: [proceed / reformulate the scope / ask a framing question]
```
