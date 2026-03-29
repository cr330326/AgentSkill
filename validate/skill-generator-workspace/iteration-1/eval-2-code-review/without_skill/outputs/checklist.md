# Code Review Checklist — Quick Reference

Use this as a rapid-fire checklist during reviews. Each item is a yes/no question.
If the answer is "no" to any item, flag it in the review.

## Correctness
- [ ] Does the code match the stated intent (PR description / ticket)?
- [ ] Are edge cases handled (empty, nil, zero, max, concurrent)?
- [ ] Are boundary conditions correct (off-by-one, inclusive/exclusive)?
- [ ] Are all new code paths reachable and tested?

## Security
- [ ] Is all user input validated and sanitized?
- [ ] Are SQL queries parameterized (no string concatenation)?
- [ ] Are auth checks present on all new endpoints?
- [ ] Are secrets absent from code and logs?
- [ ] Is sensitive data excluded from API responses and error messages?
- [ ] Are new dependencies free of known CVEs?

## Performance
- [ ] Are there no N+1 query patterns?
- [ ] Are unbounded queries protected with LIMIT?
- [ ] Is algorithmic complexity reasonable for expected input sizes?
- [ ] Are external calls protected with timeouts?
- [ ] Are resources (connections, file handles) properly pooled and released?

## Error Handling
- [ ] Are all errors handled (no silent swallowing)?
- [ ] Do error messages have sufficient context?
- [ ] Are resources cleaned up in error paths?
- [ ] Are external calls wrapped with appropriate error handling?

## Code Quality
- [ ] Are names clear and descriptive?
- [ ] Are functions focused and short (<40 lines preferred)?
- [ ] Is there no duplicated logic?
- [ ] Is dead code removed?
- [ ] Are comments explaining "why" not "what"?

## Testing
- [ ] Are there tests for new/changed behavior?
- [ ] Do tests cover happy path and edge cases?
- [ ] Are assertions checking the right things?
- [ ] Are tests deterministic (no flaky timing)?
- [ ] Is there a regression test for bug fixes?

## Style
- [ ] Does the code follow project conventions?
- [ ] Are imports organized per project standard?
- [ ] Is formatting consistent with the codebase?

## API Design
- [ ] Are new public APIs minimal and consistent?
- [ ] Are breaking changes documented?
- [ ] Are error codes and return types appropriate?

## Documentation & Observability
- [ ] Are public APIs documented?
- [ ] Is logging adequate for production debugging?
- [ ] Are new config options documented?
