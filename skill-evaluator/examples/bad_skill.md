# Bad Skill Example

Use this example when you need a negative calibration sample for Skill evaluation. It demonstrates the common failure mode of writing a Skill like a long, fuzzy handbook instead of a router.

## What This Example Is Trying To Be

An imaginary Skill that is supposed to help with product planning, research, writing, diagrams, data analysis, and meetings.

## Example Frontmatter

```yaml
---
name: product-helper
description: Help with product work, documents, planning, ideas, research, and other related tasks.
---
```

## Example Main File Excerpt

```md
# Product Helper

You are an expert in product, strategy, writing, planning, execution, research, and communication.

## What You Can Do

- Help write PRDs
- Help analyze markets
- Help summarize interviews
- Help create plans
- Help brainstorm features
- Help with team communication
- Help review product metrics
- Help with roadmaps
- Help with documentation

## References

See `references/ref1.md` for more details.
See `references/ref2.md` for more details.
See `references/ref3.md` for more details.

## Workflow

Figure out what the user wants and help them.

## More Guidance

[400+ lines of mixed frameworks, templates, meeting advice, prompt fragments, market-analysis checklists, and example outputs inline here]
```

## Why This Is Bad

### Layer 1 Failure: weak discovery surface

- `description` is vague.
- It does not use concrete trigger phrases.
- It does not define any scope boundary.
- It overlaps with many neighboring Skills.

### Layer 2 Failure: no routing behavior

- The main file is trying to do everything itself.
- There is no Quick Reference or routing table.
- The workflow is too vague to execute consistently.
- Detailed content is mixed directly into the main file.

### Layer 3 Failure: poor supporting resources

- File names like `ref1.md` do not communicate content.
- References are naked paths with no loading condition.
- The supporting files are not organized by role.

## Expected Evaluation Outcome

This example should be scored poorly on:

- Structure Design
- Trigger Clarity
- Routing Quality
- Progressive Disclosure

## Typical Recommendations

1. Rewrite the description to name the exact job and trigger phrases.
2. Split the mixed handbook content into domain-specific supporting files.
3. Replace naked references with contract references.
4. Add a Quick Routing table near the top of `SKILL.md`.
5. Rename vague files to descriptive names.
