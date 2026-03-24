---
name: ci-discipline
description: Universal CI principles — stack/platform detection, profile selection, local gate, smoke test. Load from dev persona.
scope: dev persona (always, step 3)
---

# CI Discipline — Universal trunk

---

## 1. Detection — stack + CI platform + deploy platform

### Stack (project language)

```bash
detect_stack() {
  local r="$1"
  [ -f "$r/pyproject.toml" ] || [ -f "$r/requirements.txt" ] && echo "python" && return
  [ -f "$r/package.json" ]                                    && echo "node"   && return
  [ -f "$r/go.mod" ]                                         && echo "go"     && return
  [ -f "$r/Gemfile" ]                                        && echo "ruby"   && return
  [ -f "$r/pom.xml" ] || [ -f "$r/build.gradle" ]           && echo "java"   && return
  echo "unknown"
}
```

### CI platform (where workflows will run)

```bash
detect_ci_platform() {
  local r="$1"
  [ -d "$r/.github/workflows" ]   && echo "github"   && return
  [ -f "$r/.gitlab-ci.yml" ]      && echo "gitlab"   && return
  [ -d "$r/.circleci" ]           && echo "circleci" && return
  echo "github"  # default — GitHub Actions if nothing is detected
}
```

### Deploy platform (for the smoke test)

```bash
# Read cao.config.yml if present
DEPLOY_PLATFORM=$(python3 -c "
import sys
try:
    import yaml
    cfg = yaml.safe_load(open('${_REPO_ROOT}/cao.config.yml'))
    print(cfg.get('deploy', {}).get('platform', 'none'))
except: print('none')
" 2>/dev/null || echo "none")
```

---

## 2. CI profile selection

| Stack | CI Platform | Profile |
|-------|-------------|---------|
| python | github | `agents/ci-profiles/github-python.yml` |
| node | github | `agents/ci-profiles/github-node.yml` |
| go | github | `agents/ci-profiles/github-go.yml` *(stub)* |
| * | gitlab | `agents/ci-profiles/gitlab-{stack}.yml` *(future)* |
| unknown | * | No generation — post a warning on the ticket |

Read the selected profile and replace placeholders (`{{PYTHON_VERSION}}`, `{{NODE_VERSION}}`, etc.) with the detected values.

---

## 3. CI file generation

**Target path by platform:**

| CI Platform | Target file |
|-------------|-------------|
| github | `.github/workflows/ci.yml` |
| gitlab | `.gitlab-ci.yml` |
| circleci | `.circleci/config.yml` |

**Generation rules:**

| State of existing file | Action |
|------------------------|--------|
| Absent | Create from profile |
| Present, already contains a test step | Do not touch |
| Present, without a test step | Add the test step at the end of the existing job |
| Unknown stack | Do not generate — post a warning: `"Unrecognized stack — CI not generated. Add manually."` |

**Separate commit — always:**

```bash
git add .github/workflows/ci.yml   # or equivalent
git commit -m "chore: add CI workflow (${STACK} + ${CI_PLATFORM})"
```

Never bundle CI with implementation commits.

---

## 4. Local gate — before any push

The local gate runs **between implementation and push**, independently of the platform.

**Enforced sequence:**
```
implementation → local gate (tests + coverage) → push → PR
```

**Command by stack:**

| Stack | Gate command |
|-------|-------------|
| python | `python -m pytest tests/ -v --tb=short --cov=src --cov-fail-under=70` |
| node | `npm test -- --coverage` (or `npx vitest run --coverage`) |
| go | `go test ./... -cover` |
| ruby | `bundle exec rspec` |
| unknown | Look for a `test` script in the project — if absent, block and ask |

**Universal blocking rules:**

| Condition | Action |
|-----------|--------|
| Command not found / setup error | Blocking — diagnose |
| Tests collected = 0 | Blocking — write tests |
| Tests failed > 0 | Blocking — fix |
| Tests skipped > 0 without reason in code | Blocking — investigate |
| Tests skipped with documented reason | Warning logged, push allowed |
| Coverage < configured threshold | Blocking — complete the tests |

