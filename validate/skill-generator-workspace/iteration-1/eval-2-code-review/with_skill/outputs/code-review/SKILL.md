---
name: code-review
description: >
  Review pull requests and code changes with the rigor of a senior engineer, covering code quality,
  security vulnerabilities, performance issues, and style consistency. Use this skill when the user
  wants a code review, asks to "review this PR", "review my code", "check this diff", "look at my
  changes", "review pull request", "code review", or provides a GitHub PR URL for feedback. Also
  use when the user asks "what's wrong with this code", "is this code safe", "any issues with this",
  or wants feedback on code quality before merging. Triggers on any request to evaluate, critique,
  or improve existing code changes. Do NOT use for writing new code from scratch (use relevant dev
  skills instead), refactoring existing code (use code-refactoring), or running automated tests
  (use testing-strategies).
---

# Code Review

Review code changes like a senior engineer -- catching bugs, security holes, performance traps,
and style inconsistencies before they reach production.

## Core principles

Good code review is not about gatekeeping. It serves three purposes:

1. **Catch defects early** -- bugs, security issues, and performance problems are orders of magnitude
   cheaper to fix before merge than after deployment.
2. **Share knowledge** -- reviews spread understanding of the codebase across the team and help the
   author learn patterns they may not have considered.
3. **Maintain consistency** -- a codebase that reads like it was written by one person is easier to
   maintain than one where every file has a different style.

Balance thoroughness with respect for the author's time. Focus on what matters: correctness,
security, and maintainability. Avoid bikeshedding on trivial preferences.

## Workflow

### Step 1: Gather context

Before reviewing line-by-line, understand the big picture:

1. Read the PR title, description, and any linked issues to understand **intent**.
2. Run `git diff` (or `gh pr diff <number>`) to get the full changeset.
3. Identify the **scope**: Is this a feature, bug fix, refactor, config change, or dependency update?
4. Note the **blast radius**: Which components, services, or modules are touched?
5. Check the size -- if the PR modifies more than ~400 lines of logic (excluding tests, generated
   files, and lock files), flag it as too large and suggest splitting.

### Step 2: Correctness review

This is the highest-priority pass. A correct PR that's ugly is better than an elegant PR that's wrong.

Check for:

- **Logic errors** -- off-by-one, wrong comparison operators, inverted conditions, missing edge cases
- **Null/undefined handling** -- unguarded property access, missing null checks, optional chaining gaps
- **Error handling** -- uncaught exceptions, swallowed errors, missing error propagation
- **Race conditions** -- concurrent access to shared state, missing locks or atomic operations
- **State management** -- stale closures, incorrect dependency arrays (React), mutation of shared state
- **Type safety** -- implicit any, incorrect type assertions, mismatched generics
- **API contract mismatches** -- request/response shape differences between client and server
- **Boundary conditions** -- empty arrays, zero values, maximum integer, Unicode edge cases

**Example finding:**
```
File: src/services/user.ts:47
Issue: `users.find(u => u.id === id)` returns undefined when no match,
but line 48 accesses `.name` without a null check.
Severity: Bug
Suggestion: Add a guard: `if (!user) throw new NotFoundError('User not found')`
```

### Step 3: Security review

Treat every PR as if an attacker will read the code. Check for:

- **Injection** -- SQL injection (string concatenation in queries), XSS (unescaped user input in HTML),
  command injection (user input in shell commands), template injection
- **Authentication/Authorization** -- missing auth checks on endpoints, broken access control,
  privilege escalation paths, JWT validation gaps
- **Secrets** -- hardcoded API keys, tokens, passwords, or connection strings; secrets in logs
- **Data exposure** -- sensitive fields (passwords, SSNs, tokens) in API responses, logs, or error messages
- **Dependency risks** -- new dependencies with known CVEs, overly broad permissions, typosquatting risk
- **Input validation** -- missing or insufficient validation on user-supplied data, especially at API boundaries
- **Cryptography** -- weak algorithms (MD5/SHA1 for security), custom crypto implementations,
  insufficient randomness

Refer to `references/security-checklist.md` for the OWASP-derived checklist.

**Severity levels for security findings:**
| Level | Meaning | Action |
|-------|---------|--------|
| Critical | Exploitable vulnerability, data breach risk | Block merge |
| High | Significant weakness, needs attacker + conditions | Block merge |
| Medium | Defense-in-depth gap, unlikely exploit path | Fix before or soon after merge |
| Low | Informational, hardening opportunity | Track for future improvement |

### Step 4: Performance review

Not every PR needs a performance pass. Focus here when the change involves:
- Hot paths (request handlers, loops over large datasets, rendering pipelines)
- Database queries (N+1 patterns, missing indexes, unbounded selects)
- Memory-sensitive code (caching, streaming, large object allocation)
- Network calls (unnecessary round trips, missing batching)

Check for:

- **N+1 queries** -- database call inside a loop instead of batch/join
- **Unbounded operations** -- `SELECT *` without LIMIT, loading entire collections into memory
- **Missing pagination** -- endpoints returning unbounded result sets
- **Unnecessary computation** -- recalculating derived values, redundant API calls
- **Cache misuse** -- caching mutable data, missing invalidation, unbounded cache growth
- **Blocking operations** -- synchronous I/O on async paths, heavy computation on main thread
- **Bundle impact** -- large new dependencies for simple tasks, tree-shaking blockers
- **Algorithm complexity** -- O(n^2) or worse when O(n log n) alternatives exist

