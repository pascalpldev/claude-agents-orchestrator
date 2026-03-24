---
name: cao-get-ticket
description: |
  Load a GitHub ticket by number or partial title and discuss it with fresh context.

  Use this when you want to discuss a specific ticket with the chief-builder before processing it.
  Say /cao-get-ticket #5 or /cao-get-ticket "Feature name" to load the ticket, confirm it's the right one, and discuss.

  This loads the ticket's current state from GitHub (fresh data) and prepares for inline discussion
  or to trigger enrichment/dev workflows.
argument-hint: <ticket-number-or-title>
allowed-tools: [Read, Glob, Grep, Bash]
---

# /cao-get-ticket — Load and discuss a GitHub ticket

Load a GitHub ticket with fresh context from GitHub. Perfect for discussing with the chief-builder before enrichment, or checking the current state of a ticket.

## Usage

```
/cao-get-ticket #5
/cao-get-ticket "Feature name"
/cao-get-ticket enrichment  # Load first N tickets with "to-enrich" label
```

## What this does

1. **Detect current project** from `git remote get-url origin` — extract OWNER and REPO
2. **Fetch the ticket** using `gh` CLI:
   - If argument is `#N` or a number: `gh issue view N --repo OWNER/REPO --json number,title,body,labels,comments,assignees`
   - If argument is a label name (e.g. "enrichment"): `gh issue list --repo OWNER/REPO --label <label> --json number,title,labels`
   - If argument is a text search: `gh issue list --repo OWNER/REPO --search "<text>" --json number,title,labels`
3. **Confirm which ticket** if ambiguous
4. **Show full context**: title, body, recent comments, current labels
5. **Position as chief-builder** ready to discuss
6. When you say "ok, enrich it", trigger enrichment via the automated workflow

## Implementation

1. Parse the input: `$ARGUMENTS`
2. Detect OWNER/REPO from `git remote get-url origin`
3. Fetch ticket via `gh issue view` or `gh issue list`
4. Display content
5. Position Claude as chief-builder ready to discuss
6. When approved, trigger enrichment via the automated workflow

## Example

```
You: /cao-get-ticket #5

Ticket loaded: "Feature: Improved search filtering" (#5)

Labels: to-enrich
Status: Ready to enrich

Body:
---
As a user, I want to filter search results by date range.
---

Shall we discuss this one? Any questions before enrichment?
```

Then you discuss, ask questions, or say "ok, enrich the ticket" to trigger enrichment automatically.
