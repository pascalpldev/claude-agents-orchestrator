---
name: test-discipline
description: Universal testing principles — tech-agnostic. Load the stack enrichment file alongside.
scope: dev persona (always)
reference: "Growing Object-Oriented Software (Freeman & Pryce), TDD by Example (Kent Beck)"
---

# Test Discipline — Universal trunk

> This file defines invariant principles. Load the stack enrichment file after detection:
> `agents/behaviors/test-discipline-{stack}.md` (python | node | go | ...)
> If no enrichment exists for the detected stack, this file is sufficient.

---

## Philosophy

**Test behavior, not implementation.** A test that fails when you rename a private variable is a bad test. A test that fails when you break a public contract is a good test.

Line coverage is an indicator, not a goal. 70% on the critical paths of new code is better than 100% on getters.

**Zero tests collected = blocking.** If no test is collected after implementation, the dev agent must write tests before pushing. A push without tests is not acceptable.

---

## Naming

A test name is its documentation. It must be readable by a non-technical human.

**Universal pattern**: `<subject>_<condition>_<expected result>`

```
# ✅ Describes a behavior
login_with_expired_token_returns_401
cart_total_applies_discount_when_code_is_valid
user_creation_fails_when_email_already_exists

# ❌ Describes the implementation
check_token
calculate
create_user_error
```

The exact syntax (function, method, annotation) depends on the stack — see the enrichment file.

---

## AAA Structure (Arrange / Act / Assert)

Each test follows this pattern, visually separated:

```
# Arrange — prepare data and context
# Act     — execute the tested action (one only)
# Assert  — verify the result
```

One logical Assert per test. Multiple assertions to describe the same behavior = acceptable. Multiple assertions to test different behaviors = split the test.

---

## Isolation

Each test must be independent: no dependency on execution order, no shared state between tests.

**Rules**:
- Each test creates its own data — no modified global state
- Tests pass in any order
- Clean up after yourself (teardown, DB rollback, reset mocks)

**Mocks — limited use**:
- Mock real **external** dependencies: third-party API, email, system clock, external service
- Do not mock what you own — write an integration test instead
- A test that mocks everything it calls tests nothing

---

## What to test

| ✅ Test | ❌ Do not test |
|---------|---------------|
| Business logic (calculations, rules, transformations) | Trivial getters/setters |
| Error paths (invalid input, missing resource) | Framework internals (ORM, routing) |
| API contracts (status codes, response format) | Auto-generated code |
| Edge cases (zero, empty, null, max, negative) | Constants and static configuration |
| Integration behavior (DB, cache) | Pure logging code |
| Auth: access denied if not authenticated | Re-testing what the framework guarantees |

---

## Test types

**Unit** — pure logic, no external dependency:
- Transformation, calculation, validation functions
- Classes with business rules
- Fast, numerous, isolated

**Integration** — interactions between components:
- API endpoints (happy path + at least one error path)
- DB interactions on non-trivial queries
- One integration test replaces N unit tests on fragile mocks

**E2E** — do not write unless the enrichment plan explicitly requires it.

---

## Blocking rules before push

| Condition | Action |
|-----------|--------|
| Tests collected = 0 | Blocking — write tests |
| Tests failed > 0 | Blocking — fix |
| Tests skipped > 0 without documented reason | Blocking — investigate |
| Tests skipped with reason documented in code | Warning logged, push allowed |
| Coverage < 70% on new code | Blocking — complete the tests |

A skip without a visible reason in the source code is always blocking.

---

## Enrichment → tests mapping

Each acceptance criterion from the enrichment plan must have a corresponding test. Verify 1:1 before opening the PR:

```
Acceptance criterion              → Test
────────────────────────────────────────────────────────
☑ Behaviour A works               → <subject>_normal_path_returns_expected()
☑ Edge case B is handled          → <subject>_with_edge_case_B_returns_X()
☑ Error path C returns 404        → <subject>_missing_resource_returns_404()
☑ No regression on D              → <subject>_existing_D_still_works()
```

If a criterion cannot be translated into an automated test: document it in the PR body under `## Testing` with the manual verification procedure.

---

## Test file placement

Follow the existing project convention (read CLAUDE.md). In the absence of a convention:

```
# Option A — co-located
src/
  users/
    user_service.<ext>
    test_user_service.<ext>

# Option B — separate directory
tests/
  unit/
    test_user_service.<ext>
  integration/
    test_user_api.<ext>
```

Do not create a new structure if a convention already exists — consistency comes first.
