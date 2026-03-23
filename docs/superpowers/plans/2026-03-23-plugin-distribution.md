# Plugin Distribution Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the circular plugin reference error and automate marketplace registration so `claude-agents-orchestrator` can be publicly distributed with zero-friction installation.

**Architecture:** Three-part fix addresses the root cause (circular marketplace.json reference), automates user setup (SETUP.sh enhancement), and clarifies documentation (README). Changes are backward-compatible and idempotent.

**Tech Stack:** Bash (SETUP.sh), JSON (marketplace.json), jq (JSON manipulation), Markdown (README)

---

## File Structure

| File | Purpose | Change Type |
|------|---------|-------------|
| `.claude-plugin/marketplace.json` | Plugin metadata | Modify: remove `"source"` field |
| `SETUP.sh` | Automated project setup | Modify: add plugin marketplace registration |
| `README.md` | User documentation | Modify: simplify installation instructions |

---

## Task 1: Fix marketplace.json Circular Reference

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Read current marketplace.json**

Run:
```bash
cat .claude-plugin/marketplace.json | jq '.'
```

Expected output: JSON with plugin definition containing `"source"` field.

- [ ] **Step 2: Understand the circular reference**

The `"source"` field in the plugin definition points back to `pascalpldev/claude-agents-orchestrator`, which is the same repository where the marketplace.json exists. This creates confusion in Claude Code's resolver.

Claude Code's resolution logic:
1. If `source` is specified → fetch plugin from that source
2. If `source` is absent → look in current repository
3. Load `.claude-plugin/plugin.json` from resolved location

We're at step 1, which tries to fetch recursively. We need to reach step 2.

- [ ] **Step 3: Create the fixed marketplace.json**

Replace `.claude-plugin/marketplace.json` with:

```json
{
  "$schema": "https://anthropic.com/claude-code/marketplace.schema.json",
  "name": "claude-agents-orchestrator",
  "description": "Automated GitHub ticket management workflow for Claude Code — enrichment, development, testing, and deployment via issue labels and agents",
  "owner": {
    "name": "pascalpldev"
  },
  "plugins": [
    {
      "name": "claude-agents-orchestrator",
      "description": "Automated GitHub ticket management workflow for Claude Code — enrichment, development, testing, and deployment via issue labels and agents",
      "category": "development",
      "homepage": "https://github.com/pascalpldev/claude-agents-orchestrator"
    }
  ]
}
```

Key changes:
- ✅ Removed entire `"source"` object
- ✅ Kept `name`, `description`, `category`, `homepage`
- ✅ Improved description clarity

- [ ] **Step 4: Validate the JSON**

Run:
```bash
cat .claude-plugin/marketplace.json | jq '.' > /dev/null && echo "✓ Valid JSON"
```

Expected: `✓ Valid JSON` (no errors)

- [ ] **Step 5: Verify schema compliance**

Run:
```bash
cat .claude-plugin/marketplace.json | jq '.plugins[0] | keys'
```

Expected output should include: `name`, `description`, `category`, `homepage` (no `source`)

- [ ] **Step 6: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "fix: remove circular source reference from marketplace.json

The plugin source pointing to pascalpldev/claude-agents-orchestrator
created a circular reference since the marketplace itself is in that repo.
Claude Code's resolver now correctly looks for plugin.json in the same repo.

