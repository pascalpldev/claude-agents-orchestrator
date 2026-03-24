---
name: deploy-profile-railway
description: Deploy preview via Railway MCP — trigger deploy, get URL directly without polling.
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

# Get the preview URL
# mcp__railway-mcp-server__generate-domain
#   project: $RAILWAY_PROJECT
#   service: $RAILWAY_SERVICE
# → PREVIEW_URL
```

## URL retrieval

The URL is provided **directly** by the MCP (`generate-domain`) — no polling required.

```bash
# PREVIEW_URL is available immediately after generate-domain
# Post to the ticket:
gh issue comment "$TICKET_N" --repo "$OWNER/$REPO" \
  --body "Preview deployed: $PREVIEW_URL"
```

## Smoke test

URL available immediately → no waiting. Proceed directly to `smoke_test_routes()` in `ci-discipline.md`.

```bash
# PREVIEW_URL already set — smoke test can run without delay
SMOKE_WAIT=0
```

## Rollback if smoke test fails

Railway MCP does not support automatic rollback of a preview service — the ticket is simply reset to `to-dev`. The PR remains open for investigation.
