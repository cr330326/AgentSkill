---
name: react-a11y
description: >
  Audit React components for accessibility (a11y) issues and produce actionable fix-it reports
  with before/after code diffs. Covers ARIA attributes, keyboard navigation, color contrast,
  focus management, semantic HTML, screen reader compatibility, and form labeling.
  Use this skill whenever the user asks to "check accessibility", "audit a11y", "fix ARIA",
  "improve keyboard navigation", "check color contrast", "make accessible", "screen reader support",
  "wcag compliance", "accessibility review", or any variation involving React component accessibility.
  Also trigger when a user shares React/JSX code and mentions disabled users, assistive technology,
  Section 508, WCAG, or inclusive design.
---

# React Accessibility (a11y) Auditor

Perform thorough accessibility audits of React components and produce structured reports with
concrete fix suggestions and before/after code comparisons.

## When to use

- User shares React/JSX component code and asks for an accessibility review
- User wants to check WCAG 2.1 AA (or AAA) compliance of their UI
- User asks about ARIA attributes, keyboard navigation, focus traps, color contrast, or screen reader support
- User wants to make an existing component accessible
- User asks for a11y best practices for a specific UI pattern (modal, dropdown, tabs, etc.)

## Audit workflow

### 1. Collect the code

Read the component(s) the user provides. If only a file path is given, read the file. If the user
points to a directory, find all `.tsx`, `.jsx`, `.ts`, `.js` files that contain JSX and audit each one.

### 2. Run the checklist

Work through each category below against every component. For each issue found, record:

| Field | Description |
|-------|-------------|
| **Category** | Which audit category (ARIA, Keyboard, Contrast, etc.) |
| **Severity** | `critical`, `serious`, `moderate`, `minor` |
| **Rule** | Short rule ID (e.g. `aria-role-valid`, `kbd-focus-visible`) |
| **Location** | File path and line number(s) |
| **Problem** | Plain-language description of what's wrong |
| **Impact** | Who is affected and how |
| **Fix** | Step-by-step instructions |
| **Before** | Code snippet showing the current state |
| **After** | Code snippet showing the corrected version |
| **WCAG ref** | Applicable WCAG 2.1 success criterion (e.g. 1.3.1, 2.1.1) |

### 3. Audit categories

Work through these categories in order. For detailed rules and examples in each category,
read the corresponding reference file only when you need its details.

#### A. Semantic HTML & ARIA — `references/aria-and-semantics.md`
- Prefer native HTML elements over ARIA (`<button>` not `<div role="button">`)
- Validate ARIA roles, states, and properties
- Check for missing accessible names (`aria-label`, `aria-labelledby`, visible text)
- Detect redundant or conflicting ARIA (e.g. `role="button"` on a `<button>`)
- Ensure landmark regions are present and correctly nested
- Check `aria-live` regions for dynamic content updates
- Validate `aria-expanded`, `aria-selected`, `aria-checked` reflect component state

#### B. Keyboard Navigation — `references/keyboard-nav.md`
- All interactive elements must be reachable via Tab
- Custom interactive elements need `tabIndex={0}` (or managed focus)
- Click-only handlers on non-interactive elements need `onKeyDown`/`onKeyUp` equivalents
- Focus order must follow logical reading order
- Focus must be visible (`:focus-visible` or custom focus styles)
- Modal/dialog must trap focus and return focus on close
- `Escape` should close overlays
- Complex widgets (tabs, menus, trees) need arrow-key navigation per WAI-ARIA Authoring Practices

#### C. Color & Visual — `references/color-contrast.md`
- Text contrast ratio: ≥ 4.5:1 for normal text, ≥ 3:1 for large text (WCAG AA)
- Non-text contrast: ≥ 3:1 for UI components and graphical objects
- Information must not be conveyed by color alone
- Check for hardcoded colors that may fail in dark mode or high-contrast mode
- Ensure focus indicators meet 3:1 contrast against adjacent colors

