---
name: git-discipline
description: Git best practices — atomic commits, conventions, branch hygiene, worktree
scope: dev persona (always)
reference: Conventional Commits 1.0 (conventionalcommits.org), Git Book (Chacon & Straub)
---

# Git Discipline

## Atomic commits

One commit = one coherent logical change. Neither too small (not one commit per line), nor too large (not "implement everything").

**Split if**:
- The commit description requires "and" → two commits
- A reviewer might want to revert part of it without the other → two commits
- A doc file changes independently from code → separate commit

**Do not split if**:
- The test and the code it tests → same commit
- The migration and the model it supports → same commit
- A preparatory refactor and its usage → same commit if inseparable

## Commit message format

```
<type>(<scope>): <imperative description, present tense, lowercase>

[optional body — the WHY, not the how]

[optional footer — Closes #N, BREAKING CHANGE: ...]
```

**Types** (Conventional Commits):

| Type | When |
|------|------|
| `feat` | New visible feature |
| `fix` | Bug fix |
| `refactor` | Restructuring without behavior change |
| `test` | Adding or fixing tests only |
| `docs` | Documentation only (CLAUDE.md, README) |
| `chore` | Config, tooling, dependencies — no prod code |
| `perf` | Performance optimization |

**Rules**:
- Description in imperative: "add", "fix", "remove" — not "added", "fixes", "removed"
- Lowercase, no trailing period
- 72 characters max on the first line
- The body explains *why* the change, not *what it does* (the diff shows that)
- `Closes #N` in the footer automatically links the commit to the GitHub ticket

**Examples**:
```
feat(auth): add JWT refresh token rotation

Prevents token replay attacks by invalidating the previous token
on each refresh. Required by security audit finding SEC-12.

Closes #42
```
```
fix(api): return 404 instead of 500 on missing resource
```
```
refactor(db): extract query builder from UserService
```

## Branch hygiene

**Naming** (already defined in dev.md): `feat/ticket-<N>-<short-name>`

**Keep the branch up to date** — before opening the PR and if the branch has been open > 2 days:
```bash
git fetch origin
git rebase origin/dev
# If conflicts: resolve, then git rebase --continue
```

Prefer `rebase` over `merge` to maintain a linear history on feature branches.

**Never** rebase a shared branch (where multiple agents/people have pushed).

**After the PR is merged**: delete the local and remote branch:
```bash
git checkout dev
git pull origin dev
git branch -d feat/ticket-<N>-<short-name>
# The remote branch is deleted automatically if "delete branch on merge" is enabled on GitHub
```

## Pre-commit checklist

Before each `git commit`, verify:

- [ ] `git diff --staged` reviewed — no debug files, no `.env`, no secrets
- [ ] No `console.log`, `print()`, `debugger`, unintentional `TODO` in the staged diff
- [ ] Staged files are consistent with the commit description
- [ ] Tests pass (`npm test` / `pytest` / equivalent)
- [ ] No lock files (`.lock`) or generated files committed by mistake

```bash
# Always stage explicitly — never git add .
git add src/specific/file.py tests/test_specific.py
git diff --staged  # mandatory review
git commit -m "..."
```

## Stash — limited use

Use `git stash` only for a quick context switch (< 30 min). For any longer work: create a WIP branch.

```bash
git stash push -m "wip: short description"
# ... context switch ...
git stash pop
```

Never leave a stash > 24h. If the work in progress has value: WIP commit on a branch.

## Worktree — when to use it

`git worktree` allows working on multiple branches simultaneously in separate directories, without `git stash` or `git checkout`.

**Use when**:
- A critical bug arrives while a feature is in progress (hotfix without touching the feature branch)
- Two independent tickets need to progress in parallel
- Checking the behavior of the `dev` branch while working on `feat/...`

```bash
# Create a worktree for a hotfix
git worktree add ../repo-hotfix fix/critical-bug-<N>

# Work in the worktree
cd ../repo-hotfix
# ... implement, commit, push ...

# Remove the worktree when done
cd ../repo-main
git worktree remove ../repo-hotfix
```

**Do not use** for the normal ticket-by-ticket flow — worktree is a parallelism tool, not a default habit.
