---
name: ticket
description: |
  Load a GitHub ticket by number or partial title and discuss it with fresh context.

  Use this when you want to discuss a specific ticket with the team-lead bot before processing it.
  Say /ticket #5 or /ticket "Feature name" to load the ticket, confirm it's the right one, and discuss.

  This loads the ticket's current state from GitHub (fresh data) and prepares for inline discussion
  or to trigger enrichment/dev workflows.
---

# /ticket — Load and discuss a GitHub ticket

Load a GitHub ticket with fresh context from GitHub. Perfect for discussing with the team-lead before enrichment, or checking the current state of a ticket.

## Usage

```
/ticket #5
/ticket "Feature name"
/ticket enrichment  # Load first N tickets with "to-enrich" label
```

## What this does

1. **Fetches the ticket** from GitHub (fresh data)
2. **Confirms which ticket** you meant
3. **Shows full context**: title, body, recent comments, current labels
4. **Positions as team-lead** so you can discuss directly here
5. When you say "ok, enrichis", posts to GitHub and changes labels automatically

## Example

```
You: /ticket #5

Ticket loaded: "Feature: Improved search filtering" (#5)

Labels: to-enrich
Status: Ready to enrich

Body:
---
As a user, I want to filter search results by date range so I can find older articles.

Current behavior: No date filtering
Proposed: Add date range picker to search form
---

Shall we discuss this one? Any questions before enrichment?
```

Then you discuss, ask questions, or say "ok enrichis le ticket" to trigger enrichment automatically.

## Implementation

The skill:
1. Parses the input (number or title)
2. Uses `gh issue view` to fetch the ticket
3. Confirms with you which ticket
4. Displays the content
5. Positions Claude as team-lead ready to discuss
6. When you approve, it enriches via the automated workflow