#### D. Forms & Labels
- Every `<input>`, `<select>`, `<textarea>` needs an associated `<label>` or `aria-label`
- Error messages must be programmatically associated (`aria-describedby` or `aria-errormessage`)
- Required fields must be indicated both visually and programmatically (`aria-required` or `required`)
- Form validation errors should be announced to screen readers (via `aria-live` or focus management)
- Group related controls with `<fieldset>` + `<legend>` or `role="group"` + `aria-labelledby`

#### E. Images & Media
- Every `<img>` needs meaningful `alt` text or `alt=""` for decorative images
- Icon-only buttons need accessible labels
- SVG icons used meaningfully need `role="img"` and `aria-label` or `<title>`
- Decorative SVGs should have `aria-hidden="true"`
- Video/audio content should reference captions/transcripts

#### F. Dynamic Content & State
- Content changes announced via `aria-live` regions where appropriate
- Loading states should be communicated (`aria-busy`, status messages)
- Toast/notification components should use `role="status"` or `role="alert"`
- Conditional rendering shouldn't orphan focus (if focused element disappears, move focus)
- Route changes in SPAs should announce the new page title

#### G. Component-Pattern-Specific Rules — `references/component-patterns.md`
- Modals / Dialogs
- Dropdown menus
- Tabs
- Accordions
- Tooltips
- Carousels
- Data tables
- Autocomplete / Combobox

### 4. Produce the report

Structure the final output like this:

```
## Accessibility Audit Report

### Summary
- **Components audited**: <count>
- **Total issues**: <count>
- **Critical**: <n>  |  **Serious**: <n>  |  **Moderate**: <n>  |  **Minor**: <n>

### Issues

#### 1. [Category] Rule ID — Severity

**Problem**: ...
**Impact**: ...
**WCAG**: ...
**Location**: `file:line`

**Before:**
```jsx
// problematic code
```

**After:**
```jsx
// fixed code
```

---

(repeat for each issue, ordered by severity: critical → minor)

### Recommendations
- General improvements that don't map to a single line of code
- Testing suggestions (screen reader, axe-core, keyboard-only navigation)

### Testing Checklist
- [ ] Run axe-core or similar automated tool
- [ ] Tab through entire UI with keyboard only
- [ ] Test with VoiceOver (macOS) or NVDA (Windows)
- [ ] Verify in Windows High Contrast Mode
- [ ] Check with 200% browser zoom
```

### 5. Severity definitions

Use these consistently:

| Severity | Meaning |
|----------|---------|
| **Critical** | Blocks access entirely for some users. Must fix before release. Examples: no keyboard access, missing form labels, focus trap with no escape. |
| **Serious** | Major barrier that makes the experience very difficult. Examples: poor focus management in modals, missing live region for critical updates. |
| **Moderate** | Causes friction but users can work around it. Examples: missing skip link, suboptimal heading hierarchy, redundant ARIA. |
| **Minor** | Best-practice improvement. Examples: decorative image with non-empty alt, redundant role on native element. |

## Guidelines for writing fixes

- Always show real code — not pseudocode — in before/after blocks.
- Preserve the user's coding style (hooks vs. classes, CSS-in-JS vs. classNames, etc.).
- When suggesting new attributes, explain *why* they're needed — not just what to add.
- If a fix requires a structural change (e.g. replacing a `<div>` tree with a `<dialog>`),
  show the full refactored component, not just the changed line.
- Prefer native HTML semantics over ARIA overlays wherever possible and explain the tradeoff.
- When the correct fix depends on context you don't have (e.g. whether an image is decorative),
  note the assumption and provide alternatives.

## If the user provides only a description (no code)

If the user describes a UI pattern but doesn't share code, produce:
1. An accessible reference implementation of that pattern
2. A list of a11y requirements the pattern must satisfy
3. Common mistakes to avoid

## Tools and testing recommendations

When wrapping up, suggest concrete tools the user can integrate:

- **eslint-plugin-jsx-a11y** — static lint rules for JSX
- **@axe-core/react** — runtime accessibility checks in dev mode
- **Storybook a11y addon** — visual a11y panel in component stories
- **Pa11y / Lighthouse** — automated page-level audits
- **Screen readers** — VoiceOver (macOS), NVDA (Windows), Orca (Linux)
