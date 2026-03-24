---
name: git-discipline
description: Bonnes pratiques git — commits atomiques, conventions, branch hygiene, worktree
scope: dev persona (always)
reference: Conventional Commits 1.0 (conventionalcommits.org), Git Book (Chacon & Straub)
---

# Git Discipline

## Commits atomiques

Un commit = un changement logique cohérent. Ni trop petit (pas un commit par ligne), ni trop grand (pas "implement everything").

**Découper si** :
- La description du commit nécessite "and" → deux commits
- Un reviewer pourrait vouloir reverter une partie sans l'autre → deux commits
- Un fichier de doc change indépendamment du code → commit séparé

**Ne pas découper si** :
- Le test et le code qu'il teste → même commit
- La migration et le modèle qu'elle supporte → même commit
- Un refactor préparatoire et son usage → même commit si insécables

## Format des messages de commit

```
<type>(<scope>): <description impérative, présent, minuscule>

[corps optionnel — le POURQUOI, pas le comment]

[footer optionnel — Closes #N, BREAKING CHANGE: ...]
```

**Types** (Conventional Commits) :

| Type | Quand |
|------|-------|
| `feat` | Nouvelle fonctionnalité visible |
| `fix` | Correction de bug |
| `refactor` | Restructuration sans changement de comportement |
| `test` | Ajout ou correction de tests uniquement |
| `docs` | Documentation uniquement (CLAUDE.md, README) |
| `chore` | Config, tooling, dépendances — pas de code prod |
| `perf` | Optimisation de performance |

**Règles** :
- Description en impératif : "add", "fix", "remove" — pas "added", "fixes", "removed"
- Minuscule, pas de point final
- 72 caractères max sur la première ligne
- Le corps explique *pourquoi* le changement, pas *ce qu'il fait* (le diff le montre)
- `Closes #N` en footer lie automatiquement le commit au ticket GitHub

**Exemples** :
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

**Nommage** (déjà défini dans dev.md) : `feat/ticket-<N>-<short-name>`

**Garder la branch à jour** — avant d'ouvrir la PR et si la branch est ouverte > 2 jours :
```bash
git fetch origin
git rebase origin/dev
# Si conflits : résoudre, puis git rebase --continue
```

Préférer `rebase` à `merge` pour garder un historique linéaire sur les branches feature.

**Ne jamais** rebaser une branch partagée (plusieurs agents/personnes y ont pushé).

**Après merge de la PR** : supprimer la branch locale et distante :
```bash
git checkout dev
git pull origin dev
git branch -d feat/ticket-<N>-<short-name>
# La branch distante est supprimée automatiquement si "delete branch on merge" est activé sur GitHub
```

## Pre-commit checklist

Avant chaque `git commit`, vérifier :

- [ ] `git diff --staged` relu — pas de fichier de debug, pas de `.env`, pas de secret
- [ ] Pas de `console.log`, `print()`, `debugger`, `TODO` non intentionnel dans le diff stagé
- [ ] Les fichiers stagés sont cohérents avec la description du commit
- [ ] Les tests passent (`npm test` / `pytest` / équivalent)
- [ ] Pas de fichier de lock (`.lock`) ni de fichier généré commités par erreur

```bash
# Toujours stager explicitement — jamais git add .
git add src/specific/file.py tests/test_specific.py
git diff --staged  # relecture obligatoire
git commit -m "..."
```

## Stash — usage limité

Utiliser `git stash` uniquement pour un contexte switch rapide (< 30 min). Pour tout travail plus long : créer une branch WIP.

```bash
git stash push -m "wip: description courte"
# ... switch de contexte ...
git stash pop
```

Ne jamais laisser un stash > 24h. Si le travail en cours a de la valeur : commit WIP sur une branch.

## Worktree — quand l'utiliser

`git worktree` permet de travailler sur plusieurs branches simultanément dans des répertoires séparés, sans `git stash` ni `git checkout`.

**Utiliser quand** :
- Un bug critique arrive pendant qu'une feature est en cours (hotfix sans toucher la feature branch)
- Deux tickets indépendants doivent avancer en parallèle
- Vérifier le comportement de la branch `dev` pendant qu'on travaille sur `feat/...`

```bash
# Créer un worktree pour un hotfix
git worktree add ../repo-hotfix fix/critical-bug-<N>

# Travailler dans le worktree
cd ../repo-hotfix
# ... implémenter, commiter, pusher ...

# Supprimer le worktree quand terminé
cd ../repo-main
git worktree remove ../repo-hotfix
```

**Ne pas utiliser** pour le flux normal ticket-par-ticket — le worktree est un outil de parallélisme, pas une habitude par défaut.