**Logging:**
```bash
_log "$RUN_ID" "dev" "$TICKET_N" "pytest_gate" "ok" \
  "local test gate passed" \
  "{\"stack\":\"$STACK\",\"passed\":$PASSED,\"failed\":$FAILED,\"skipped\":$SKIPPED,\"collected\":$COLLECTED}"
```

---

## 5. Branch protection verification (post-CI creation)

After creating or modifying the CI, verify whether the base branch requires this CI to pass before merge:

```bash
PROTECTION=$(gh api \
  repos/$OWNER/$REPO/branches/dev/protection \
  --jq '.required_status_checks.contexts // []' 2>/dev/null || echo "[]")

CI_REQUIRED=$(echo "$PROTECTION" | python3 -c "
import json, sys
contexts = json.load(sys.stdin)
print('yes' if any('test' in c.lower() or 'ci' in c.lower() for c in contexts) else 'no')
")

if [ "$CI_REQUIRED" = "no" ]; then
  gh issue comment "$TICKET_N" --repo "$OWNER/$REPO" \
    --body "⚠️ **CI created but branch protection not configured**

The CI file was generated, but the \`dev\` branch does not require CI to pass before merge.

To block merges if CI fails:
\`\`\`
GitHub → Settings → Branches → Branch protection rules → dev
→ ✅ Require status checks to pass before merging
→ Add: \"test\" (or the job name in ci.yml)
\`\`\`"
fi
```

---

## 6. Post-deploy smoke test

The smoke test is conditional: active **only** if `DEPLOY_PLATFORM != none`.

**`PREVIEW_URL` is provided by the deploy profile** (`agents/deploy-profiles/${DEPLOY_PLATFORM}.md`) — this file does not handle URL retrieval, only its evaluation.

### Routes to test

1. `testing.smoke_routes` in `cao.config.yml` if present
2. Otherwise: routes extracted from the enrichment plan's acceptance criteria
3. Minimal default: `["/"]`

### What constitutes a failure

| Condition | Result |
|-----------|--------|
| HTTP 5xx | Failure — return to to-dev |
| HTTP 404 on `/` | Failure — return to to-dev |
| HTTP 404 on specific route | Warning (may be legitimate) |
| Response time > 5s | Warning logged, non-blocking |
| `PREVIEW_URL` empty (timeout) | Warning logged, smoke skipped, flow continues |

### On failure

```bash
gh pr comment "$PR_NUMBER" --repo "$OWNER/$REPO" \
  --body "🚨 **Smoke test failed** — deploy platform: ${DEPLOY_PLATFORM}

Routes tested:
${SMOKE_RESULTS}

Ticket returned to \`to-dev\` for investigation."

gh issue edit "$TICKET_N" --repo "$OWNER/$REPO" \
  --remove-label "dev-in-progress" --add-label "to-dev"

exit 1
```

### Curl execution (universal trunk)

```bash
smoke_test_routes() {
  local base_url="$1"
  shift
  local routes=("$@")
  local failed=0
  local results=""

  for route in "${routes[@]}"; do
    local url="${base_url}${route}"
    local response
    response=$(curl -s -o /tmp/smoke_body -w "%{http_code} %{time_total} %{content_type}" \
      --max-time 15 "$url" 2>/dev/null)
    local status time_s content_type
    read -r status time_s content_type <<< "$response"

    local line="- \`${route}\`: HTTP ${status} (${time_s}s)"

    if [[ "$status" =~ ^5 ]]; then
      line="${line} ❌ FAIL"
      failed=$((failed + 1))
    elif [[ "$route" == "/" && "$status" == "404" ]]; then
      line="${line} ❌ FAIL (root not found)"
      failed=$((failed + 1))
    elif (( $(echo "$time_s > 5.0" | bc -l 2>/dev/null || echo 0) )); then
      line="${line} ⚠️ SLOW"
    else
      line="${line} ✅ OK"
    fi

    results="${results}\n${line}"
  done

  echo "$results"
  return $failed
}
```

---

## 7. cao.config.yml configuration

Optional fields to override default behaviors:

```yaml
# cao.config.yml
testing:
  smoke_routes: ["/", "/health", "/api/status"]  # replaces the default
  smoke_timeout_s: 300                            # max wait for bot comment
  coverage_threshold: 70                          # minimum coverage %
```
