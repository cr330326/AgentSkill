# Keyboard Navigation Reference

## Core principles

1. **All interactive elements must be operable with keyboard alone** — no mouse required
2. **Focus must be visible** — users must see where focus is at all times
3. **Focus order must be logical** — typically follows reading order (left-to-right, top-to-bottom in LTR locales)
4. **No keyboard traps** — except for intentional modal focus traps that can be dismissed with Escape

## Tab order

### Making elements focusable

| Element | Focusable by default? | Tabbable by default? |
|---------|----------------------|---------------------|
| `<a href>` | Yes | Yes |
| `<button>` | Yes | Yes |
| `<input>`, `<select>`, `<textarea>` | Yes | Yes |
| `<div>`, `<span>`, `<p>` | No | No |
| `<div tabIndex={0}>` | Yes | Yes |
| `<div tabIndex={-1}>` | Yes (programmatic only) | No |

### Common issues

#### Click handler on non-focusable element

```jsx
// BAD — div with onClick but not keyboard-accessible
<div onClick={handleClick} className="card">
  <h3>{title}</h3>
  <p>{description}</p>
</div>

// GOOD — use a button or add keyboard support
<div
  role="button"
  tabIndex={0}
  onClick={handleClick}
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick();
    }
  }}
  className="card"
>
  <h3>{title}</h3>
  <p>{description}</p>
</div>

// BETTER — just use a button
<button onClick={handleClick} className="card">
  <h3>{title}</h3>
  <p>{description}</p>
</button>
```

#### Positive tabIndex

```jsx
// BAD — positive tabIndex creates unpredictable focus order
<input tabIndex={3} />
<input tabIndex={1} />
<input tabIndex={2} />

// GOOD — use DOM order + tabIndex={0} when needed
<input />
<input />
<input />
```

Never use `tabIndex` values greater than 0. They override the natural DOM order and create
maintenance nightmares. Reorder elements in the DOM instead.

## Focus visibility

### Removing focus outlines breaks accessibility

```css
/* BAD — removes focus indicator entirely */
*:focus {
  outline: none;
}

/* GOOD — custom focus style that's clearly visible */
*:focus-visible {
  outline: 2px solid #4A90D9;
  outline-offset: 2px;
}

/* GOOD — remove default only when providing a better alternative */
button:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.5);
}
```

Use `:focus-visible` to show focus rings only during keyboard navigation (not mouse clicks).

### Checking focus visibility in React

```jsx
// BAD — inline styles that remove outline
<button style={{ outline: 'none' }} onClick={onClick}>
  Click me
</button>

// Check CSS modules / styled-components for outline: none / outline: 0
```

## Focus management

### Modal / Dialog focus

```jsx
function Modal({ isOpen, onClose, children }) {
  const modalRef = useRef(null);
  const previousFocusRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      // Save the element that had focus before the modal opened
      previousFocusRef.current = document.activeElement;
      // Move focus into the modal
      modalRef.current?.focus();
    }

    return () => {
      // Return focus to the previously focused element
      if (previousFocusRef.current) {
        previousFocusRef.current.focus();
      }
    };
  }, [isOpen]);

  // Trap focus inside modal
  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      onClose();
      return;
    }

    if (e.key === 'Tab') {
      const focusable = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      ref={modalRef}
      tabIndex={-1}
      onKeyDown={handleKeyDown}
    >
      {children}
    </div>
  );
}
```

### Focus after conditional rendering

```jsx
// BAD — focus is lost when the element disappears
{showDetails && <DetailsPanel />}
<button onClick={() => setShowDetails(!showDetails)}>
  Toggle details
</button>

// GOOD — manage focus when content is removed
const detailsRef = useRef(null);
const toggleRef = useRef(null);

useEffect(() => {
  if (showDetails) {
    detailsRef.current?.focus();
  } else {
    // If details were just hidden, return focus to the toggle
    toggleRef.current?.focus();
  }
}, [showDetails]);
```

### Skip navigation link

```jsx
// Provide a skip link as the first focusable element on the page
function SkipLink() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:p-3 focus:bg-white focus:text-black"
    >
      Skip to main content
    </a>
  );
}

// Target
<main id="main-content" tabIndex={-1}>
  ...
</main>
```

## Key bindings for common widget patterns

These follow WAI-ARIA Authoring Practices:

### Tabs
| Key | Action |
|-----|--------|
| `Tab` | Move into / out of the tab list |
| `ArrowLeft` / `ArrowRight` | Switch between tabs (horizontal) |
| `ArrowUp` / `ArrowDown` | Switch between tabs (vertical) |
| `Home` | First tab |
| `End` | Last tab |

### Menu
| Key | Action |
|-----|--------|
| `Enter` / `Space` | Activate menu item |
| `ArrowUp` / `ArrowDown` | Navigate items |
| `Escape` | Close menu |
| `Home` | First item |
| `End` | Last item |

### Accordion
| Key | Action |
|-----|--------|
| `Enter` / `Space` | Toggle section |
| `ArrowUp` / `ArrowDown` | Move between headers |
| `Home` | First header |
| `End` | Last header |

### Tree view
| Key | Action |
|-----|--------|
| `ArrowUp` / `ArrowDown` | Navigate items |
| `ArrowRight` | Expand node / move to first child |
| `ArrowLeft` | Collapse node / move to parent |
| `Enter` | Activate item |
| `Home` / `End` | First / last visible item |

### Combobox / Autocomplete
| Key | Action |
|-----|--------|
| `ArrowDown` | Open list / move to next option |
| `ArrowUp` | Move to previous option |
| `Enter` | Select current option |
| `Escape` | Close list |
| Type characters | Filter options |
