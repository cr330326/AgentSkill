# Progressive Disclosure Reference

Use this reference when evaluating whether a Skill gets high task quality from minimal context cost.

## Weighted Score: 30 Points

| Area | Max Score | What good looks like |
|------|-----------|----------------------|
| Main File Size Discipline | 10 | `SKILL.md` stays focused and under control |
| On-Demand Loading Design | 10 | low-frequency detail is pushed into referenced files |
| Operability and Tool Fit | 10 | scripts, templates, and tools are used where they add leverage |

## Core Principle

Progressive disclosure is not just about saving tokens. It is about protecting the model's limited working attention and maximizing Knowledge ROI.

**Question to ask during review:**

Would moving this information out of `SKILL.md` improve focus without hurting execution quality?

If yes, the Skill is probably under-split.

## 1. Main File Size Discipline

### 500-Line Rule

- Under 500 lines: usually acceptable
- 500-650 lines: review carefully; may need refactoring
- Over 650 lines: strong refactor signal unless scope is unusually constrained

### What belongs in `SKILL.md`

- High-frequency workflow
- Route table or navigation aid
- Contract references
- Key tool constraints
- Output rules

### What does not belong in `SKILL.md`

- Large blocks of formulas
- Long policy documents
- Many worked examples
- Repeated templates
- Deterministic code logic better handled by scripts

## 2. On-Demand Loading Design

### Split Decisions

| If the content is... | Best home |
|----------------------|-----------|
| core routing logic | `SKILL.md` |
| domain knowledge | `references/` |
| standard output shape | `assets/` |
| deterministic processing | `scripts/` |
| sample cases | `examples/` |
| static lookup data | `data/` |

### Contract Reference Checklist

- [ ] Trigger condition is stated
- [ ] File path is explicit
- [ ] Expected contents are stated
- [ ] The referenced file actually exists

### Red Flags

- `SKILL.md` contains all details and supporting directories are empty
- Many files exist but the main file never references them
- File names are too vague for the agent to select confidently
- The Skill lists paths but does not say when to load them

## 3. Operability and Tool Fit

The article's final point matters here: Skills and Tools should cooperate.

### Good Patterns

- Use `allowed-tools` to enforce least privilege
- Use scripts for deterministic, repeatable logic
- Use assets for standard output structures
- Let the agent execute a script rather than re-derive fixed logic every time

### Use a Script When

- the logic is formulaic
- the output should be repeatable
- the same calculation or validation would be rewritten again and again

### Do Not Force a Script When

- the task is mostly judgment
- the task depends on interactive clarification
- the output is open-ended and creative

### Score Anchors

- 9-10: Script/template/tool choices clearly improve reliability or token economy
- 6-8: Some leverage exists, but the design is only partially realized
- 3-5: Tools or files exist but do not materially help execution
- 0-2: No visible attention to operability

## Review Questions

Use these questions when scoring:

1. Is the main file mostly routing, or mostly detail?
2. Are low-frequency details moved outward?
3. Do scripts own deterministic logic?
4. Do templates own output structure?
5. Is the Skill likely to load only what it needs for common requests?

## Refactor Recommendations

### If the Skill is too long

- Keep the workflow in `SKILL.md`
- Split knowledge by domain into `references/`
- Move output structures into `assets/`
- Move deterministic checks into `scripts/`

### If the Skill has many files but poor loading behavior

- Add contract references in `SKILL.md`
- Add a Quick Routing table
- Rename vague files to descriptive names

### If the Skill overuses tools

- Trim `allowed-tools` to the minimum needed
- Keep destructive tools out unless the task genuinely requires them
