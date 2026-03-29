---
name: skill-generator
description: >
  Generate well-structured SKILL.md scaffolds and complete skill directory layouts for Claude/OpenCode skills.
  Use this skill whenever the user wants to create a new skill, scaffold a skill, generate a SKILL.md,
  bootstrap a skill project, or says "create skill", "new skill", "skill template", "generate skill",
  "scaffold skill", "skill boilerplate", "make a skill for X", "write a skill".
  Also use when the user has a workflow they want to turn into a reusable skill,
  or asks about skill file structure, frontmatter format, or best practices for writing skills.
  Do NOT use for evaluating or improving existing skills (use skill-creator or skill-evaluator instead).
---

# Skill Generator

Generate production-ready skill scaffolds with correct frontmatter, well-structured instructions,
and the right directory layout -- so every new skill starts from a solid foundation instead of a blank page.

## Why this exists

Writing a skill from scratch means getting the frontmatter format right, figuring out the directory
structure, writing a description that actually triggers correctly, and structuring instructions
so Claude can follow them. This skill encodes all those conventions so you can focus on the
*content* of your skill rather than the *structure*.

## Workflow

### Step 1: Understand what the skill should do

Before generating anything, clarify these four things with the user:

1. **Purpose** -- What should this skill enable Claude to do?
2. **Trigger scenarios** -- What would a user say or do that should activate this skill?
3. **Output** -- What does the skill produce? (files, terminal output, structured text, etc.)
4. **Dependencies** -- Does it need specific tools, CLIs, APIs, or MCP servers?

If the user already described their intent in the conversation, extract answers from context
first and confirm before proceeding.

### Step 2: Choose the right skill pattern

Pick the pattern that best fits the use case:

| Pattern | Best for | Body length | Example |
|---------|----------|-------------|---------|
| **Tool wrapper** | Wrapping a CLI or API | 60-120 lines | tavily-search |
| **Practice guide** | Coding methodology, architecture | 200-500 lines | fullstack-dev, code-refactoring |
| **Process workflow** | Multi-phase creative/build processes | 150-400 lines | skill-creator, mcp-builder |
| **Reference lookup** | Domain knowledge with variants | 80-150 lines + refs | cloud-deploy with per-cloud refs |

### Step 3: Generate the scaffold

Create the skill directory and files. The directory name should be lowercase, hyphenated,
and match the `name` field in frontmatter.

#### Directory structure

```
skill-name/
├── SKILL.md              # Required -- frontmatter + instructions
├── references/            # Optional -- docs loaded on demand (for large reference material)
├── scripts/               # Optional -- executable code for deterministic tasks
└── assets/                # Optional -- templates, icons, fonts used in output
```

Only create subdirectories that the skill actually needs. A simple tool wrapper might only
need SKILL.md with no subdirectories.

#### Frontmatter rules

The YAML frontmatter between `---` fences is the most important part. Two fields are required:

```yaml
---
name: my-skill-name          # Required. Lowercase, hyphenated. Matches directory name.
description: >                # Required. This is the PRIMARY trigger mechanism.
  One sentence saying what it does. Use this skill when the user wants to X, Y, or Z,
  or says "phrase A", "phrase B", "phrase C". Also use when [edge case triggers].
  Do NOT use for [common false-positive scenarios] (use other-skill instead).
---
```

**Writing effective descriptions:**

The description field determines whether Claude invokes your skill. Follow these principles:

- **Start with what it does** (1 sentence): "Generate Docker Compose configurations for multi-service apps."
- **List trigger conditions** with `Use this skill when` or `Use when`: Include both intent-based triggers ("wants to deploy") and phrase-based triggers ("says 'docker compose'", "'multi-container'").
- **Be slightly pushy** -- Claude tends to undertrigger skills. Add edge cases: "even if the user doesn't explicitly mention Docker, if they're describing a multi-service architecture, use this skill."
- **Add anti-triggers** to avoid false positives: "Do NOT use for single-container deployments (use docker-simple instead)."
- **Include concrete artifacts** when applicable: file extensions, CLI command names, specific terms.
- **Keep it 50-150 words** -- long enough for comprehensive coverage, short enough to scan.

#### Body structure by pattern

**Tool wrapper pattern:**
```markdown
# Skill Name
One-line summary.

## Prerequisites
What needs to be installed or configured.

## When to use
Bullet list of concrete use cases.

## Quick start
Copy-pasteable command examples.

## Options / Parameters
Table of flags, arguments, or configuration.

## Tips
Practical advice, gotchas, edge cases.

## See also
Related skills, external docs.
```