Fixes: Plugin claude-agents-orchestrator not found in marketplace"
```

---

## Task 2: Enhance SETUP.sh to Auto-Register Plugin Marketplace

**Files:**
- Modify: `SETUP.sh`

- [ ] **Step 1: Read current SETUP.sh**

Run:
```bash
cat SETUP.sh
```

Understand the current structure:
- It creates GitHub labels
- It creates/switches to dev branch
- It displays a success message

We're adding a new section before the success message.

- [ ] **Step 2: Add plugin marketplace registration function**

Insert this function before the main execution block (before the section that runs the label creation):

```bash
# Register plugin marketplace in user's global Claude Code settings
register_plugin_marketplace() {
  local settings_file="$HOME/.claude/settings.json"
  local marketplace_name="claude-agents-orchestrator"
  local marketplace_config='{
    "source": {
      "source": "github",
      "repo": "pascalpldev/claude-agents-orchestrator"
    }
  }'

  # Create settings file if it doesn't exist
  if [ ! -f "$settings_file" ]; then
    mkdir -p "$(dirname "$settings_file")"
    echo '{"extraKnownMarketplaces": {}}' > "$settings_file"
  fi

  # Check if marketplace is already registered
  if ! grep -q "\"$marketplace_name\"" "$settings_file" 2>/dev/null; then
    # Use jq to safely merge the marketplace config into settings.json
    jq ".extraKnownMarketplaces[\"$marketplace_name\"] = $marketplace_config" "$settings_file" > "$settings_file.tmp" 2>/dev/null

    if [ $? -eq 0 ]; then
      mv "$settings_file.tmp" "$settings_file"
      echo "✓ Plugin marketplace registered in ~/.claude/settings.json"
    else
      rm -f "$settings_file.tmp"
      echo "⚠ Warning: Could not register plugin marketplace (jq might not be installed)"
    fi
  else
    echo "✓ Plugin marketplace already registered"
  fi
}
```

- [ ] **Step 3: Integrate function into main setup flow**

Find the section where labels are created. After label creation and dev branch creation, add this call:

```bash
# Register the plugin marketplace
register_plugin_marketplace
```

Example placement:
```bash
# ... existing label creation code ...

# Create dev branch
git switch -c dev 2>/dev/null || git checkout -b dev

# Register the plugin marketplace (NEW)
register_plugin_marketplace

echo "✓ Setup complete! You're ready to use claude-agents-orchestrator"
```

- [ ] **Step 4: Test the SETUP.sh changes locally**

Create a test directory and run the script:

```bash
mkdir -p /tmp/cao-test
cd /tmp/cao-test
git init
git remote add origin https://github.com/pascalpldev/claude-agents-orchestrator.git
bash /path/to/SETUP.sh
```

Expected output should include:
```
✓ Created label: to-enrich
✓ Created label: enriching
... (other labels)
✓ Plugin marketplace registered in ~/.claude/settings.json
✓ Setup complete!
```

- [ ] **Step 5: Verify settings.json was updated**

Run:
```bash
cat ~/.claude/settings.json | jq '.extraKnownMarketplaces.["claude-agents-orchestrator"]'
```

Expected output:
```json
{
  "source": {
    "source": "github",
    "repo": "pascalpldev/claude-agents-orchestrator"
  }
}
```

- [ ] **Step 6: Test idempotency**

Run SETUP.sh a second time:

```bash
bash /path/to/SETUP.sh
```

Expected: Script should complete without errors, showing "already registered" message.

- [ ] **Step 7: Commit**

```bash
git add SETUP.sh
git commit -m "feat: automate plugin marketplace registration in SETUP.sh

When users run SETUP.sh, the script now automatically registers the
claude-agents-orchestrator plugin marketplace in ~/.claude/settings.json.
This eliminates the need for manual JSON configuration.

The registration is idempotent - safe to run multiple times.
Uses jq for safe JSON manipulation."
```

---

## Task 3: Update README.md Installation Instructions

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Read current README.md**

Run:
```bash
cat README.md | head -100
```

Find the "Installation" section. Current structure:
- Prerequisites
- Step 1a: Add to settings.json
- Step 1b: Run /plugins, search, install
- Step 1c: Verify autocomplete
- Step 2: Set up each project
- Step 3: Create CLAUDE.md

- [ ] **Step 2: Locate the installation section to replace**

The section starts with:
```markdown
### Step 1 — Install the plugin (once, global)

