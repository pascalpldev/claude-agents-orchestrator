---
name: product-baseline
description: YAGNI philosophy calibrated by maturity — knowing when a module becomes necessary, not forcing it before
---

# Product Baseline

This behavior is not a checklist of modules to tick off. It is a philosophy of judgment: **YAGNI, but calibrated by the project's actual exposure**.

---

## The core philosophy

YAGNI is not an absolute rule — it is a dial. What is premature in a solo project becomes urgent the moment there are real users, real data, or a reputation at stake.

The right question is not *"should we have this?"* but *"what is the cost of its absence at this stage?"*

- **Low cost** → aggressive YAGNI, don't mention it
- **Growing cost** → signal the optimal moment, don't force it now
- **Immediate cost** → recommend without hesitation

The stage is read from project signals: number of users, nature of collected data, whether third parties have access, whether reputation is on the line. A project can be "solo" on one feature and "public" on another.

---

## The modules that matter

These modules have one thing in common: their absence is invisible until the moment it becomes costly — and by then, it is often too late to put them in place properly.

### Feedback and observation

**User feedback**: as soon as there are users who are not you, a direct feedback channel is more valuable than any feature. Not buried in settings — visible, in 10 seconds, from anywhere in the product. Without it, the product is blind.

**Behavioral observation**: users declare what they think, tracking shows what they actually do. These two pieces of information are complementary and often contradictory. Setting up the foundation early (PostHog free tier, for example) costs little — catching up on missed observation never happens.

> These two modules are non-negotiable as soon as there are third-party users. No YAGNI here.

### Logs and errors

**Logs**: even in a solo project, logs save time. As soon as there are other users, they become critical — you need to know about your users' errors before they report them to you. An external error tracker (Sentry or equivalent) is not a luxury.

**Visible robustness**: clean error pages, clear status messages, handled timeouts — all of this signals the perceived quality of the product. The more users there are, the more it matters.

> Logs are the only way to see what is happening when you are not there. Set this up early.

### Access and identity

Do not build a full auth system before you need one. But distinguish two very different needs:

- **Protecting access** during the test phase: a shared code or a token link is enough — no registration, no password reset
- **Managing user accounts**: only when the product has a stable foundation and the full lifecycle (expiration, logout, recovery) makes sense

The signal: are people arriving by invitation or referral? What is the risk if an unwanted person gains access?

### Data and compliance

As soon as personal data from third-party users is collected, account export and deletion are not optional — it is GDPR. The form can be minimal (JSON generated on demand, manual deletion), but it must exist.

### Communication and onboarding

Notifications and changelog: only when the product evolves fast enough that users can no longer keep up without help.

Onboarding and contextual help: as soon as a flow is not self-explanatory. See `discoverability.md`.

---

## How to reason in practice

When reading a ticket, one question only: **will the absence of one of these modules cost something at this stage?**

If yes → mention it with the appropriate level of urgency.
If no → complete silence.

Do not mention something because "we'll need it someday." Mention it because the moment has come — or because the cost of waiting is starting to exceed the cost of building.
