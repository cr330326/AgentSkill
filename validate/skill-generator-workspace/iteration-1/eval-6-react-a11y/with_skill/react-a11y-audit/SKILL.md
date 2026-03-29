---
name: react-a11y-audit
description: >
  Audit React components for accessibility (a11y) issues across four dimensions:
  ARIA attributes, keyboard navigation, color contrast, and screen reader compatibility.
  Produces concrete fix suggestions with before/after code comparisons.
  Use when user asks to "check accessibility", "audit a11y", "fix ARIA",
  "keyboard navigation issues", "screen reader support", "color contrast check",
  "WCAG compliance", or "make component accessible".
  Do NOT use for native mobile accessibility (iOS VoiceOver / Android TalkBack)
  or PDF accessibility — those require platform-specific tooling.
---

# React Accessibility Audit

## Purpose

Detect and fix accessibility violations in React components so that users with
disabilities — including those who rely on screen readers, keyboard-only navigation,
or high-contrast modes — can use the application effectively.

All guidance targets **WCAG 2.1 AA** compliance unless the user requests AAA.

## Workflow

### 1. Gather scope

Determine which files to audit:
- If the user provides specific files or components, audit those.
- If the user says "audit the project", search for `*.tsx` and `*.jsx` files under `src/`.
- Prioritize interactive components (forms, modals, menus, tabs, dialogs) — they carry the highest a11y risk.

### 2. Run the four-dimension audit

Inspect every component against the four dimensions below. For each violation found,
record: **dimension, severity (critical / serious / moderate / minor), location (file:line), description, fix**.

#### Dimension A — ARIA Attributes

Check that ARIA roles, states, and properties are correct and complete.

| Check | What to look for | Severity |
|-------|-------------------|----------|
| Missing role | Interactive custom element (`<div onClick>`) without `role` | Critical |
| Invalid ARIA attribute | Misspelled or non-existent `aria-*` prop | Serious |
| Missing accessible name | Interactive element without `aria-label`, `aria-labelledby`, or visible text | Critical |
| Redundant ARIA | Native HTML element with redundant role (e.g. `<button role="button">`) | Minor |
| Incorrect `aria-expanded` / `aria-selected` / `aria-checked` | Boolean state not toggled in sync with visual state | Serious |
| Missing `aria-live` | Dynamic content region that updates without notifying screen readers | Serious |
| Missing relationship attrs | `aria-controls`, `aria-owns`, `aria-describedby` absent where needed | Moderate |

**Before / After — Missing role & accessible name:**

```tsx
// BEFORE — div acting as button, invisible to screen readers
<div className="close-btn" onClick={handleClose}>
  <XIcon />
</div>

// AFTER — proper semantics + accessible name
<button
  className="close-btn"
  onClick={handleClose}
  aria-label="Close dialog"
>
  <XIcon aria-hidden="true" />
</button>
```

**Before / After — aria-expanded sync:**

```tsx
// BEFORE — aria-expanded never updates
<button aria-expanded="false" onClick={() => setOpen(!open)}>
  Menu
</button>

// AFTER — state drives attribute
<button aria-expanded={open} onClick={() => setOpen(!open)}>
  Menu
</button>
{open && <ul role="menu">{/* items */}</ul>}
```

**Before / After — Dynamic live region:**

```tsx
// BEFORE — toast appears silently
<div className="toast">{message}</div>

// AFTER — screen reader announces the toast
<div className="toast" role="status" aria-live="polite">
  {message}
</div>
```

#### Dimension B — Keyboard Navigation

Ensure every interactive element is reachable and operable via keyboard alone.

| Check | What to look for | Severity |
|-------|-------------------|----------|
| Non-focusable interactive | `<div onClick>` or `<span onClick>` without `tabIndex={0}` (prefer native `<button>`) | Critical |
| Missing key handlers | `onClick` without corresponding `onKeyDown` / `onKeyUp` (Enter / Space) | Critical |
| Focus trap in modal | Modal/dialog does not trap focus or restore focus on close | Critical |
| Tab order | `tabIndex` > 0 used (breaks natural order) | Serious |
| Skip navigation | No skip-to-content link on pages with repeated nav | Moderate |
| Roving tabindex | Tab group (toolbar, tabs, menu) does not implement arrow-key navigation | Serious |
| Visible focus indicator | `:focus` styles removed with `outline: none` without replacement | Serious |