**1a.** Add to `~/.claude/settings.json`:
```

And ends before:
```markdown
### Step 2 — Set up each project (per project)
```

- [ ] **Step 3: Replace with simplified instructions**

Replace the entire "Step 1" section with:

```markdown
### Step 1 — Install the plugin (once, global)

Run this setup script in any Claude Code session:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)
```

This will:
- ✓ Create GitHub labels for the workflow
- ✓ Create and switch to the `dev` branch
- ✓ Register the plugin marketplace globally

Verify — in any Claude Code session, type `/cao-` and the skills should autocomplete.
```

- [ ] **Step 4: Update the "Quickstart" section if it exists**

If there's a Quickstart section, update it to reflect the single setup command:

Before:
```bash
# 1. In your project repo
cd mon-projet
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)

# 2. Create CLAUDE.md at the project root
# 3. Create your first ticket
```

After:
```bash
# 1. Run setup (once per project)
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)

# 2. Create CLAUDE.md at the project root
# 3. Create your first ticket
```

- [ ] **Step 5: Verify README clarity**

Read through the updated section to ensure:
- ✅ Single command (no manual JSON editing)
- ✅ Clear explanation of what setup does
- ✅ Verification step included
- ✅ No references to old manual process

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: simplify plugin installation instructions

Replace multi-step manual setup with automated SETUP.sh command.
Users now run a single command to register the plugin marketplace,
eliminating the need to manually edit ~/.claude/settings.json.

Updates Quickstart and Installation sections."
```

---

## Task 4: Clear Cache and Test Plugin Installation

**Files:**
- None (testing only)

- [ ] **Step 1: Clear Claude Code plugin cache**

Run:
```bash
rm -rf ~/.claude/plugins/cache/claude-agents-orchestrator
rm -rf ~/.claude/plugins/marketplaces/claude-agents-orchestrator
```

Expected: Directories are removed (or didn't exist).

- [ ] **Step 2: Verify settings.json still has marketplace config**

Run:
```bash
cat ~/.claude/settings.json | jq '.extraKnownMarketplaces.["claude-agents-orchestrator"]'
```

Expected: Should show the marketplace configuration.

- [ ] **Step 3: Verify plugin can be discovered**

In Claude Code, press Ctrl+Shift+P (or Cmd+Shift+P on Mac) and type `/plugins`:

Expected behavior:
- `/plugins` command is available
- Searching for `claude-agents-orchestrator` shows the plugin
- Plugin shows as available (not installed, or already installed depending on state)

- [ ] **Step 4: Test skill autocomplete**

In Claude Code, type `/cao-` and wait for autocomplete:

Expected skills to appear:
- `/cao-hello-team-lead`
- `/cao-process-tickets`
- `/cao-get-ticket`
- `/cao-show-logs`
- `/cao-save-session`
- `/cao-worker`
- `/cao-maintain-context`
- `/cao-cancel-loop`

- [ ] **Step 5: Test a basic skill execution**

Run `/cao-hello-team-lead` in Claude Code:

Expected: Skill executes without "Plugin not found in marketplace" error. You should see output about project status.

---

## Task 5: End-to-End Skill Execution Test

**Files:**
- None (integration testing)

**Prerequisites:** Must complete Tasks 1-4. Must have GitHub CLI (`gh`) authenticated and a test GitHub repository.

- [ ] **Step 1: Create a test GitHub repository**

If testing locally, use an existing repo, or create one:

```bash
cd /tmp
mkdir cao-e2e-test
cd cao-e2e-test
git init
git remote add origin https://github.com/YOUR_USERNAME/cao-test.git
```

Or use an existing test repo you have write access to.

- [ ] **Step 2: Run SETUP.sh in test repository**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/pascalpldev/claude-agents-orchestrator/main/SETUP.sh)
```

Expected:
- Labels created
- Dev branch created
- Plugin marketplace registered

- [ ] **Step 3: Create test GitHub issue**

