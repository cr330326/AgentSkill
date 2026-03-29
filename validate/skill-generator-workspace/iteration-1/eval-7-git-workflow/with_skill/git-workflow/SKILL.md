---
name: git-workflow
description: >
  Enforce gitflow-like branching, conventional commit messages, PR descriptions,
  and semantic release tags. Covers branch naming, commit formatting, PR templates,
  and version tagging. Use when user says "create branch", "format commit",
  "write PR description", "tag release", "hotfix", "what branch should I use",
  or asks about branching strategy. Do NOT use for CI/CD pipeline configuration,
  GitHub Actions workflows, or repository hosting setup.
---

# Git Workflow

A lean reference for gitflow-like branching with conventional commits.

## Branch Naming

| Type | Pattern | Example | Branches from | Merges into |
|------|---------|---------|---------------|-------------|
| Feature | `feature/<ticket>-<slug>` | `feature/PROJ-42-user-auth` | `develop` | `develop` |
| Bugfix | `bugfix/<ticket>-<slug>` | `bugfix/PROJ-99-null-check` | `develop` | `develop` |
| Release | `release/<version>` | `release/2.1.0` | `develop` | `main` + `develop` |
| Hotfix | `hotfix/<version>-<slug>` | `hotfix/2.1.1-crash-fix` | `main` | `main` + `develop` |

Rules:
- Use lowercase, hyphens only — no underscores or uppercase.
- Always include the ticket ID when one exists.
- Keep the slug to 3-5 words max.

## Conventional Commits

Format: `<type>(<scope>): <subject>`

```
feat(auth): add OAuth2 login flow
fix(api): handle null response from payment gateway
docs(readme): update installation steps
refactor(db): extract connection pool into module
test(auth): add unit tests for token refresh
chore(deps): bump express to 4.19.2
```

| Type | When to use | Bumps |
|------|-------------|-------|
| `feat` | New user-facing functionality | MINOR |
| `fix` | Bug fix | PATCH |
| `docs` | Documentation only | — |
| `refactor` | Code change with no behavior change | — |
| `test` | Adding or updating tests | — |
| `chore` | Tooling, deps, config | — |
| `perf` | Performance improvement | PATCH |
| `ci` | CI/CD config changes | — |

Rules:
- Subject: imperative mood, lowercase, no period, max 72 chars.
- Body (optional): wrap at 80 chars, explain *why* not *what*.
- Footer: `BREAKING CHANGE: <description>` triggers a MAJOR bump.
- Footer: `Closes #<issue>` or `Refs PROJ-<ticket>` to link issues.

## PR Description

Use this structure when writing or reviewing PR descriptions:

```markdown
## What
<!-- One-sentence summary of the change -->

## Why
<!-- Problem or motivation — link the ticket -->

## How
<!-- Brief technical approach — what the reviewer should focus on -->

## Testing
<!-- How this was verified — commands, screenshots, test names -->

## Checklist
- [ ] Tests pass locally
- [ ] No unresolved TODOs introduced
- [ ] Conventional commit message on squash/merge
```

Keep the PR focused on a single concern. If the diff exceeds ~400 lines, consider splitting.

## Release Tagging

Sequence for a release:

1. Create `release/<version>` from `develop`.
2. Apply only bug fixes on the release branch — no new features.
3. When ready, merge into `main` AND back into `develop`.
4. Tag `main` with the version:

```bash
git tag -a v<MAJOR>.<MINOR>.<PATCH> -m "Release v<MAJOR>.<MINOR>.<PATCH>"
git push origin v<MAJOR>.<MINOR>.<PATCH>
```

Hotfix sequence:

1. Create `hotfix/<version>-<slug>` from `main`.
2. Fix, commit, bump patch version.
3. Merge into `main` AND `develop`.
4. Tag `main`.

Version decision:

| Condition | Bump |
|-----------|------|
| `BREAKING CHANGE` in any commit since last tag | MAJOR |
| Any `feat` commit since last tag | MINOR |
| Only `fix`, `perf`, `chore`, etc. | PATCH |

## Quick Reference Commands

```bash
# Start a feature
git checkout develop && git pull
git checkout -b feature/PROJ-42-user-auth

# Finish a feature (squash merge preferred)
git checkout develop && git merge --squash feature/PROJ-42-user-auth
git commit -m "feat(auth): add OAuth2 login flow"

# Start a release
git checkout develop && git checkout -b release/2.1.0

# Finish a release
git checkout main && git merge --no-ff release/2.1.0
git tag -a v2.1.0 -m "Release v2.1.0"
git checkout develop && git merge --no-ff release/2.1.0

# Hotfix
git checkout main && git checkout -b hotfix/2.1.1-crash-fix
# ... fix and commit ...
git checkout main && git merge --no-ff hotfix/2.1.1-crash-fix
git tag -a v2.1.1 -m "Release v2.1.1"
git checkout develop && git merge --no-ff hotfix/2.1.1-crash-fix
```
