# Color Contrast Reference

## WCAG contrast requirements

### AA level (minimum)

| Content type | Minimum ratio | Examples |
|-------------|---------------|---------|
| Normal text (<18pt / <14pt bold) | 4.5:1 | Body text, labels, links |
| Large text (≥18pt / ≥14pt bold) | 3:1 | Headings, large buttons |
| UI components & graphical objects | 3:1 | Borders, icons, focus indicators |
| Disabled / inactive components | No requirement | Greyed-out buttons |
| Decorative / logos | No requirement | Brand logos, pure decoration |

### AAA level (enhanced)

| Content type | Minimum ratio |
|-------------|---------------|
| Normal text | 7:1 |
| Large text | 4.5:1 |

## Checking contrast in React code

Look for color values in:
- Inline styles (`style={{ color: '...', backgroundColor: '...' }}`)
- CSS module imports
- Styled-components / Emotion `css` blocks
- Tailwind classes (e.g. `text-gray-400 bg-white`)
- Theme tokens / design system variables

### Common problem patterns

#### Low-contrast placeholder text

```jsx
// BAD — light gray placeholder on white background, ratio ~1.9:1
<input
  placeholder="Enter email"
  style={{ color: '#333', backgroundColor: '#fff' }}
  // Browser default placeholder color is often ~#999 on #fff = ~2.8:1 FAIL
/>

// GOOD — ensure placeholder meets 4.5:1 (or 3:1 for large text)
// Use CSS:
// input::placeholder { color: #767676; } /* #767676 on #fff = 4.54:1 ✓ */
```

#### Gray text on gray background

```jsx
// BAD — #888 on #f5f5f5 = 3.5:1 (FAILS AA for normal text)
<p style={{ color: '#888', backgroundColor: '#f5f5f5' }}>
  Subtle note
</p>

// GOOD — #666 on #f5f5f5 = 5.2:1 ✓
<p style={{ color: '#666', backgroundColor: '#f5f5f5' }}>
  Subtle note
</p>
```

#### Information conveyed by color alone

```jsx
// BAD — only color distinguishes success/error
<span style={{ color: isValid ? 'green' : 'red' }}>
  {isValid ? 'Valid' : 'Invalid'}
</span>

// GOOD — color + icon + text
<span style={{ color: isValid ? '#137333' : '#c5221f' }}>
  {isValid ? '✓ Valid' : '✗ Invalid'}
</span>

// EVEN BETTER — add programmatic association
<span
  role="status"
  style={{ color: isValid ? '#137333' : '#c5221f' }}
  aria-label={isValid ? 'Validation passed' : 'Validation failed'}
>
  {isValid ? '✓ Valid' : '✗ Invalid'}
</span>
```

#### Focus indicator contrast

```css
/* BAD — light blue outline on white page, may not meet 3:1 */
button:focus {
  outline: 2px solid #90cdf4;
}

/* GOOD — darker blue meets 3:1 against white background */
button:focus-visible {
  outline: 2px solid #2b6cb0;
  outline-offset: 2px;
}
```

## Common color pairs and their ratios

Quick reference for frequently used combinations:

| Foreground | Background | Ratio | AA normal | AA large |
|-----------|------------|-------|-----------|----------|
| `#000000` | `#ffffff` | 21:1 | PASS | PASS |
| `#333333` | `#ffffff` | 12.6:1 | PASS | PASS |
| `#666666` | `#ffffff` | 5.7:1 | PASS | PASS |
| `#767676` | `#ffffff` | 4.5:1 | PASS | PASS |
| `#777777` | `#ffffff` | 4.5:1 | PASS | PASS |
| `#888888` | `#ffffff` | 3.5:1 | FAIL | PASS |
| `#999999` | `#ffffff` | 2.8:1 | FAIL | FAIL |
| `#aaaaaa` | `#ffffff` | 2.3:1 | FAIL | FAIL |
| `#ffffff` | `#0066cc` | 5.3:1 | PASS | PASS |
| `#ffffff` | `#1a73e8` | 4.6:1 | PASS | PASS |
| `#ffffff` | `#4285f4` | 3.3:1 | FAIL | PASS |
| `#ffffff` | `#ff6600` | 3.0:1 | FAIL | PASS |

## Tailwind CSS contrast gotchas

Common Tailwind classes that may fail contrast:

| Classes | Approximate ratio | Status |
|---------|-------------------|--------|
| `text-gray-400 bg-white` | ~3.0:1 | FAIL (normal text) |
| `text-gray-500 bg-white` | ~4.6:1 | PASS |
| `text-gray-300 bg-gray-900` | ~7.0:1 | PASS |
| `text-blue-400 bg-white` | ~3.0:1 | FAIL (normal text) |
| `text-blue-600 bg-white` | ~4.8:1 | PASS |
| `text-red-400 bg-white` | ~3.1:1 | FAIL (normal text) |
| `text-red-600 bg-white` | ~4.6:1 | PASS |

When auditing Tailwind code, flag any `text-{color}-300` or `text-{color}-400` on a white or
near-white background — these frequently fail AA.

## Dark mode considerations

- Contrast requirements apply in dark mode too
- Don't assume white text on dark backgrounds always passes (e.g. `#f0f0f0` on `#333` = 8.6:1 ✓, but `#888` on `#333` = 2.6:1 ✗)
- Check both light and dark theme if the component supports it
- Watch for hardcoded colors that don't adapt to theme changes

## Tools for verifying contrast

- **Browser DevTools**: Chrome/Firefox accessibility inspector shows contrast ratios
- **WebAIM Contrast Checker**: https://webaim.org/resources/contrastchecker/
- **Colour Contrast Analyser** (CCA): desktop app for measuring any on-screen colors
- **axe-core**: catches contrast issues in automated testing
- **Storybook a11y addon**: shows contrast ratio live in the component panel
