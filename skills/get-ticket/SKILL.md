---
name: get-ticket
description: |
  Load a GitHub ticket by number or partial title and discuss it with fresh context.

  Use this when you want to discuss a specific ticket with the team-lead bot before processing it.
  Say /get-ticket #5 or /get-ticket "Feature name" to load the ticket, confirm it's the right one, and discuss.

  This loads the ticket's current state from GitHub (fresh data) and prepares for inline discussion
  or to trigger enrichment/dev workflows.
argument-hint: <ticket-number-or-title>
allowed-tools: [Read, Glob, Grep, Bash]
---

# /get-ticket — Load and discuss a GitHub ticket

Load a GitHub ticket with fresh context from GitHub. Perfect for discussing with the team-lead before enrichment, or checking the current state of a ticket.

## Usage

```
/get-ticket #5
/get-ticket "Feature name"
/get-ticket enrichment  # Load first N tickets with "to-enrich" label
```

## What this does

1. **Detect current project** from `git remote get-url origin` (works with any repo)
2. **Fetch the ticket** from GitHub using `gh issue view` (fresh data)
3. **Confirm which ticket** you meant
4. **Show full context**: title, body, recent comments, current labels
5. **Position as team-lead** so you can discuss directly here
6. When you say "ok, enrichis", post to GitHub and change labels automatically

## Implementation

The skill:
1. Parses the input: `$ARGUMENTS`
2. Detects the current GitHub repo automatically via `git remote`
3. Uses `gh issue view` or `gh issue list` to fetch the ticket(s)
4. Confirms with you which ticket
5. Displays the content
6. Positions Claude as team-lead ready to discuss
7. When you approve, it enriches via the automated workflow

## Example

```
You: /get-ticket #5

Ticket loaded: "Feature: Improved search filtering" (#5)

Labels: to-enrich
Status: Ready to enrich

Body:
---
As a user, I want to filter search results by date range.
---

Shall we discuss this one? Any questions before enrichment?
```

Then you discuss, ask questions, or say "ok enrichis le ticket" to trigger enrichment automatically.