**Example finding:**
```
File: src/api/orders.ts:82
Issue: Fetching user details inside a loop over orders creates an N+1 query pattern.
       With 1000 orders, this generates 1001 database queries.
Severity: Performance / High
Suggestion: Batch-fetch all unique user IDs before the loop:
  const userIds = [...new Set(orders.map(o => o.userId))];
  const users = await userRepo.findByIds(userIds);
```

### Step 5: Style and maintainability review

This is the lowest-priority pass. Only flag style issues that genuinely hurt readability or
maintainability -- avoid subjective nitpicks. Defer to the project's existing conventions and
any configured linter/formatter rules.

Check for:

- **Naming** -- misleading variable/function names, single-letter names outside tight loops,
  acronyms without context, names that don't match behavior
- **Complexity** -- functions over ~40 lines, deeply nested conditionals (>3 levels),
  god objects, feature envy
- **Duplication** -- copy-pasted logic that should be extracted, repeated patterns across files
- **Dead code** -- commented-out code, unreachable branches, unused imports/variables
- **Documentation gaps** -- public APIs without doc comments, complex algorithms without explanation,
  non-obvious "why" decisions without inline comments
- **Test coverage** -- new logic paths without corresponding tests, test names that don't describe behavior
- **File organization** -- overly large files, misplaced code, circular dependencies

### Step 6: Compose the review

Structure the review output for clarity and actionability:

```markdown
## Review Summary

**PR:** [title or number]
**Scope:** [feature | bugfix | refactor | config | deps]
**Risk:** [low | medium | high]
**Verdict:** [approve | approve with comments | request changes | block]

### Critical Issues (must fix before merge)
- [Finding with file:line, explanation, and suggested fix]

### Recommendations (should fix, but non-blocking)
- [Finding with file:line, explanation, and suggested fix]

### Nits (optional improvements)
- [Minor suggestions]

### Positive Observations
- [What the author did well -- good patterns, thorough tests, clear naming]
```

Always include positive observations. Reviewing is a collaboration, not an audit.

## Severity classification

Use this table to consistently classify findings:

| Severity | Description | Examples | Action |
|----------|-------------|----------|--------|
| **Blocker** | Breaks functionality or introduces vulnerability | Crash, data loss, SQL injection, auth bypass | Must fix before merge |
| **Major** | Significant issue but not immediately exploitable | Missing error handling, N+1 query, race condition | Should fix before merge |
| **Minor** | Improvement opportunity, no immediate risk | Naming, minor duplication, missing docs | Fix in this PR or follow-up |
| **Nit** | Stylistic preference, trivial | Formatting, import order, comment wording | Author's discretion |

## Language-specific considerations

Adapt your review focus based on the language:

| Language | Extra focus areas |
|----------|------------------|
| **JavaScript/TypeScript** | Prototype pollution, `==` vs `===`, async/await error handling, bundle size, `any` type escape hatches |
| **Python** | Mutable default arguments, exception handling specificity, type hint coverage, import cycles |
| **Go** | Error return handling, goroutine leaks, defer ordering, nil pointer receivers |
| **Rust** | Unsafe blocks justification, lifetime complexity, unwrap/expect in library code |
| **Java/Kotlin** | Null safety, resource leaks (try-with-resources), thread safety, checked exceptions |
| **SQL** | Injection via string building, missing indexes on WHERE/JOIN columns, N+1 patterns |

## Review etiquette

These guidelines help keep reviews constructive:

- **Ask questions instead of making demands** -- "What happens if `items` is empty here?" is better
  than "You forgot to handle the empty case."
- **Distinguish preferences from requirements** -- prefix subjective suggestions with "nit:" or
  "optional:" so the author knows they can disagree.
- **Explain the why** -- "This could cause a memory leak because the event listener is never removed"
  is better than "Remove the event listener."
- **Suggest, don't just criticize** -- include a code snippet or approach when flagging an issue.
- **Acknowledge good work** -- call out clean abstractions, thorough tests, or clever solutions.
- **Keep scope** -- review the code in the PR, not adjacent code the author didn't touch (unless
  the PR introduces a regression in that adjacent code).

## Constraints

- Never approve a PR with known security vulnerabilities of Critical or High severity.
- Flag but do not block on style-only issues unless they violate project-configured linter rules.
- If the PR is too large to review effectively (>800 lines of logic changes), recommend splitting
  it and explain how to divide it logically.
- Always provide actionable suggestions, not just problem descriptions.
- Respect the project's existing patterns even if you'd personally choose a different approach.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| PR diff is too large to parse | Ask the user for specific files to focus on, or review by component |
| No PR description or context | Ask the author about the intent before reviewing; note this as a process issue |
| Unfamiliar language or framework | State your confidence level, focus on universal principles (logic, security), suggest domain-specific review from someone with expertise |
| Conflicting style preferences | Defer to the project's configured linter/formatter; if none exists, suggest adding one |
| Author pushes back on feedback | Distinguish must-fix (bugs, security) from suggestions; be willing to be wrong on style calls |