**Practice guide pattern:**
```markdown
# Skill Name
Brief overview paragraph.

## Core principles
The "why" behind the approach.

## Workflow
### Step 1: ...
### Step 2: ...

## Patterns and examples
Before/after code examples, decision tables.

## Constraints
What to always do and what to avoid.

## Troubleshooting
Common issues with solutions.

## References
Links to external resources.
```

**Process workflow pattern:**
```markdown
# Skill Name
High-level overview.

## Phase 1: [Name]
### 1.1 Sub-step
### 1.2 Sub-step

## Phase 2: [Name]
...

## Reference files
Pointers to bundled docs in references/ directory.
```

### Step 4: Apply writing best practices

When filling in the body content, follow these guidelines:

- **Use imperative form** in instructions: "Read the config file" not "You should read the config file"
- **Explain the why**, not just the what. Today's LLMs are smart -- they follow instructions better when they understand the reasoning. Avoid heavy-handed MUSTs in all caps unless truly critical.
- **Include examples** -- concrete input/output pairs make instructions dramatically clearer:
  ```markdown
  **Example:**
  Input: "Set up auth for my Express app"
  Output: JWT-based auth middleware with refresh token rotation
  ```
- **Use decision tables** for choosing between options -- they're scannable and precise
- **Keep SKILL.md under 500 lines** -- if approaching this limit, move detailed reference material to `references/` subdirectory with clear pointers from SKILL.md
- **For large reference files** (>300 lines), include a table of contents at the top
- **Progressive disclosure** -- metadata is always in context (~100 words), SKILL.md body loads when triggered (<500 lines), bundled resources load on demand (unlimited)

### Step 5: Validate the output

After generating the scaffold, verify:

- [ ] `name` in frontmatter matches directory name
- [ ] `description` includes both "what it does" and "when to trigger"
- [ ] `description` includes anti-triggers if there are similar/competing skills
- [ ] YAML frontmatter is valid (watch for unescaped colons, quotes in values)
- [ ] Body has clear structure with meaningful headings
- [ ] Instructions are actionable, not just descriptive
- [ ] Examples are included where they'd help clarify intent
- [ ] Any referenced files (references/, scripts/, assets/) actually exist
- [ ] Total SKILL.md is under 500 lines

## Example: generating a complete skill

If the user says "I want a skill that helps write conventional commit messages":

**Generated directory:**
```
commit-helper/
├── SKILL.md
└── references/
    └── conventional-commits.md
```

**Generated SKILL.md:**
```yaml
---
name: commit-helper
description: >
  Generate conventional commit messages from staged git changes. Use this skill when the user
  wants to write a commit message, asks for help with git commits, says "commit message",
  "write commit", "conventional commit", or has staged changes and needs a well-formatted
  commit. Also triggers when reviewing commit history for consistency. Do NOT use for
  git operations beyond commit message formatting (use git directly).
---
```

```markdown
# Commit Helper

Generate clear, conventional commit messages by analyzing staged changes and inferring intent.

## Format

Follow the Conventional Commits specification:

\`\`\`
<type>(<scope>): <description>

[optional body]

[optional footer]
\`\`\`

**Types:** feat, fix, docs, style, refactor, perf, test, build, ci, chore

## Workflow

1. Run `git diff --staged` to see what's being committed
2. Identify the primary change type and scope
3. Write a concise description (imperative mood, no period, under 72 chars)
4. Add body if the "why" isn't obvious from the description
5. Add footer for breaking changes or issue references

## Examples

**Input:** Staged diff shows a new `/api/users` endpoint
**Output:** `feat(api): add user registration endpoint`

**Input:** Staged diff fixes a null pointer in auth middleware
**Output:** `fix(auth): handle null token in middleware validation`

For the full Conventional Commits specification, see `references/conventional-commits.md`.
```

## Common mistakes to avoid

- **Empty subdirectories** -- don't create `assets/`, `scripts/`, `references/` unless you put files in them
- **Description that's too vague** -- "Helps with code" won't trigger. Be specific about scenarios.
- **Referencing files that don't exist** -- if your SKILL.md says "see references/guide.md", that file must exist
- **Overly rigid instructions** -- "ALWAYS do X, NEVER do Y" in all caps everywhere. Explain the reasoning instead.
- **Mixing trigger info into the body** -- "Activation conditions" in the body don't affect triggering. Only the `description` field matters.
