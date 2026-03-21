---
name: cao-save-session
description: Summarize the current session, update CLAUDE.md and memory files if needed. Use at the end of a work session to persist context for future conversations.
allowed-tools: [Read, Edit, Write, Glob, Grep]
---

# /cao-save-session — End of session context persistence

Role: maintain project context up-to-date for future conversations.

## Step 1 — Identify what changed

1. Base on the current conversation: files read, edited, created, or discussed.
2. Do not use git to identify changes — git management is handled separately.
3. Read the project's CLAUDE.md (if it exists at root) to understand the currently documented state.
4. Read memory files in `~/.claude/projects/*/memory/` for the current project.

## Step 2 — Summarize the session

Produce a concise summary:
- Files created or modified (and why)
- Technical or product decisions made
- Bugs resolved
- New features added
- What remains to do (if mentioned)

## Step 3 — Update CLAUDE.md if justified

Update CLAUDE.md **only** if one of these conditions is true:
- A new phase was completed (e.g. Phase 3 → 4)
- A new API or external dependency was added
- A significant new code pattern was established
- A critical file was added or renamed
- An important constraint was identified (e.g. "never do X")
- Startup commands changed

If none of these conditions is true, do not modify CLAUDE.md.

## Step 4 — Update memory files if justified

For each memory type, update or create a file **only** if:

**type: project** → a product decision was made, an objective changed, a phase started/ended, a deadline constraint exists

**type: feedback** → user corrected your approach ("no, not like that"), or validated a non-obvious approach ("yes exactly, keep doing that")

**type: user** → you learned something about the user's role, preferences, or technical level

**type: reference** → an external system (Linear, Grafana, Notion, Slack channel) was mentioned as source of truth

If you create a new memory file, also add a pointer in `MEMORY.md`.

Memory file format:
```markdown
---
name: Short name
description: One line — used to decide relevance in future conversations
type: project|feedback|user|reference
---

Main content.

**Why:** Reason or context.

**How to apply:** When and how to apply this memory.
```

## Step 5 — Display the summary

```
## Session Summary

### What was done
[short list]

### Updates made
- CLAUDE.md: [updated / not modified — why]
- Memories: [list of files created/modified, or "no updates needed"]

### For next session
[optional: what remains to do if clearly identified]
```

If nothing warrants an update (light session, exploration without decisions), say so clearly and don't modify anything.