**Before / After — Keyboard-accessible custom button:**

```tsx
// BEFORE — keyboard users cannot activate
<div className="card" onClick={() => select(item)}>
  {item.name}
</div>

// AFTER — native button, keyboard-accessible by default
<button className="card" onClick={() => select(item)}>
  {item.name}
</button>
```

**Before / After — Focus trap in modal:**

```tsx
// BEFORE — focus escapes modal into background
function Modal({ onClose, children }) {
  return (
    <div className="modal-overlay">
      <div className="modal">{children}</div>
    </div>
  );
}

// AFTER — focus trapped, Escape closes, focus restored
import { useEffect, useRef } from 'react';

function Modal({ onClose, children }) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previousFocus.current = document.activeElement as HTMLElement;
    modalRef.current?.focus();
    return () => previousFocus.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key !== 'Tab') return;

    const focusable = modalRef.current?.querySelectorAll<HTMLElement>(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (!focusable || focusable.length === 0) return;

    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault(); last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault(); first.focus();
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        {children}
      </div>
    </div>
  );
}
```

**Before / After — Visible focus indicator:**

```css
/* BEFORE — focus ring removed entirely */
button:focus {
  outline: none;
}

/* AFTER — custom focus ring visible for keyboard, hidden for mouse */
button:focus-visible {
  outline: 2px solid #1a73e8;
  outline-offset: 2px;
}
```

#### Dimension C — Color Contrast

Verify text and interactive elements meet WCAG contrast ratios.

| Level | Normal text (< 18pt / 14pt bold) | Large text (>= 18pt / 14pt bold) | UI components & graphical objects |
|-------|----------------------------------|----------------------------------|-----------------------------------|
| AA | 4.5:1 | 3:1 | 3:1 |
| AAA | 7:1 | 4.5:1 | 3:1 |

**What to check:**
- Hardcoded color pairs in inline styles and CSS/Tailwind classes.
- Common violations: light gray text on white (`#999 on #fff` = 2.85:1), placeholder text, disabled states.
- When exact colors are in the code, calculate the ratio. When colors come from theme tokens or CSS variables, flag for manual verification.

**Decision table — common color pairs:**

| Foreground | Background | Ratio | AA normal | AA large | Action |
|------------|------------|-------|-----------|----------|--------|
| `#757575` | `#ffffff` | 4.6:1 | Pass | Pass | None |
| `#999999` | `#ffffff` | 2.85:1 | Fail | Fail | Darken to `#767676` (4.54:1) |
| `#ffffff` | `#1a73e8` | 4.6:1 | Pass | Pass | None |
| `#cccccc` | `#ffffff` | 1.6:1 | Fail | Fail | Darken to `#767676` or use different background |
| `#666666` | `#f5f5f5` | 5.9:1 | Pass | Pass | None |

**Before / After — Low contrast text:**

```tsx
// BEFORE — 2.85:1 ratio, fails AA
<p style={{ color: '#999', backgroundColor: '#fff' }}>
  Subtle helper text
</p>

// AFTER — 4.54:1 ratio, passes AA
<p style={{ color: '#767676', backgroundColor: '#fff' }}>
  Subtle helper text
</p>
```

**Before / After — Tailwind utility classes:**

```tsx
// BEFORE — text-gray-400 on white ≈ 3.0:1, fails AA for normal text
<span className="text-gray-400">Required field</span>

// AFTER — text-gray-500 on white ≈ 4.6:1, passes AA
<span className="text-gray-500">Required field</span>
```

#### Dimension D — Screen Reader Compatibility

Ensure content is meaningful and well-structured when consumed non-visually.

