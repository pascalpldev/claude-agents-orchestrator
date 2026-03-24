---
name: deploy-profile-railway
description: Deploy preview via Railway MCP — trigger deploy, poll until SUCCESS, then get URL.
platform: railway
url_source: mcp-direct
---

# Deploy Profile — Railway

## Deploy

Uses the Railway MCP to trigger the deploy of the feature branch.

```bash
# Read from cao.config.yml:
# deploy.project → RAILWAY_PROJECT
# deploy.service → RAILWAY_SERVICE

# Trigger via MCP
# mcp__railway-mcp-server__deploy
#   project: $RAILWAY_PROJECT
#   service: $RAILWAY_SERVICE
# → returns DEPLOYMENT_ID
```

## Wait for deployment to complete

`generate-domain` returns the service URL immediately, but the new deployment
may still be building. Always wait for the deployment to reach `SUCCESS` before
running the smoke test — otherwise the test may hit the previous version.

```bash
MAX_WAIT=${SMOKE_TIMEOUT_S:-300}
POLL_INTERVAL=15
ELAPSED=0
DEPLOY_STATUS=""

while [ "$DEPLOY_STATUS" != "SUCCESS" ] && [ "$DEPLOY_STATUS" != "FAILED" ] \
      && [ $ELAPSED -lt $MAX_WAIT ]; do
  sleep $POLL_INTERVAL
  ELAPSED=$((ELAPSED + POLL_INTERVAL))

  # mcp__railway-mcp-server__list-deployments
  #   project: $RAILWAY_PROJECT
  #   service: $RAILWAY_SERVICE
  # → read latest deployment status → DEPLOY_STATUS
done

if [ "$DEPLOY_STATUS" = "FAILED" ]; then
  _log "$RUN_ID" "dev" "$TICKET_N" "deploy_preview" "error" \
    "Railway deployment failed" "{\"elapsed\":$ELAPSED}"
  gh issue comment "$TICKET_N" --repo "$OWNER/$REPO" \
    --body "❌ Railway deployment failed — check Railway logs. Ticket reset to \`to-dev\`."
  gh issue edit "$TICKET_N" --repo "$OWNER/$REPO" \
    --remove-label "dev-in-progress" --add-label "to-dev"
  exit 1
fi

if [ "$DEPLOY_STATUS" != "SUCCESS" ]; then
  _log "$RUN_ID" "dev" "$TICKET_N" "deploy_preview" "warning" \
    "Railway deployment timeout after ${MAX_WAIT}s — smoke test skipped" '{}'
  PREVIEW_URL=""
fi
```

## URL retrieval

Only fetch the URL after the deployment is confirmed `SUCCESS`.

```bash
if [ "$DEPLOY_STATUS" = "SUCCESS" ]; then
  # mcp__railway-mcp-server__generate-domain
  #   project: $RAILWAY_PROJECT
  #   service: $RAILWAY_SERVICE
  # → PREVIEW_URL

  gh issue comment "$TICKET_N" --repo "$OWNER/$REPO" \
    --body "Preview deployed: $PREVIEW_URL"
fi
```

## Smoke test

`PREVIEW_URL` is set only after `SUCCESS` → smoke test runs against the freshly
deployed version. Pass `PREVIEW_URL` to `smoke_test_routes()` in `ci-discipline.md`.

## Rollback if smoke test fails

Railway MCP does not support automatic rollback of a preview service — the ticket
is simply reset to `to-dev`. The PR remains open for investigation.
