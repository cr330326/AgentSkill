---
name: git-workflow
description: "Gitflow branching model with conventional commits, branch naming, PR templates, and release tagging. Use when: creating branches, writing commit messages, opening PRs, tagging releases, or managing hotfixes."
---

# Git Workflow Management

Enforce a gitflow-like branching model with consistent naming, conventional commits, and structured releases.

## Branch Model

| Branch | Pattern | Source | Merges Into |
|---|---|---|---|
| Main | `main` | — | — |
| Develop | `develop` | `main` | `main` (via release) |
| Feature | `feature/<ticket>-<short-desc>` | `develop` | `develop` |
| Release | `release/<semver>` | `develop` | `main` + `develop` |
| Hotfix | `hotfix/<ticket>-<short-desc>` | `main` | `main` + `develop` |

### Branch naming rules

- Lowercase, hyphen-delimited. No underscores, no uppercase.
- `<ticket>` = issue/ticket ID (e.g. `GH-42`, `JIRA-1337`). Omit if no tracker.
- `<short-desc>` = 2-4 words max (e.g. `add-login-page`).
- Examples: `feature/GH-42-add-login-page`, `hotfix/GH-99-fix-null-crash`, `release/2.1.0`.

## Conventional Commits

Every commit message MUST follow this format:

```
<type>(<scope>): <subject>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, whitespace (no logic change) |
| `refactor` | Code change that neither fixes nor adds |
| `perf` | Performance improvement |
| `test` | Adding or updating tests |
| `build` | Build system or dependencies |
| `ci` | CI configuration |
| `chore` | Maintenance tasks |

### Rules

1. `<subject>`: imperative mood, lowercase, no period. Max 72 chars.
2. `<scope>`: optional, names the module/area (e.g. `auth`, `api`, `ui`).
3. Breaking changes: add `!` after type/scope AND a `BREAKING CHANGE:` footer.
4. Body: wrap at 100 chars. Explain *what* and *why*, not *how*.

### Examples

```
feat(auth): add OAuth2 login flow

Integrates Google and GitHub providers via passport.js.

Refs: GH-42
```

```
fix(api)!: remove deprecated /v1/users endpoint

BREAKING CHANGE: /v1/users has been removed. Use /v2/users instead.
```

## Pull Request Workflow

### PR title

Must match conventional commit format: `<type>(<scope>): <subject>`

### PR template

When the user asks to create a PR or needs a PR description, use this structure:

```markdown
## Summary
<!-- 1-3 sentences: what and why -->

## Changes
- <!-- Bullet list of concrete changes -->

## Type
- [ ] feat
- [ ] fix
- [ ] refactor
- [ ] docs
- [ ] chore

## Testing
- [ ] Unit tests added/updated
- [ ] Manual testing performed
<!-- Describe what was tested -->

## Breaking Changes
<!-- None, or describe impact and migration -->

## Related
<!-- GH-42, closes #42, etc. -->
```

### PR rules

- Feature branches: PR into `develop`.
- Release branches: PR into `main` (and back-merge to `develop` after).
- Hotfix branches: PR into `main` (and back-merge to `develop` after).
- Require at least 1 approval before merge.
- Squash-merge features. Merge-commit for releases and hotfixes (preserves history).

## Release Tagging

### Creating a release

1. Branch: `git checkout -b release/<version> develop`
2. Bump version in project files (package.json, pyproject.toml, etc.).
3. Commit: `chore(release): bump version to <version>`
4. PR into `main`. After merge:
   - Tag: `git tag -a v<version> -m "Release v<version>"`
   - Push: `git push origin v<version>`
   - Back-merge `main` into `develop`.

### Tag format

- Always prefixed with `v`: `v1.0.0`, `v2.3.1`.
- Follow semver strictly: `MAJOR.MINOR.PATCH`.
- Pre-releases: `v1.0.0-rc.1`, `v1.0.0-beta.2`.

### Hotfix release

1. Branch: `git checkout -b hotfix/<ticket>-<desc> main`
2. Fix, commit, PR into `main`.
3. After merge: tag with bumped PATCH version.
4. Back-merge `main` into `develop`.

## Quick Reference Commands

```bash
# Start feature
git checkout develop && git pull && git checkout -b feature/<ticket>-<desc>

# Start release
git checkout develop && git pull && git checkout -b release/<version>

# Start hotfix
git checkout main && git pull && git checkout -b hotfix/<ticket>-<desc>

# Tag release (after merge to main)
git checkout main && git pull && git tag -a v<version> -m "Release v<version>" && git push origin v<version>
```
