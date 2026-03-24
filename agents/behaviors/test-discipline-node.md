---
name: test-discipline-node
description: Test enrichment for Node/TypeScript projects — Jest/Vitest, async, coverage. Load alongside test-discipline.md.
scope: dev persona (if stack = node)
reference: "Jest docs, Vitest docs, Testing Library"
---

# Test Discipline — Node / TypeScript Enrichment

> Complements `test-discipline.md`. Universal principles apply — this file adds patterns specific to Jest/Vitest.

---

## Runner detection

```bash
detect_test_runner() {
  local repo_root="$1"
  # Vitest (vite-based projects)
  if grep -q '"vitest"' "$repo_root/package.json" 2>/dev/null; then
    echo "vitest"
  # Jest
  elif grep -q '"jest"' "$repo_root/package.json" 2>/dev/null; then
    echo "jest"
  # npm test fallback
  else
    echo "npm"
  fi
}
```

---

## Reference commands

```bash
# Jest
npx jest --coverage --verbose 2>&1

# Vitest
npx vitest run --coverage 2>&1

# npm test (fallback — reads the "test" script from package.json)
npm test -- --coverage 2>&1
```

**Parsing results**:

```bash
TEST_OUTPUT=$(npm test -- --coverage 2>&1)
TEST_EXIT=$?

# Jest / Vitest output format: "Tests: X failed, Y passed, Z total"
FAILED=$(echo "$TEST_OUTPUT"  | grep -oP '\d+(?= failed)'  | tail -1 || echo "0")
PASSED=$(echo "$TEST_OUTPUT"  | grep -oP '\d+(?= passed)'  | tail -1 || echo "0")
SKIPPED=$(echo "$TEST_OUTPUT" | grep -oP '\d+(?= skipped)' | tail -1 || echo "0")
TOTAL=$(echo "$TEST_OUTPUT"   | grep -oP '\d+(?= total)'   | tail -1 || echo "0")
[ "$TOTAL" = "0" ] && COLLECTED=0 || COLLECTED=$TOTAL
```

---

## Naming

```typescript
// ✅ Good — behavior described
it('returns 401 when token is expired', ...)
it('applies discount when promo code is valid', ...)
it('throws when user email already exists', ...)

// ❌ Bad — implementation described
it('checks token', ...)
it('calculates', ...)
```

Group with `describe` by tested unit:

```typescript
describe('CartService', () => {
  describe('calculateTotal', () => {
    it('applies tax rate', ...)
    it('applies discount when code is valid', ...)
    it('returns 0 for empty cart', ...)
  })
})
```

---

## AAA Structure

```typescript
it('applies discount when promo code is valid', () => {
  // Arrange
  const cart = new Cart([new Item({ price: 100 })])
  const promoCode = 'SAVE10'

  // Act
  const total = cart.calculateTotal({ promoCode })

  // Assert
  expect(total).toBe(90)
})
```

---

## Async — correct patterns

```typescript
// ✅ async/await — readable, errors propagated correctly
it('fetches user by id', async () => {
  const user = await userService.findById('123')
  expect(user.email).toBe('test@example.com')
})

// ✅ Explicit Promise if needed
it('rejects with NotFoundError for unknown id', async () => {
  await expect(userService.findById('unknown')).rejects.toThrow(NotFoundError)
})

// ❌ No .then() in tests — hides async errors
it('bad async test', (done) => {
  userService.findById('123').then(user => {
    expect(user.email).toBe('test@example.com')
    done()
  })
})
```

---

## Setup / Teardown

```typescript
describe('UserRepository', () => {
  let db: Database

  beforeAll(async () => {
    db = await createTestDatabase()  // expensive — once per suite
  })

  afterAll(async () => {
    await db.close()
  })

  beforeEach(async () => {
    await db.truncate('users')       // isolation — before each test
  })
})
```

`beforeAll` for expensive resources. `beforeEach` for data isolation.

---

## Mocks

```typescript
// ✅ Mock an external dependency (email service)
jest.mock('../services/emailService')
const mockSendEmail = emailService.send as jest.Mock

it('sends welcome email on user creation', async () => {
  await userService.create({ email: 'new@example.com' })
  expect(mockSendEmail).toHaveBeenCalledWith(
    expect.objectContaining({ to: 'new@example.com' })
  )
})

// ✅ Spy on an existing method
jest.spyOn(logger, 'error').mockImplementation(() => {})

// ❌ Do not mock your own business modules — write an integration test
```

---

## Documented skips

```typescript
// ✅ Documented skip — non-blocking
it.skipIf(!process.env.STRIPE_API_KEY)(
  'charges card via Stripe API',
  async () => { ... }
)

// ✅ Explicit todo
it.todo('handles concurrent cart updates')

// ❌ Skip without reason — blocking
it.skip('something', () => { ... })
xit('something', () => { ... })
```

---

## Coverage

```bash
# Jest — threshold on new code
npx jest --coverage --coverageThreshold='{"global":{"lines":70}}'

# Vitest
npx vitest run --coverage --coverage.thresholds.lines=70
```

Exclude in `jest.config.js` or `vitest.config.ts`:
```javascript
coveragePathIgnorePatterns: [
  '/node_modules/',
  '/__generated__/',
  '/migrations/',
]
```

---

## Node version detection

```bash
detect_node_version() {
  local repo_root="$1"
  # 1. .nvmrc
  if [ -f "$repo_root/.nvmrc" ]; then
    cat "$repo_root/.nvmrc" | tr -d 'v\n'
    return
  fi
  # 2. package.json engines.node
  if [ -f "$repo_root/package.json" ]; then
    local v
    v=$(python3 -c "
import json, re
pkg = json.load(open('$repo_root/package.json'))
engines = pkg.get('engines', {}).get('node', '')
m = re.search(r'(\d+)', engines)
print(m.group(1) if m else '')
" 2>/dev/null)
    [ -n "$v" ] && echo "$v" && return
  fi
  # 3. Dockerfile
  if [ -f "$repo_root/Dockerfile" ]; then
    local v
    v=$(grep -oP 'FROM\s+node:\K\d+' "$repo_root/Dockerfile" | head -1)
    [ -n "$v" ] && echo "$v" && return
  fi
  # 4. LTS Fallback
  echo "20"
}
```
