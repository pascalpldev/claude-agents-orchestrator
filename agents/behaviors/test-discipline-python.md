---
name: test-discipline-python
description: Test enrichment for Python projects — pytest, fixtures, coverage. Load alongside test-discipline.md.
scope: dev persona (if stack = python)
reference: "pytest docs, pytest-cov, hypothesis"
---

# Test Discipline — Python Enrichment

> Complements `test-discipline.md`. Universal principles apply — this file adds patterns specific to pytest.

---

## Reference commands

```bash
# Run tests with coverage
python -m pytest tests/ -v --tb=short \
  --cov=src --cov-report=term-missing \
  --cov-fail-under=70

# Parse results
PYTEST_OUTPUT=$(python -m pytest tests/ -v --tb=short 2>&1)
PYTEST_EXIT=$?

COLLECTED=$(echo "$PYTEST_OUTPUT" | grep -oP '\d+(?= item)' | head -1 || echo "0")
PASSED=$(echo "$PYTEST_OUTPUT"   | grep -oP '\d+(?= passed)' | tail -1 || echo "0")
FAILED=$(echo "$PYTEST_OUTPUT"   | grep -oP '\d+(?= failed)' | tail -1 || echo "0")
SKIPPED=$(echo "$PYTEST_OUTPUT"  | grep -oP '\d+(?= skipped)' | tail -1 || echo "0")
# Exit 5 = no tests collected — treat as COLLECTED=0
[ $PYTEST_EXIT -eq 5 ] && COLLECTED=0
```

**pytest exit codes**:

| Code | Meaning | Action |
|------|---------|--------|
| 0 | All pass | Continue |
| 1 | Tests failed | Blocking |
| 2 | Interrupted (Ctrl+C) | Blocking |
| 3 | Internal pytest error | Blocking |
| 4 | Command line error | Blocking |
| 5 | No tests collected | Blocking — write tests |

---

## Naming

```python
# ✅ Good — behavior described
def test_login_with_expired_token_returns_401():
def test_cart_total_applies_discount_when_code_is_valid():
def test_user_creation_fails_when_email_already_exists():

# ❌ Bad — implementation described
def test_check_token():
def test_calculate():
```

---

## AAA Structure

```python
def test_order_total_includes_tax():
    # Arrange
    cart = Cart(items=[Item(price=100)])
    tax_rate = 0.2

    # Act
    total = cart.calculate_total(tax_rate=tax_rate)

    # Assert
    assert total == 120
```

---

## Fixtures

Use pytest fixtures for shared setup — never a class `setUp` if a fixture suffices.

```python
# conftest.py — fixtures shared across test files
import pytest

@pytest.fixture
def db_session():
    """Provides an isolated DB session, rolled back after each test."""
    session = create_test_session()
    yield session
    session.rollback()
    session.close()

@pytest.fixture
def authenticated_client(client, user):
    """HTTP client with a valid auth token."""
    token = create_token(user.id)
    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

**Scopes**: `function` (default) for isolation, `session` only for expensive-to-create resources (e.g., DB schema).

---

## Parametrize — for edge cases

```python
import pytest

@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("not-an-email",     False),
    ("",                 False),
    ("a" * 256 + "@b.com", False),  # too long
])
def test_email_validation(email, valid):
    assert validate_email(email) == valid
```

Prefer `parametrize` over multiple test functions when the logic is identical and only the data changes.

---

## Mocks

```python
from unittest.mock import patch, MagicMock

# ✅ Mock an external dependency (third-party API)
def test_send_email_calls_smtp():
    with patch("myapp.email.smtplib.SMTP") as mock_smtp:
        send_welcome_email("user@example.com")
        mock_smtp.return_value.__enter__.return_value.sendmail.assert_called_once()

# ❌ Do not mock your own modules
# → Write an integration test instead
```

---

## Documented skips

A skip is acceptable **only** if the reason is explicit in the code:

```python
# ✅ Documented skip — non-blocking
@pytest.mark.skipif(
    os.getenv("STRIPE_API_KEY") is None,
    reason="Requires STRIPE_API_KEY — run manually with real credentials"
)
def test_stripe_charge_creates_payment():
    ...

# ❌ Skip without reason — blocking
@pytest.mark.skip
def test_something():
    ...
```

---

## Coverage

```bash
# Target only new code — not legacy
python -m pytest tests/ \
  --cov=src \
  --cov-report=term-missing \
  --cov-fail-under=70

# Exclude generated code and configs
# In pyproject.toml or setup.cfg:
# [tool:pytest]
# addopts = --cov-config=.coveragerc
#
# .coveragerc:
# [run]
# omit = */migrations/*, */generated/*, */config.py
```

Threshold: **70% on new code** — not on the entire project. Do not reduce existing coverage.

---

## Python version detection

```bash
detect_python_version() {
  local repo_root="$1"
  # 1. pyproject.toml
  if [ -f "$repo_root/pyproject.toml" ]; then
    local v
    v=$(python3 -c "
import re, sys
content = open('$repo_root/pyproject.toml').read()
m = re.search(r'requires-python\s*=\s*\"[>=!<~^]*(\d+\.\d+)', content)
print(m.group(1) if m else '')
" 2>/dev/null)
    [ -n "$v" ] && echo "$v" && return
  fi
  # 2. Dockerfile
  if [ -f "$repo_root/Dockerfile" ]; then
    local v
    v=$(grep -oP 'FROM\s+python:\K\d+\.\d+' "$repo_root/Dockerfile" | head -1)
    [ -n "$v" ] && echo "$v" && return
  fi
  # 3. Fallback
  echo "3.11"
}
```
