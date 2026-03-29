# SKILL.md Template

Use this as a starting point when generating new skills. Copy the relevant pattern
and fill in the placeholders.

---

## Minimal Template (Tool Wrapper)

```yaml
---
name: <skill-name>
description: >
  <What it does in one sentence>. Use this skill when the user <trigger conditions>,
  or says "<trigger phrase 1>", "<trigger phrase 2>", "<trigger phrase 3>".
  Also use when <edge case>. Do NOT use for <false positive scenario>
  (use <other-skill> instead).
---
```

```markdown
# <Skill Name>

<One-line summary of what this skill does and why it's useful.>

## Prerequisites

- <Tool/CLI that must be installed>
- <Environment variable or config needed>

## When to use

- <Concrete use case 1>
- <Concrete use case 2>
- <Concrete use case 3>

## Quick start

<Copy-pasteable example showing the most common usage:>

\`\`\`bash
<command example>
\`\`\`

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--flag` | What it controls | `value` |

## Tips

- <Practical gotcha or optimization>
- <Common mistake and how to avoid it>

## See also

- <Related skill or external documentation>
```

---

## Practice Guide Template

```yaml
---
name: <skill-name>
description: >
  <Methodology/practice description>. Use when <trigger conditions>.
  Handles <capability 1>, <capability 2>, <capability 3>.
  Do NOT use for <out of scope>.
---
```

```markdown
# <Skill Name>

<Overview paragraph explaining the approach and its value.>

## Core Principles

1. **<Principle 1>** -- <Why it matters>
2. **<Principle 2>** -- <Why it matters>
3. **<Principle 3>** -- <Why it matters>

## Workflow

### Step 1: <Phase Name>

<Instructions in imperative form.>

### Step 2: <Phase Name>

<Instructions with explanation of why this step matters.>

## Patterns

### <Pattern Name>

**When to use:** <Situation description>

**Before:**
\`\`\`<language>
// problematic code
\`\`\`

**After:**
\`\`\`<language>
// improved code
\`\`\`

## Decision Table

| Situation | Approach | Rationale |
|-----------|----------|-----------|
| <Case 1> | <What to do> | <Why> |
| <Case 2> | <What to do> | <Why> |

## Constraints

- Always: <thing to always do>
- Never: <thing to avoid and why>

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| <Problem> | <Root cause> | <Fix> |

## References

- [<Resource name>](<url>) -- <What it covers>
```

---

## Process Workflow Template

```yaml
---
name: <skill-name>
description: >
  <Process description>. Use when the user wants to <goal>,
  says "<phrase 1>", "<phrase 2>", or needs <capability>.
---
```

```markdown
# <Skill Name>

<High-level overview of the process and what it produces.>

## Phase 1: <Name>

### 1.1 <Sub-step>

<Detailed instructions. Explain reasoning behind important choices.>

### 1.2 <Sub-step>

<Instructions with examples.>

## Phase 2: <Name>

### 2.1 <Sub-step>

<Instructions.>

## Output Format

<Template or specification for what the skill produces:>

\`\`\`
<output structure>
\`\`\`

## Reference Files

- `references/<file>.md` -- <When to read this file and what it contains>
- `scripts/<file>.py` -- <What this script does and when to run it>
```

---

## Frontmatter Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Lowercase, hyphenated identifier. Must match directory name. |
| `description` | string | Primary trigger mechanism. 50-150 words. |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `license` | string | License identifier (e.g., "MIT") or "Complete terms in LICENSE.txt" |
| `allowed-tools` | string | Restrict which tools the skill can use |
| `metadata` | object | Version, tags, category, platforms, sources |

### Description Checklist

- [ ] Starts with what the skill does (1 sentence)
- [ ] Includes "Use this skill when" with trigger conditions
- [ ] Lists specific phrases users might say (in quotes)
- [ ] Covers edge cases that should also trigger
- [ ] Specifies anti-triggers with "Do NOT use for"
- [ ] Names alternative skills for false-positive scenarios
- [ ] Between 50-150 words total
