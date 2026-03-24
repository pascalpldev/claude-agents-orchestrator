---
name: deploy-profile-vercel
description: Deploy preview via Vercel — auto-deploy on push, URL via GitHub status checks.
platform: vercel
url_source: github-status-checks
---

# Deploy Profile — Vercel

## Deploy

Vercel deploys automatically on every push to a feature branch — **no action to trigger**.

The dev agent only needs to wait for the deploy to appear in the PR's status checks.

## URL retrieval

Vercel exposes the preview URL in the GitHub status checks of the PR.

```bash
PREVIEW_URL=""
MAX_WAIT=${SMOKE_TIMEOUT_S:-180}  # Vercel is fast — 3 min is generally enough
POLL_INTERVAL=15
ELAPSED=0

while [ -z "$PREVIEW_URL" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))

  # 1. Look in status checks
  PREVIEW_URL=$(gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" \
    --json statusCheckRollup \
    --jq '.statusCheckRollup[]
          | select(.name | test("vercel"; "i"))
          | select(.targetUrl | test("vercel.app"))
          | .targetUrl' \
    2>/dev/null | head -1)

  # 2. Fallback — look in the PR body (Vercel sometimes posts the URL there)
  if [ -z "$PREVIEW_URL" ]; then
    PREVIEW_URL=$(gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" \
      --json body \
      --jq '.body' \
      | grep -oP 'https://[a-zA-Z0-9\-]+\.vercel\.app[^\s"]*' | head -1)
  fi
done

if [ -z "$PREVIEW_URL" ]; then
  _log "$RUN_ID" "dev" "$TICKET_N" "deploy_preview" "warning" \
    "Vercel URL not found after ${MAX_WAIT}s — smoke test skipped" '{}'
fi
```

## Smoke test

Pass `PREVIEW_URL` to `smoke_test_routes()` in `ci-discipline.md`.

## Notes

- Vercel does not require an MCP — the deploy is entirely managed by the Vercel GitHub integration
- If the project does not have the Vercel-GitHub integration enabled, `PREVIEW_URL` will be empty → smoke test skipped (non-blocking)