```bash
gh issue create \
  --repo YOUR_USERNAME/cao-test \
  --title "Feature: test CAO plugin distribution" \
  --body "End-to-end test of claude-agents-orchestrator plugin installation and execution" \
  --label "to-enrich"
```

Expected: Issue created with number (e.g., #1).

- [ ] **Step 4: Create CLAUDE.md in test repo**

Create `.github/CLAUDE.md` with:

```markdown
# CAO E2E Test Repository

## Objective
Test the claude-agents-orchestrator plugin distribution and end-to-end skill execution.

## Architecture
Simple test repo with no real code. Used to verify plugin installation works and skills execute correctly.

## Dev Commands
None required for this test.
```

- [ ] **Step 5: In Claude Code, load the ticket**

Run `/cao-get-ticket #1` (or whatever number was assigned):

Expected:
- Ticket loads without errors
- You can see the ticket details
- No "plugin not found" errors

- [ ] **Step 6: Test enrichment**

Run `/cao-process-tickets`:

Expected behavior:
- Agent detects the `to-enrich` labeled ticket
- Agent enriches the ticket (posts a comment with an implementation plan)
- Ticket label changes to `enriched`
- Check GitHub issue — should see enrichment comment with plan

Success indicators:
```
✓ No "Plugin not found in marketplace" errors
✓ Enrichment comment posted to GitHub
✓ Label changed to enriched automatically
```

- [ ] **Step 7: Validate end-to-end execution**

Verify on GitHub:

```bash
gh issue view YOUR_USERNAME/cao-test#1
```

Expected output should show:
- Title: "Feature: test CAO plugin distribution"
- Label: `enriched` (changed from `to-enrich`)
- Comments: At least one enrichment comment from Claude

- [ ] **Step 8: Document test results**

Create a test results file (for reference, not committed):

```
TEST RESULTS - Plugin Distribution Fix
======================================

Date: 2026-03-23
Tester: [Your name]

✅ marketplace.json fix: PASS
   - Removed circular source reference
   - JSON validates correctly

✅ SETUP.sh enhancement: PASS
   - Marketplace registered in settings.json
   - Idempotent (can run multiple times)

✅ README updates: PASS
   - Installation instructions simplified
   - Single command to set up

✅ Plugin installation: PASS
   - Skills autocomplete works
   - No "plugin not found" errors

✅ End-to-end skill execution: PASS
   - /cao-get-ticket loads ticket
   - /cao-process-tickets enriches ticket
   - Label changes automatically
   - Enrichment comment posted to GitHub

Overall Status: READY FOR PUBLIC DISTRIBUTION
```

---

## Summary

| Task | Purpose | Files Changed | Estimated Time |
|------|---------|----------------|-----------------|
| 1 | Fix circular marketplace reference | `.claude-plugin/marketplace.json` | 10 min |
| 2 | Automate plugin registration | `SETUP.sh` | 15 min |
| 3 | Simplify documentation | `README.md` | 10 min |
| 4 | Test plugin caching & discovery | None | 10 min |
| 5 | End-to-end skill execution test | None | 15 min |
| **Total** | | | **~60 minutes** |

---

## Key Principles Applied

- **DRY:** Setup logic centralized in one function
- **YAGNI:** Only removing unnecessary circular reference, not over-engineering
- **TDD:** Tests before implementation where applicable
- **Frequent commits:** Each task commits its changes
- **Idempotent:** SETUP.sh can run safely multiple times

---

## Rollback Plan (if needed)

If issues arise:
1. Revert marketplace.json to include `"source"` field
2. Remove plugin registration from SETUP.sh
3. Revert README to old instructions
4. Clear plugin cache: `rm -rf ~/.claude/plugins/cache/claude-agents-orchestrator`

Command:
```bash
git revert HEAD~2..HEAD
```

---

## Next Steps After Completion

1. Merge to main branch
2. Tag release: `v1.0.0-distribution-fix`
3. Create GitHub release with installation instructions
4. Announce on community channels
5. Monitor issues and gather user feedback
