---
name: deploy-profile-railway-auto
description: Deploy preview via Railway auto-deploy on push — URL via Railway bot comment on PR.
platform: railway-auto
url_source: bot-comment
---

# Deploy Profile — Railway (auto-deploy)

## Deploy

Railway deploys automatically on every push if "Preview Environments" are enabled
in the project — **no action to trigger**.

## URL retrieval

Railway posts a comment on the PR via its GitHub App (`railway-app`).
Poll until the comment appears and contains a preview URL.

```bash
PREVIEW_URL=""
MAX_WAIT=${SMOKE_TIMEOUT_S:-300}
POLL_INTERVAL=15
ELAPSED=0

while [ -z "$PREVIEW_URL" ] && [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))

  RAILWAY_COMMENT=$(gh pr view "$PR_NUMBER" --repo "$OWNER/$REPO" \
    --json comments \
    --jq '.comments[]
          | select(.author.login == "railway-app")
          | .body' \
    2>/dev/null | tail -1)

  # Railway bot links: https://railway.com/project/.../deployments/...
  # or preview domains: https://<service>-pr-<N>.<custom>.up.railway.app
  PREVIEW_URL=$(echo "$RAILWAY_COMMENT" \
    | grep -oP 'https://[a-zA-Z0-9\-]+\.up\.railway\.app[^\s"<)]*' | head -1)

  # Fallback — direct railway.com deployment link
  if [ -z "$PREVIEW_URL" ]; then
    PREVIEW_URL=$(echo "$RAILWAY_COMMENT" \
      | grep -oP 'https://railway\.com/project/[^\s"<)]+' | head -1)
  fi
done

if [ -z "$PREVIEW_URL" ]; then
  _log "$RUN_ID" "dev" "$TICKET_N" "deploy_preview" "warning" \
    "Railway URL not found after ${MAX_WAIT}s — smoke test skipped" '{}'
fi
```

## Smoke test

Pass `PREVIEW_URL` to `smoke_test_routes()` in `ci-discipline.md`.

## Notes

- "Preview Environments" must be enabled in the Railway project dashboard
- If not enabled, `PREVIEW_URL` will be empty → smoke test skipped (non-blocking)
- First Railway deploy on a PR can take 2–5 min depending on build size
- Use `platform: railway` (not `railway-auto`) if you want explicit MCP-triggered deploys