| Check | What to look for | Severity |
|-------|-------------------|----------|
| Missing alt text | `<img>` without `alt` prop, or decorative image without `alt=""` | Critical |
| Heading hierarchy | Skipped heading levels (h1 -> h3) or multiple h1s | Serious |
| Form labels | `<input>` without associated `<label>`, `aria-label`, or `aria-labelledby` | Critical |
| Table structure | Data table missing `<thead>`, `<th>`, or `scope` attributes | Serious |
| Icon-only elements | Icon with meaning but no text alternative | Critical |
| Hidden content | Content hidden with `display:none` but should be screen-reader visible, or vice versa | Moderate |
| Reading order | DOM order differs significantly from visual order (CSS grid/flex reordering) | Serious |

**Before / After — Image alt text:**

```tsx
// BEFORE — no alt, screen reader announces filename
<img src="/hero-banner.jpg" />

// AFTER — informative image gets descriptive alt
<img src="/hero-banner.jpg" alt="Team collaborating around a whiteboard" />

// Decorative image — empty alt so screen readers skip it
<img src="/decorative-wave.svg" alt="" />
```

**Before / After — Form labels:**

```tsx
// BEFORE — input has no programmatic label
<div>
  <span>Email</span>
  <input type="email" placeholder="you@example.com" />
</div>

// AFTER — label properly associated
<div>
  <label htmlFor="email-input">Email</label>
  <input id="email-input" type="email" placeholder="you@example.com" />
</div>
```

**Before / After — Icon-only button:**

```tsx
// BEFORE — screen reader says "button" with no label
<button onClick={onDelete}>
  <TrashIcon />
</button>

// AFTER — screen reader says "Delete item"
<button onClick={onDelete} aria-label="Delete item">
  <TrashIcon aria-hidden="true" />
</button>
```

**Before / After — Heading hierarchy:**

```tsx
// BEFORE — skips from h1 to h4
<h1>Dashboard</h1>
<h4>Recent Activity</h4>

// AFTER — correct hierarchy
<h1>Dashboard</h1>
<h2>Recent Activity</h2>
```

### 3. Report findings

Produce a structured report grouped by dimension. For each finding include:

```
### [Severity] Dimension X — Short description
**File:** `src/components/Modal.tsx:42`
**Issue:** <what is wrong and why it matters>
**Fix:**
<before/after code block>
```

Order findings: Critical -> Serious -> Moderate -> Minor.

End the report with a **Summary table**:

| Dimension | Critical | Serious | Moderate | Minor | Total |
|-----------|----------|---------|----------|-------|-------|
| A. ARIA Attributes | | | | | |
| B. Keyboard Navigation | | | | | |
| C. Color Contrast | | | | | |
| D. Screen Reader | | | | | |
| **Total** | | | | | |

### 4. Apply fixes (if requested)

If the user asks to fix issues (not just audit):
1. Fix all Critical issues first.
2. Then fix Serious issues.
3. Leave Moderate/Minor as comments with `// TODO(a11y):` prefix for manual review.
4. After fixing, re-audit the changed files to confirm no regressions.

## Common Component Patterns — Quick Reference

Refer to `references/component-patterns.md` for ARIA patterns for these common React components:
- Modal / Dialog
- Dropdown Menu
- Tabs
- Accordion
- Tooltip
- Combobox / Autocomplete
- Toast / Notification

## Tooling Integration

When available in the project, leverage these tools for deeper analysis:
- **eslint-plugin-jsx-a11y** — Static lint rules. Check if installed; if not, suggest adding it.
- **@axe-core/react** — Runtime audit in dev mode. Check for import in dev setup.
- **Lighthouse** — Full page audit. Suggest running via Chrome DevTools if applicable.

If `eslint-plugin-jsx-a11y` is present, run `npx eslint --no-eslintrc --plugin jsx-a11y --rule '{"jsx-a11y/alt-text": "error", "jsx-a11y/anchor-is-valid": "error", "jsx-a11y/aria-props": "error", "jsx-a11y/aria-role": "error", "jsx-a11y/click-events-have-key-events": "error", "jsx-a11y/no-noninteractive-element-interactions": "error", "jsx-a11y/no-static-element-interactions": "error"}' <files>` to get an automated first pass, then manually audit the dimensions above for issues lint cannot catch.
