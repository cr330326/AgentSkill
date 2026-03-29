# ARIA & Semantic HTML Reference

## Prefer native HTML over ARIA

The first rule of ARIA is: don't use ARIA if you can use a native HTML element that already has
the semantics and behavior you need.

### Common anti-patterns and fixes

#### Clickable div instead of button

```jsx
// BAD
<div onClick={handleClick} className="btn">
  Submit
</div>

// GOOD
<button onClick={handleClick} className="btn">
  Submit
</button>
```

Why: `<button>` provides keyboard activation (Enter/Space), focus management, and the implicit
`role="button"` for free. A `<div>` has none of these.

#### Div with role="link" instead of anchor

```jsx
// BAD
<div role="link" onClick={() => navigate('/about')}>
  About Us
</div>

// GOOD
<a href="/about">About Us</a>
// or with client-side routing:
<Link to="/about">About Us</Link>
```

#### Custom checkbox instead of native input

```jsx
// BAD
<div
  role="checkbox"
  aria-checked={checked}
  onClick={toggle}
  className="custom-checkbox"
>
  {checked && <CheckIcon />}
</div>

// GOOD — visually hidden native input with custom styling
<label className="custom-checkbox">
  <input
    type="checkbox"
    checked={checked}
    onChange={toggle}
    className="sr-only"
  />
  <span className="custom-checkbox__visual">
    {checked && <CheckIcon aria-hidden="true" />}
  </span>
  Accept terms
</label>
```

## ARIA roles

### Valid roles checklist

Verify every `role` attribute uses a valid WAI-ARIA role. Common valid roles:

**Landmark**: `banner`, `complementary`, `contentinfo`, `form`, `main`, `navigation`, `region`, `search`

**Widget**: `alert`, `alertdialog`, `button`, `checkbox`, `combobox`, `dialog`, `grid`, `gridcell`,
`link`, `listbox`, `menu`, `menubar`, `menuitem`, `menuitemcheckbox`, `menuitemradio`, `option`,
`progressbar`, `radio`, `radiogroup`, `scrollbar`, `searchbox`, `separator`, `slider`, `spinbutton`,
`status`, `switch`, `tab`, `tablist`, `tabpanel`, `textbox`, `timer`, `toolbar`, `tooltip`, `tree`,
`treegrid`, `treeitem`

**Document structure**: `article`, `cell`, `columnheader`, `definition`, `directory`, `document`,
`feed`, `figure`, `group`, `heading`, `img`, `list`, `listitem`, `math`, `none`, `note`,
`presentation`, `row`, `rowgroup`, `rowheader`, `table`, `term`

### Required owned elements

Some roles require specific children:

| Parent role | Required children |
|-------------|-------------------|
| `list` | `listitem` |
| `menu` / `menubar` | `menuitem`, `menuitemcheckbox`, `menuitemradio` |
| `tablist` | `tab` |
| `tree` | `treeitem` |
| `grid` / `treegrid` | `row` → `gridcell` / `columnheader` / `rowheader` |
| `radiogroup` | `radio` |

### Required ARIA properties per role

| Role | Required properties |
|------|---------------------|
| `checkbox` | `aria-checked` |
| `combobox` | `aria-expanded`, `aria-controls` |
| `heading` | `aria-level` |
| `meter` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| `option` | (none, but typically needs `aria-selected`) |
| `radio` | `aria-checked` |
| `scrollbar` | `aria-controls`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`, `aria-orientation` |
| `separator` (focusable) | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| `slider` | `aria-valuenow`, `aria-valuemin`, `aria-valuemax` |
| `switch` | `aria-checked` |

## Accessible names

Every interactive element must have a programmatically determinable accessible name.
The name computation priority (simplified):

1. `aria-labelledby` (references another element's text)
2. `aria-label` (string label)
3. Native label mechanisms (`<label>`, `alt`, `<caption>`, `<legend>`, `<title>` in SVG)
4. Element text content (for `<button>`, `<a>`, etc.)
5. `title` attribute (last resort — has poor screen reader support)
6. `placeholder` (should never be the only label)

### Checking for missing names

```jsx
// BAD — icon button with no accessible name
<button onClick={onClose}>
  <XIcon />
</button>

// GOOD
<button onClick={onClose} aria-label="Close dialog">
  <XIcon aria-hidden="true" />
</button>
```

```jsx
// BAD — input with placeholder only
<input type="email" placeholder="Email address" />

// GOOD
<label>
  Email address
  <input type="email" placeholder="user@example.com" />
</label>
```

## aria-live regions

Use `aria-live` to announce dynamic content changes to screen readers.

| Value | When to use |
|-------|-------------|
| `polite` | Non-urgent updates (search results count, saved confirmation) |
| `assertive` | Urgent information (errors, session timeout warnings) |
| `off` | Default — no announcements |

Important rules:
- The live region container must exist in the DOM *before* the content changes
- Don't put `aria-live` on elements that change constantly (causes announcement spam)
- Use `role="status"` (polite) or `role="alert"` (assertive) as shortcuts

```jsx
// Pattern: status message
const [status, setStatus] = useState('');

return (
  <>
    <button onClick={handleSave}>Save</button>
    <div role="status" aria-live="polite">
      {status}
    </div>
  </>
);
```

## Heading hierarchy

- Pages should have exactly one `<h1>`
- Headings should not skip levels (h1 → h3 without h2)
- Use headings to create a navigable document outline, not for visual styling
- In component libraries, consider `aria-level` with `role="heading"` for flexible heading levels

```jsx
// BAD — heading used for styling
<h3 className="small-text">Terms and conditions apply</h3>

// GOOD
<p className="small-text">Terms and conditions apply</p>
```

## Landmark regions

Ensure the page has appropriate landmark regions so screen reader users can navigate by landmarks:

- `<header>` or `role="banner"` — site header (one per page, top-level)
- `<nav>` or `role="navigation"` — navigation blocks
- `<main>` or `role="main"` — primary content (exactly one per page)
- `<footer>` or `role="contentinfo"` — site footer
- `<aside>` or `role="complementary"` — secondary content
- `<form>` with `aria-label`/`aria-labelledby` — named form landmark
- `role="search"` — search functionality

If multiple landmarks of the same type exist, label them distinctly:
```jsx
<nav aria-label="Main navigation">...</nav>
<nav aria-label="Footer links">...</nav>
```
