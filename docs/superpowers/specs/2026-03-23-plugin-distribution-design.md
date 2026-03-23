# Claude Code Plugin Distribution Design
**Date:** 2026-03-23
**Project:** claude-agents-orchestrator
**Status:** Design Approved

---

## Executive Summary

This document specifies the design for making `claude-agents-orchestrator` properly distributable to the public with zero-friction installation. Users will run a single setup script, and the plugin will be ready to use immediately without manual configuration.

**Key Outcomes:**
- Plugin marketplace configuration error resolved
- Automated plugin registration for users
- Public distribution ready
- End-to-end skill execution validated

---

## Problem Statement

### Current State
The `claude-agents-orchestrator` plugin fails to load with error:
```
Plugin claude-agents-orchestrator not found in marketplace
```

**Root Cause:**
The `.claude-plugin/marketplace.json` contains a self-referential plugin definition:
```json
"source": {
  "source": "github",
  "repo": "pascalpldev/claude-agents-orchestrator"
}
```

This circular reference confuses Claude Code's plugin resolver. When the marketplace itself points back to the same repository as the plugin source, the resolver cannot distinguish between marketplace metadata and plugin metadata.

### User Friction Points
1. Users must manually add marketplace to `~/.claude/settings.json`
2. Marketplace configuration has circular reference
3. Installation instructions are unclear
4. No guarantee that end-to-end skill execution works after installation

---

## Solution Overview

### Two-Part Fix

#### Part 1: Fix Marketplace Metadata (.claude-plugin/marketplace.json)
**Remove the self-referential `"source"` field.**

When a marketplace and plugin live in the same repository, Claude Code automatically resolves the plugin.json from that repository. The explicit source specification is redundant and causes confusion.

**Change:**
```json
// BEFORE
{
  "name": "claude-agents-orchestrator",
  "description": "...",
  "source": {
    "source": "github",
    "repo": "pascalpldev/claude-agents-orchestrator"
  },
  "category": "development",
  "homepage": "https://github.com/pascalpldev/claude-agents-orchestrator"
}

// AFTER
{
  "name": "claude-agents-orchestrator",
  "description": "Automated GitHub ticket management workflow for Claude Code — enrichment, development, testing, and deployment via issue labels and agents",
  "category": "development",
  "homepage": "https://github.com/pascalpldev/claude-agents-orchestrator"
}
```

#### Part 2: Automate Plugin Registration (SETUP.sh Enhancement)
**Automatically register the plugin marketplace in user's global settings.**

When a user runs `SETUP.sh`, the script will:
1. Create GitHub labels (existing)
2. Create/switch to dev branch (existing)
3. **NEW:** Register the plugin marketplace in `~/.claude/settings.json` (if not already registered)

This eliminates the manual configuration step.

---

## Technical Specifications

### File 1: `.claude-plugin/marketplace.json`

**Location:** Repository root, `.claude-plugin/marketplace.json`

**Current Structure:**
```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "claude-agents-orchestrator",
  "description": "Automated GitHub ticket management workflow...",
  "owner": {
    "name": "pascalpldev"
  },
  "plugins": [
    {
      "name": "claude-agents-orchestrator",
      "description": "Automated GitHub ticket management workflow...",
      "source": {
        "source": "github",
        "repo": "pascalpldev/claude-agents-orchestrator"
      },
      "category": "development",
      "homepage": "https://github.com/pascalpldev/claude-agents-orchestrator"
    }
  ]
}
```

**Required Changes:**
- Remove the entire `"source"` object from the plugin definition
- Keep all other fields intact
- Result: Claude Code knows to look in the same repository for plugin.json

**Why This Works:**
Claude Code's plugin resolver uses a precedence hierarchy:
1. If `source` is specified, fetch plugin from that source
2. If `source` is absent, look in current repository (same as marketplace)
3. Load `.claude-plugin/plugin.json` from the resolved location

By removing `source`, we move to step 2 (current repo).

---

### File 2: `SETUP.sh`

**Location:** Repository root, `SETUP.sh`

**New Section to Add:**

```bash
# Register plugin marketplace (if not already registered)
register_plugin_marketplace() {
  local settings_file="$HOME/.claude/settings.json"
  local marketplace_name="claude-agents-orchestrator"
  local marketplace_config='{
    "source": {
      "source": "github",
      "repo": "pascalpldev/claude-agents-orchestrator"
    }
  }'

  if [ ! -f "$settings_file" ]; then
    echo "{\"extraKnownMarketplaces\": {}}" > "$settings_file"
  fi

  if ! grep -q "\"$marketplace_name\"" "$settings_file"; then
    # Use jq to safely merge the marketplace config
    jq ".extraKnownMarketplaces[\"$marketplace_name\"] = $marketplace_config" "$settings_file" > "$settings_file.tmp"
    mv "$settings_file.tmp" "$settings_file"
    echo "✓ Plugin marketplace registered"
  else
    echo "✓ Plugin marketplace already registered"
  fi
}

# Call in main setup flow
register_plugin_marketplace
```

**Dependencies:**
- Requires `jq` for safe JSON manipulation (standard on macOS, available on Linux)
- Gracefully handles missing settings.json
- Idempotent (safe to run multiple times)

**Integration Point:**
Add the call to `register_plugin_marketplace()` after GitHub label creation and before the success message.

---

### File 3: `README.md`

**Update Installation Section:**

