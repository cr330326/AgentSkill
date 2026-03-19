# Content Quality Reference

Use this reference when judging whether a Skill is well written, easy to trigger, easy to route, and capable of producing actionable output.

## Weighted Score: 40 Points

| Content Area | Max Score | What good looks like |
| -------------- | ----------- | ---------------------- |
| Trigger Clarity | 10 | description uses real user vocabulary |
| Routing Quality | 12 | quick routing and contract references are easy to follow |
| Workflow and Guidance | 10 | instructions are ordered, concrete, and complete |
| Recommendation Quality | 8 | output is evidence-based and actionable |

## 1. Trigger Clarity

### Trigger Checks

- The `description` names the exact object and task
- It includes phrases users are likely to type
- It distinguishes this Skill from adjacent ones
- It does not waste space on generic filler

### Strong Description Pattern

```yaml
description: Evaluate and score other Skills, identify design gaps, and recommend concrete improvements. Use when reviewing a SKILL.md, auditing skill structure, checking progressive disclosure, or improving a skill document.
```

### Weak Description Pattern

```yaml
description: Help with skills.
```

### Trigger Score Anchors

- 9-10: Highly specific and trigger-rich
- 6-8: Clear but somewhat broad
- 3-5: Generic or keyword-poor
- 0-2: Very unlikely to trigger correctly

## 2. Routing Quality

The best Skills reduce decision cost.

### Quick Routing Table

A good routing table:

- sits near the top
- uses user-facing wording rather than internal jargon
- keeps one route per row
- points to one next resource or tool per route

### Contract Reference Standard

Every important referenced file should be introduced as a contract with three parts:

1. Trigger condition: when should the file be loaded?
2. Path: which file should be loaded?
3. Expected payload: what will the agent get from it?

**Weak reference:**

```md
See `references/revenue.md` for more details.
```

**Strong reference:**

```md
When the user asks about revenue growth, ARPU, or revenue composition:
-> Load `references/revenue.md` for formulas, benchmarks, and red-flag checks.
```

### Routing Score Anchors

- 10-12: Clear routing table plus repeated use of contract references
- 7-9: Usable routing, but some references are weak or implicit
- 4-6: The agent can navigate, but with extra search effort
- 0-3: Hard to tell where to go next

## 3. Workflow and Guidance

### Workflow Checks

- Steps are in execution order
- The workflow starts with understanding the user's request
- Deterministic checks happen before qualitative judgment when appropriate
- Output expectations are explicit
- Critical constraints are stated as rules, not hints

### Strong Workflow Pattern

1. Identify the target and review depth.
2. Run deterministic checks if a concrete file path exists.
3. Load only the needed reference files.
4. Produce scored findings with evidence and a rewrite plan.

### Weak Workflow Pattern

- Lists many checks with no sequence
- Mixes optional tips into mandatory steps
- Tells the agent to "be helpful" instead of saying what to do

### Workflow Score Anchors

- 9-10: Ordered, executable, and low ambiguity
- 6-8: Mostly good but some steps are underspecified
- 3-5: Understandable only after rereading
- 0-2: Vague and unreliable

## 4. Recommendation Quality

The output should help the user fix the Skill, not just judge it.

### Recommendation Checks

- Scores are dimension-based, not hand-wavy
- Findings are tied to specific files or sections
- Recommendations explain impact, not just preference
- Rewrite examples are used when wording matters
- High-priority issues are separated from polish issues

### Good Recommendation Pattern

| Issue | Why it hurts | Better pattern |
| ------ | -------------- | ---------------- |
| Naked reference path | The agent has no loading condition | Replace it with a contract reference |
| `SKILL.md` is 700+ lines | Routing and reference material are mixed together | Keep routing in `SKILL.md`, move detail into `references/` |

### Recommendation Score Anchors

- 7-8: Concrete, prioritized, easy to act on
- 4-6: Useful but still somewhat generic
- 1-3: Mostly abstract advice
- 0: No usable recommendations

## Content Red Flags

| Red flag | Why it is a problem | Fix |
| ---------- | --------------------- | ----- |
| No examples | Hard to calibrate what "good" means | Add one poor and one strong example |
| No output format | Reviews vary too much | Use a template |
| No rewrite guidance | User learns what is wrong but not how to improve | Add before/after snippets |
| Overlapping sections | Same rules appear in many places | Keep one source of truth per rule |

## Calibration Examples

Use contrastive examples when the review is drifting into vague preference judgments.

- Load `examples/bad_skill.md` when you need a concrete negative anchor.
- Load `examples/good_skill.md` when you need a concrete positive anchor.
- Compare the target Skill against both, not just against abstract principles.

This is especially useful when reviewing:

- borderline descriptions
- weak routing tables
- naked file references
- Skills that feel "sort of okay" but are hard to score consistently

## Reviewer Guidance

- Judge the Skill against its intended job, not against maximum complexity.
- Simplicity is a strength when the problem is narrow.
- Complexity without routing is a quality failure.
- Prefer the smallest wording change that improves discoverability or execution clarity.
