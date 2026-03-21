# Claude Workflow Kit

**Automated GitHub ticket management with Claude agents.**

Use this kit in any project to automate feature enrichment, development, testing, and deployment.

## Features

- ✅ **Automated enrichment** — Claude plans features (Sonnet)
- ✅ **Automated development** — Claude implements features (Haiku)
- ✅ **Testing support** — You test, agent fixes based on feedback
- ✅ **Auto-merge** — Deploy with a tag
- ✅ **Conversation mode** — Discuss tickets before automation
- ✅ **Feedback loops** — Change labels to redirect agent actions

## Quick Start

```bash
./SETUP.sh "my-project"
```

Then create a ticket:
```bash
gh issue create --title "Feature: ..." --label "to-enrich"
```

Run automation:
```bash
/process-tickets
```

## How It Works

```
Ticket created (to-enrich)
    ↓
Team-lead enriches (plan + details)
    ↓
You validate (change to to-dev)
    ↓
Dev implements (creates branch, posts URL)
    ↓
You test (feedback or tag godeploy)
    ↓
Auto-merge to dev
```

See [CLAUDE.md](./CLAUDE.md) for complete documentation.

## Skills Provided

- **`/hello-team-lead`** — Daily standup
- **`/ticket #N`** — Load a ticket for discussion
- **`/process-tickets`** — Run automation once

## Integration

### As Submodule
```bash
git submodule add https://github.com/pascalpldev/claude-workflow-kit.git .claude-workflow
```

### As Template
```bash
cp -r claude-workflow-kit/* my-project/
```

## Requirements

- Claude Code (with `gh` CLI installed)
- GitHub repo
- Git branches: `main`, `dev`

## License

MIT