**BEFORE:**
```markdown
**1a.** Add to `~/.claude/settings.json`:

```json
{
  "extraKnownMarketplaces": {
    "claude-agents-orchestrator": {
      "source": {
        "source": "github",
        "repo": "pascalpldev/claude-agents-orchestrator"
      }
    }
  }
}
```

**1b.** In any Claude Code session, run `/plugins`, search for `claude-agents-orchestrator`, and install it.

**1c.** Verify — type `/cao-` in any session and the skills should autocomplete.
```

**AFTER:**
```markdown
**Step 1 — Install the plugin (once, global)**

In any Claude Code session, run the setup script:
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)
```

This will:
- ✓ Create GitHub labels
- ✓ Create/switch to dev branch
- ✓ Register the plugin marketplace globally

Verify — type `/cao-` in any Claude Code session and the skills should autocomplete.
```

**Rationale:**
- Single command instead of 3 steps
- Clear output showing what was registered
- No manual JSON editing required

---

## Implementation Workflow

### Step 1: Update marketplace.json
Edit `.claude-plugin/marketplace.json`:
- Remove the `"source"` field from the plugin object in the `"plugins"` array
- Preserve all other fields

### Step 2: Update SETUP.sh
Add the `register_plugin_marketplace()` function and integrate it into the main flow:
1. Create labels (existing)
2. Create dev branch (existing)
3. Register marketplace (new)
4. Display success message

### Step 3: Update README.md
Simplify the installation instructions to reflect the automated setup.

### Step 4: Test End-to-End
1. Clear Claude Code plugin cache: `rm -rf ~/.claude/plugins/cache/claude-agents-orchestrator`
2. Run SETUP.sh in a test project
3. Verify marketplace is registered: `cat ~/.claude/settings.json | grep claude-agents-orchestrator`
4. In Claude Code, type `/cao-` → verify skills autocomplete
5. Create a test GitHub issue with label `to-enrich`
6. Run `/cao-process-tickets` → verify end-to-end execution (agent enriches ticket successfully)

### Step 5: Commit Changes
```bash
git add .claude-plugin/marketplace.json SETUP.sh README.md
git commit -m "fix: resolve plugin distribution by removing circular marketplace reference

- Remove self-referential 'source' from marketplace.json plugin definition
- Enhance SETUP.sh to auto-register plugin marketplace for users
- Update README with simplified installation instructions

Fixes: Plugin claude-agents-orchestrator not found in marketplace"
```

---

## Success Criteria

### Installation Success
- ✅ User runs one command: `bash <(curl -fsSL https://raw...)`
- ✅ No manual configuration required
- ✅ `/cao-` skills autocomplete in Claude Code
- ✅ Skills are callable

### Execution Success
- ✅ `/cao-hello-team-lead` executes without errors
- ✅ `/cao-process-tickets` detects and enriches tickets
- ✅ `/cao-get-ticket #N` loads and displays ticket details
- ✅ All skills complete end-to-end without "plugin not found" errors

### Public Distribution
- ✅ README is clear for new users
- ✅ Setup is automated (no confusing JSON edits)
- ✅ Plugin resolves correctly on first install
- ✅ No caching/resolution errors reported

---

## Testing & Validation

### Manual Testing (Required)
1. **Fresh environment test:**
   - Create new directory
   - Clone repository
   - Run SETUP.sh
   - Verify settings.json is updated
   - Launch Claude Code and verify skills show up

2. **End-to-end skill test:**
   - Create test GitHub issue with `to-enrich` label
   - Run `/cao-process-tickets`
   - Verify agent enriches the ticket successfully
   - Check GitHub for the enrichment comment

3. **Idempotency test:**
   - Run SETUP.sh twice
   - Verify no errors on second run
   - Verify settings.json not duplicated

### Automated Testing (Optional, for future)
- CI check: validate marketplace.json schema
- CI check: validate plugin.json schema
- Integration test: simulate plugin installation and skill invocation

---

## Risk Assessment

### Low Risk
- **Marketplace.json change:** Removing circular reference, standard fix for plugin systems
- **SETUP.sh enhancement:** Uses jq for safe JSON manipulation, idempotent design
- **README update:** Documentation only, no code impact

### Mitigation
- Test on macOS and Linux (jq availability)
- Validate JSON before/after changes
- Manual end-to-end testing before release

---

## Timeline

| Phase | Effort | Duration |
|-------|--------|----------|
| Implement changes | 1 engineer | 30 min |
| Manual testing | 1 engineer | 30 min |
| Documentation review | - | 10 min |
| Commit and release | - | 5 min |
| **Total** | | **~1.5 hours** |

---

## Future Considerations

### Post-Release Monitoring
- Monitor GitHub issues for installation problems
- Track skill execution success rates
- Collect feedback on user experience

### Long-Term Improvements
1. **Publish to official marketplace:** Make it discoverable without custom marketplace registration
2. **CI/CD validation:** Automate schema validation and integration testing
3. **Telemetry:** Track plugin installation and skill usage

---

## Related Documents

- **README.md** — User-facing installation guide
- **.claude-plugin/marketplace.json** — Plugin marketplace metadata
- **SETUP.sh** — Automated project and plugin setup
- **CLAUDE.md** — Project workflow documentation

---

## Approval

- **Designer:** Claude Haiku
- **Date Approved:** 2026-03-23
- **Ready for Implementation:** Yes
