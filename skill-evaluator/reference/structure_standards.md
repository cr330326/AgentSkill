# Structure Standards Reference

Use this reference when reviewing whether a Skill follows the three-layer architecture described in the article: directory page, main chapter, and on-demand appendix.

## Weighted Score: 30 Points

| Structural Area | Max Score | What good looks like |
|-----------------|-----------|----------------------|
| Layer 1: Entry Point | 10 | `description` is specific, discoverable, and scoped |
| Layer 2: Main File Router | 12 | `SKILL.md` routes work instead of dumping all details |
| Layer 3: On-Demand Resources | 8 | supporting files are organized, descriptive, and real |

## Layer 1: Entry Point (目录页)

### Description Requirements

The `description` should answer three questions in one compact sentence or paragraph:

1. What does the Skill do?
2. When should it trigger?
3. What nearby scope does it not try to cover?

**Essential Elements:**

- Clear purpose statement (what the Skill does)
- Trigger keywords (when to activate)
- Scope boundaries (what it does NOT do)

**Character Budget:**

- Optimal: 100-200 characters
- Maximum: Share 15,000 character pool with other Skills
- Adjustment: Use `SLASH_COMMAND_TOOL_CHAR_BUDGET` environment variable

**Quality Checklist:**

- [ ] Contains specific trigger keywords
- [ ] Distinguishes from similar Skills
- [ ] Not too vague ("help with stuff")
- [ ] Not too long (avoids truncation)

**Score Anchors:**

- 9-10: Clear purpose, concrete triggers, crisp scope boundary
- 6-8: Mostly clear but somewhat broad or under-keyworded
- 3-5: Triggerable only with luck because the description is vague or generic
- 0-2: Missing, misleading, or too vague to be useful

### Example Comparison

**Poor:**

```yaml
description: Help with writing skills and files.
```

Problems:

- Too broad
- No trigger phrases
- No distinction from adjacent skills

**Good:**

```yaml
description: Evaluate and score other Skills, identify design gaps, and recommend concrete improvements. Use when reviewing a SKILL.md, auditing skill structure, checking progressive disclosure, or improving a skill document.
```

### Common Layer 1 Failures

| Failure | Why it hurts | Improvement |
|---------|--------------|-------------|
| Generic purpose | The Skill will not trigger reliably | Name the exact job and object: evaluate Skills, summarize PRs, create Word docs |
| Missing trigger vocabulary | User language and description language do not meet | Add the phrases users are likely to say |
| No scope boundary | Skill overlaps with nearby skills | Clarify what this Skill does not cover |

## Layer 2: Main File Router (章节)

The main file should behave like a router. It should tell the agent what path to take, not try to inline every detail.

### Structural Expectations

- `SKILL.md` stays under 500 lines unless there is a strong reason not to
- A `Quick Reference` or routing table appears near the top
- The file explains the default workflow
- References are contract-based, not just naked file paths
- `allowed-tools` reflects least privilege for the job

### Router Checklist

- [ ] There is a short explanation of what “good” looks like
- [ ] There is a route table or equivalent navigation aid
- [ ] The workflow says when to inspect, when to read references, and when to use scripts/templates
- [ ] Main sections are easy to scan
- [ ] Detailed knowledge is pushed outward to supporting files

### Score Anchors

- 10-12: Clear router, readable workflow, good contracts, disciplined tool scope
- 7-9: Understandable but some routing or workflow details are buried
- 4-6: Mixed router and reference content; usable but noisy
- 0-3: Main file is mostly a dump of details with little routing logic

### Red Flags

- `SKILL.md` reads like a handbook instead of a routing page
- There is no route table or obvious navigation aid
- File paths are listed without telling the agent when to load them
- `allowed-tools` grants more power than the task needs

## Layer 3: On-Demand Resources (附录)

Supporting files should have clear roles.

### Recommended Resource Roles

| Directory | Role | Typical contents |
|-----------|------|------------------|
| `reference/` | knowledge | standards, formulas, policies, schemas |
| `templates/` | standardized output | reports, code skeletons, review formats |
| `scripts/` | deterministic actions | validators, converters, generators |
| `examples/` | worked examples | sample inputs and outputs |
| `data/` | static lookup data | JSON, CSV, benchmark tables |

### Resource Checklist

- [ ] File names are descriptive
- [ ] Referenced files actually exist
- [ ] Each file has one clear role
- [ ] Scripts handle deterministic logic
- [ ] Templates standardize output shape

### Score Anchors

- 7-8: Clean organization, descriptive names, references resolve cleanly
- 4-6: Mostly good but some files are missing, vague, or underused
- 1-3: Supporting files exist but feel accidental or disconnected
- 0: Everything is stuffed into the main file

### Naming Rules

Prefer names like these:

- `reference/progressive_disclosure.md`
- `templates/evaluation_report.md`
- `scripts/analyze_skill.py`

Avoid names like these:

- `reference/ref1.md`
- `docs/misc.md`
- `file.md`

## Structural Rewrite Patterns

### If the Skill has no real layer separation

- Keep routing logic in `SKILL.md`
- Move standards and examples into `reference/`
- Move reusable report formats into `templates/`
- Move deterministic checks into `scripts/`

### If the main file is too long

- Keep the high-frequency workflow in `SKILL.md`
- Move low-frequency detail into referenced files
- Replace lists of file paths with contract references

### If the directory exists but the files are empty

- Treat the Skill as structurally incomplete
- Score the intent separately from the actual implementation
- Recommend filling the resource files before adding more top-level complexity


