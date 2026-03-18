# Good Skill Example

Use this example when you need a positive calibration sample for Skill evaluation. It demonstrates the intended pattern from the article: directory, router, and on-demand appendix.

## What This Example Is Trying To Be

An imaginary Skill for evaluating API design proposals and generating structured design feedback.

## Example Frontmatter

```yaml
---
name: api-design-reviewer
description: Review API design documents, score interface quality, and recommend concrete fixes. Use when reviewing endpoint design, request or response schemas, versioning strategy, or API proposal documents.
---
```

## Example Main File Excerpt

```md
# API Design Reviewer

## Quick Routing

| If the user needs... | Then use | Why |
|----------------------|----------|-----|
| Endpoint and resource design review | `reference/interface_design.md` | Review naming, consistency, and resource modeling |
| Schema and payload review | `reference/schema_quality.md` | Review request and response structures |
| Formal review output | `templates/review_report.md` | Keep scoring and recommendations consistent |
| Repeatable checks | `scripts/check_api_doc.py` | Gather deterministic baseline signals |

## Default Workflow

1. Identify the target API proposal and review depth.
2. Run the baseline checker when a concrete file is provided.
3. Load only the needed references.
4. Produce scored findings and a rewrite plan.

## Contract References

When the user asks whether endpoints are modeled clearly:
-> Load `reference/interface_design.md` for resource-modeling criteria and naming checks.

When the user asks whether request or response structures are well designed:
-> Load `reference/schema_quality.md` for schema rules, anti-patterns, and rewrite examples.

When the user wants a formal scorecard:
-> Use `templates/review_report.md` for structured output.
```

## Why This Is Good

### Layer 1 Success: strong discovery surface

- The `description` names the exact object and task.
- It includes realistic trigger language.
- It is specific enough to trigger reliably.

### Layer 2 Success: the main file acts as a router

- The Quick Routing table reduces search effort.
- The workflow is short, ordered, and executable.
- The contract references tell the agent when to load which resource and why.

### Layer 3 Success: supporting files have clear jobs

- `reference/` owns domain rules.
- `templates/` owns output shape.
- `scripts/` owns deterministic checks.
- File names are descriptive.

## Expected Evaluation Outcome

This example should score strongly on:

- Structure Design
- Content Quality
- Progressive Disclosure & Operability

## What Makes It Stable

1. High-frequency instructions stay in the main file.
2. Low-frequency detail moves into referenced resources.
3. Each reference is introduced with a contract.
4. The Skill can answer common questions without loading irrelevant detail.
