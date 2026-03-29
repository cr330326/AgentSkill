# ARIA Component Patterns — React Quick Reference

Canonical patterns derived from [WAI-ARIA Authoring Practices 1.2](https://www.w3.org/WAI/ARIA/apg/).
Each pattern shows the minimal ARIA attributes and keyboard interactions required.

---

## Modal / Dialog

```tsx
<div
  role="dialog"
  aria-modal="true"
  aria-labelledby="dialog-title"
  aria-describedby="dialog-desc"  // optional
  tabIndex={-1}                   // receives initial focus
>
  <h2 id="dialog-title">Confirm Deletion</h2>
  <p id="dialog-desc">This action cannot be undone.</p>
  <button>Cancel</button>
  <button>Delete</button>
</div>
```

**Keyboard:**
| Key | Action |
|-----|--------|
| Tab / Shift+Tab | Cycle through focusable elements within dialog |
| Escape | Close dialog, return focus to trigger element |

**Checklist:**
- [ ] Focus moves into dialog on open
- [ ] Focus is trapped inside dialog
- [ ] Focus returns to trigger element on close
- [ ] Background content has `aria-hidden="true"` or `inert` attribute

---

## Dropdown Menu

```tsx
<div>
  <button
    aria-haspopup="true"
    aria-expanded={isOpen}
    aria-controls="menu-list"
  >
    Options
  </button>
  {isOpen && (
    <ul id="menu-list" role="menu">
      <li role="menuitem" tabIndex={-1}>Edit</li>
      <li role="menuitem" tabIndex={-1}>Duplicate</li>
      <li role="separator" />
      <li role="menuitem" tabIndex={-1}>Delete</li>
    </ul>
  )}
</div>
```

**Keyboard:**
| Key | Action |
|-----|--------|
| Enter / Space / ArrowDown | Open menu, focus first item |
| ArrowUp / ArrowDown | Move between items |
| Escape | Close menu, focus trigger |
| Home / End | Jump to first / last item |
| Letter key | Jump to next item starting with that letter |

**Checklist:**
- [ ] Only one item in the menu has `tabIndex={0}` at a time (roving tabindex)
- [ ] Menu closes on Escape and on click outside
- [ ] `aria-expanded` reflects open/closed state

---

## Tabs

```tsx
<div>
  <div role="tablist" aria-label="Account settings">
    <button role="tab" aria-selected={activeTab === 0} aria-controls="panel-0" id="tab-0" tabIndex={activeTab === 0 ? 0 : -1}>
      Profile
    </button>
    <button role="tab" aria-selected={activeTab === 1} aria-controls="panel-1" id="tab-1" tabIndex={activeTab === 1 ? 0 : -1}>
      Security
    </button>
  </div>
  <div role="tabpanel" id="panel-0" aria-labelledby="tab-0" hidden={activeTab !== 0} tabIndex={0}>
    {/* Profile content */}
  </div>
  <div role="tabpanel" id="panel-1" aria-labelledby="tab-1" hidden={activeTab !== 1} tabIndex={0}>
    {/* Security content */}
  </div>
</div>
```

**Keyboard:**
| Key | Action |
|-----|--------|
| ArrowLeft / ArrowRight | Switch between tabs |
| Home / End | Jump to first / last tab |
| Tab | Move focus from tab to tab panel content |

**Checklist:**
- [ ] Only active tab has `tabIndex={0}`; inactive tabs have `tabIndex={-1}`
- [ ] `aria-selected` reflects active state
- [ ] Each tab has matching `aria-controls` and panel has `aria-labelledby`

---

## Accordion

```tsx
<div>
  {sections.map((section, i) => (
    <div key={i}>
      <h3>
        <button
          aria-expanded={expanded === i}
          aria-controls={`section-${i}`}
          id={`header-${i}`}
        >
          {section.title}
        </button>
      </h3>
      <div
        id={`section-${i}`}
        role="region"
        aria-labelledby={`header-${i}`}
        hidden={expanded !== i}
      >
        {section.content}
      </div>
    </div>
  ))}
</div>
```

**Keyboard:**
| Key | Action |
|-----|--------|
| Enter / Space | Toggle section |
| ArrowDown / ArrowUp | Move to next / previous header (optional) |
| Home / End | Move to first / last header (optional) |

**Checklist:**
- [ ] `aria-expanded` reflects open/closed state
- [ ] Panel region has `aria-labelledby` pointing to its header

---

## Tooltip

```tsx
<div style={{ position: 'relative' }}>
  <button
    aria-describedby={showTip ? 'tooltip-1' : undefined}
    onMouseEnter={() => setShowTip(true)}
    onMouseLeave={() => setShowTip(false)}
    onFocus={() => setShowTip(true)}
    onBlur={() => setShowTip(false)}
  >
    Settings
  </button>
  {showTip && (
    <div id="tooltip-1" role="tooltip">
      Manage your account settings
    </div>
  )}
</div>
```

**Keyboard:**
| Key | Action |
|-----|--------|
| Escape | Dismiss tooltip without closing other things |
| Focus / Blur | Show / hide tooltip on keyboard focus |

**Checklist:**
- [ ] Tooltip appears on focus, not just hover
- [ ] Tooltip uses `role="tooltip"` and trigger uses `aria-describedby`
- [ ] Tooltip is dismissible with Escape
- [ ] Tooltip does not contain interactive content (use a popover instead)

---

## Combobox / Autocomplete

```tsx
<div>
  <label htmlFor="search-input">Search users</label>
  <input
    id="search-input"
    role="combobox"
    aria-expanded={suggestions.length > 0}
    aria-autocomplete="list"
    aria-controls="suggestions-list"
    aria-activedescendant={activeId}  // id of highlighted option
  />
  {suggestions.length > 0 && (
    <ul id="suggestions-list" role="listbox">
      {suggestions.map((s) => (
        <li
          key={s.id}
          id={`option-${s.id}`}
          role="option"
          aria-selected={activeId === `option-${s.id}`}
        >
          {s.name}
        </li>
      ))}
    </ul>
  )}
</div>
```

**Keyboard:**
| Key | Action |
|-----|--------|
| ArrowDown / ArrowUp | Navigate suggestions |
| Enter | Select highlighted suggestion |
| Escape | Close suggestion list |
| Typing | Filter / update suggestions |

**Checklist:**
- [ ] `aria-activedescendant` updates as user arrows through options
- [ ] `aria-expanded` reflects whether listbox is visible
- [ ] Input has explicit `<label>`

---

## Toast / Notification

```tsx
// Container — always present in DOM
<div aria-live="polite" aria-atomic="true" className="toast-container">
  {toasts.map((toast) => (
    <div key={toast.id} role="status" className="toast">
      <span>{toast.message}</span>
      <button aria-label={`Dismiss: ${toast.message}`} onClick={() => dismiss(toast.id)}>
        <XIcon aria-hidden="true" />
      </button>
    </div>
  ))}
</div>
```

**Key decisions:**

| Urgency | `aria-live` value | `role` |
|---------|-------------------|--------|
| Informational (success, info) | `polite` | `status` |
| Urgent (error, warning) | `assertive` | `alert` |

**Checklist:**
- [ ] Live region container exists in DOM before toast content is inserted
- [ ] Dismiss button has accessible name
- [ ] Toasts do not auto-dismiss too quickly (minimum 5 seconds recommended)
- [ ] Error toasts use `role="alert"` and `aria-live="assertive"`
