---
name: deploy-profile-render
description: Deploy preview via Render — auto-deploy on push, URL via render[bot] comment.
platform: render
url_source: bot-comment
---

# Deploy Profile — Render

## Deploy

Render deploys automatically on every push if "Preview Environments" are enabled in the project — **no action to trigger**.

## URL retrieval

Render posts a comment on the PR via its GitHub App (`render[bot]`).

```bash
PREVIEW_URL=""
MAX_WAIT=${SMOKE_TIMEOUT_S:-300}
POLL_INTERVAL=20
ELAPSED=0

while [ -z "$PREVIEW_URL" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))

  RENDER_COMMENT=$(gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" \
    --json comments \
    --jq '.comments[]
          | select(.author.login == "render[bot]")
          | .body' \
    2>/dev/null | tail -1)

  PREVIEW_URL=$(echo "$RENDER_COMMENT" \
    | grep -oP 'https://[a-zA-Z0-9\-]+\.onrender\.com[^\s"]*' | head -1)
done

if [ -z "$PREVIEW_URL" ]; then
  _log "$RUN_ID" "dev" "$TICKET_N" "deploy_preview" "warning" \
    "Render URL not found after ${MAX_WAIT}s — smoke test skipped" '{}'
fi
```

## Smoke test

Pass `PREVIEW_URL` to `smoke_test_routes()` in `ci-discipline.md`.

## Notes

- Render "Preview Environments" must be enabled in the project's Render dashboard
- If not enabled, `PREVIEW_URL` will be empty → smoke test skipped (non-blocking)
- First Render deploy on a PR can take 3–5 min depending on build size
