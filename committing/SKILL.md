---
description: Quick git commit with auto-generated or specified message
argument-hint: "[optional: commit message]"
disable-model-invocation: true
allowed-tools: Bash(git status:*), Bash(git add:*), Bash(git commit:*), Bash(git diff:*), Bash(git log:*), Bash(git show:*), Bash(git branch:*)
---

Create a git commit.

If a message is provided: $ARGUMENTS
- Use that as the commit message

If no message is provided:
- Analyze the changes with `git diff --staged` (or `git diff` if nothing staged)
- Generate a concise, meaningful commit message

## Steps

1. Check `git status` to see current state
2. If nothing staged or only partial changes staged:
   - Use `git add -A` to stage ALL changes (including modified, new, and deleted files)
   - If node_modules changes exist, use `git add -A -- . ':!node_modules'` to exclude them
3. Verify all changes are staged with `git status --short`
4. Review what will be committed with `git diff --staged --stat`
5. Create commit:
   - If `$ARGUMENTS` is provided, use it as the message
   - Otherwise, generate a message based on the diff
6. Show the commit result with details

## Commit Message Format

- Start with type: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Be concise but descriptive (max 72 chars for first line)
- Example: `feat: add user authentication with JWT`

## Output Format

After successful commit, show a formatted result:

```
✓ Commit created successfully!

  Branch:    [current branch name]
  Commit:    [short hash] [full hash]
  Message:   [commit message]

  [number] files changed, [insertions], [deletions]
```

Example:
```
✓ Commit created successfully!

  Branch:    main
  Commit:    a1b2c3d a1b2c3d4e5f6...
  Message:   feat: add user authentication

  5 files changed, 120 insertions(+), 15 deletions(-)
```

If commit fails, show the error message clearly.

## Important Notes

- Always use `git add -A` (not `git add .`) to include deleted files
- After staging, verify with `git status --short` that no unstaged changes remain
- If unstaged changes still exist after `git add -A`, report them to user