# Component Pattern Accessibility Reference

Accessible implementations of common React UI patterns, following WAI-ARIA Authoring Practices.

## Modal / Dialog

### Requirements
- `role="dialog"` and `aria-modal="true"`
- Labeled with `aria-labelledby` (pointing to the title) or `aria-label`
- Focus moves into the dialog on open
- Focus is trapped inside while open
- `Escape` closes the dialog
- Focus returns to the trigger element on close
- Background content is inert (`inert` attribute or `aria-hidden="true"` on siblings)

### Reference implementation

```jsx
function Dialog({ isOpen, onClose, title, children }) {
  const dialogRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement;
      // Use native <dialog> for built-in inertness and focus management
      dialogRef.current?.showModal();
    } else {
      dialogRef.current?.close();
      triggerRef.current?.focus();
    }
  }, [isOpen]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="dialog-title"
      onClose={onClose}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
    >
      <h2 id="dialog-title">{title}</h2>
      {children}
      <button onClick={onClose}>Close</button>
    </dialog>
  );
}
```

### Common mistakes
- Using `<div>` instead of `<dialog>` — loses free focus trapping and inertness
- Missing `aria-modal="true"` on custom dialog implementations
- Not returning focus on close
- Forgetting `Escape` key handling
- Not labeling the dialog

---

## Tabs

### Requirements
- Container: `role="tablist"`
- Each tab: `role="tab"`, `aria-selected="true|false"`, `aria-controls="panelId"`
- Each panel: `role="tabpanel"`, `aria-labelledby="tabId"`
- Arrow keys navigate between tabs
- Only the active tab is in the tab order (`tabIndex={0}`), inactive tabs get `tabIndex={-1}`
- `Home` / `End` move to first / last tab

### Reference implementation

```jsx
function Tabs({ tabs }) {
  const [activeIndex, setActiveIndex] = useState(0);

  const handleKeyDown = (e, index) => {
    let newIndex = index;
    switch (e.key) {
      case 'ArrowRight':
        newIndex = (index + 1) % tabs.length;
        break;
      case 'ArrowLeft':
        newIndex = (index - 1 + tabs.length) % tabs.length;
        break;
      case 'Home':
        newIndex = 0;
        break;
      case 'End':
        newIndex = tabs.length - 1;
        break;
      default:
        return;
    }
    e.preventDefault();
    setActiveIndex(newIndex);
    document.getElementById(`tab-${newIndex}`)?.focus();
  };

  return (
    <div>
      <div role="tablist" aria-label="Content sections">
        {tabs.map((tab, i) => (
          <button
            key={i}
            id={`tab-${i}`}
            role="tab"
            aria-selected={i === activeIndex}
            aria-controls={`panel-${i}`}
            tabIndex={i === activeIndex ? 0 : -1}
            onClick={() => setActiveIndex(i)}
            onKeyDown={(e) => handleKeyDown(e, i)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {tabs.map((tab, i) => (
        <div
          key={i}
          id={`panel-${i}`}
          role="tabpanel"
          aria-labelledby={`tab-${i}`}
          hidden={i !== activeIndex}
          tabIndex={0}
        >
          {tab.content}
        </div>
      ))}
    </div>
  );
}
```

### Common mistakes
- All tabs in the tab order (should be roving tabindex)
- Missing `aria-selected`
- Using `display: none` or conditional rendering instead of `hidden` attribute (both work, but must use one)
- Missing keyboard navigation between tabs

---

## Dropdown Menu

### Requirements
- Trigger button: `aria-haspopup="true"`, `aria-expanded="true|false"`
- Menu container: `role="menu"`
- Menu items: `role="menuitem"`
- Arrow keys navigate items
- `Escape` closes the menu and returns focus to trigger
- `Enter` / `Space` activate an item
- Focus moves to first item on open

### Reference implementation

```jsx
function DropdownMenu({ label, items }) {
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const triggerRef = useRef(null);
  const itemRefs = useRef([]);

  const open = () => {
    setIsOpen(true);
    setActiveIndex(0);
  };

  const close = () => {
    setIsOpen(false);
    setActiveIndex(-1);
    triggerRef.current?.focus();
  };

  useEffect(() => {
    if (isOpen && activeIndex >= 0) {
      itemRefs.current[activeIndex]?.focus();
    }
  }, [isOpen, activeIndex]);

  const handleMenuKeyDown = (e) => {
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setActiveIndex((prev) => (prev + 1) % items.length);
        break;
      case 'ArrowUp':
        e.preventDefault();
        setActiveIndex((prev) => (prev - 1 + items.length) % items.length);
        break;
      case 'Escape':
        close();
        break;
      case 'Home':
        e.preventDefault();
        setActiveIndex(0);
        break;
      case 'End':
        e.preventDefault();
        setActiveIndex(items.length - 1);
        break;
    }
  };

  return (
    <div>
      <button
        ref={triggerRef}
        aria-haspopup="true"
        aria-expanded={isOpen}
        onClick={() => (isOpen ? close() : open())}
      >
        {label}
      </button>
      {isOpen && (
        <ul role="menu" onKeyDown={handleMenuKeyDown}>
          {items.map((item, i) => (
            <li
              key={i}
              role="menuitem"
              tabIndex={-1}
              ref={(el) => (itemRefs.current[i] = el)}
              onClick={() => {
                item.action();
                close();
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  item.action();
                  close();
                }
              }}
            >
              {item.label}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

---

## Accordion

### Requirements
- Each header: `<button>` (or element with `role="button"`) with `aria-expanded="true|false"`
- Header button controls its panel: `aria-controls="panelId"`
- Panel: `role="region"` with `aria-labelledby="headerId"`
- `Enter` / `Space` toggle the section
- Optional: arrow keys between headers, `Home` / `End` for first / last

### Common mistakes

```jsx
// BAD — div as accordion header
<div className="accordion-header" onClick={() => toggle(i)}>
  {section.title}
</div>

// GOOD
<h3>
  <button
    id={`accordion-header-${i}`}
    aria-expanded={openIndex === i}
    aria-controls={`accordion-panel-${i}`}
    onClick={() => toggle(i)}
  >
    {section.title}
  </button>
</h3>
<div
  id={`accordion-panel-${i}`}
  role="region"
  aria-labelledby={`accordion-header-${i}`}
  hidden={openIndex !== i}
>
  {section.content}
</div>
```

---

## Tooltip

### Requirements
- Trigger element has `aria-describedby` pointing to tooltip `id`
- Tooltip has `role="tooltip"`
- Shows on focus AND hover (not just hover)
- `Escape` dismisses the tooltip
- Tooltip does not contain interactive content (use a popover/dialog for that)

### Reference implementation

```jsx
function Tooltip({ content, children }) {
  const [visible, setVisible] = useState(false);
  const id = useId();

  return (
    <span
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
      onKeyDown={(e) => {
        if (e.key === 'Escape') setVisible(false);
      }}
    >
      <span aria-describedby={visible ? id : undefined}>
        {children}
      </span>
      {visible && (
        <span id={id} role="tooltip" className="tooltip">
          {content}
        </span>
      )}
    </span>
  );
}
```

### Common mistakes
- Only showing tooltip on hover — keyboard users can't see it
- Making tooltip content interactive (links, buttons) — use a dialog instead
- Missing `role="tooltip"` and `aria-describedby` relationship

---

## Data Table

### Requirements
- Use `<table>`, `<thead>`, `<tbody>`, `<th>`, `<td>` — native semantics
- Column headers: `<th scope="col">`
- Row headers: `<th scope="row">`
- Table must have a caption or `aria-label` / `aria-labelledby`
- Sortable columns: `aria-sort="ascending|descending|none"` on `<th>`
- Complex tables with merged cells need `headers` attribute on `<td>`

### Common mistakes

```jsx
// BAD — CSS grid as table without ARIA
<div className="grid grid-cols-3">
  <div className="font-bold">Name</div>
  <div className="font-bold">Role</div>
  <div className="font-bold">Status</div>
  {data.map(row => (
    <>
      <div>{row.name}</div>
      <div>{row.role}</div>
      <div>{row.status}</div>
    </>
  ))}
</div>

// GOOD — semantic table
<table aria-label="Team members">
  <thead>
    <tr>
      <th scope="col">Name</th>
      <th scope="col">Role</th>
      <th scope="col">Status</th>
    </tr>
  </thead>
  <tbody>
    {data.map(row => (
      <tr key={row.id}>
        <td>{row.name}</td>
        <td>{row.role}</td>
        <td>{row.status}</td>
      </tr>
    ))}
  </tbody>
</table>
```

---

## Autocomplete / Combobox

### Requirements
- Input: `role="combobox"`, `aria-expanded`, `aria-controls`, `aria-autocomplete`
- Listbox: `role="listbox"` with `role="option"` children
- Active option: `aria-activedescendant` on input, `aria-selected` on option
- Arrow keys navigate options, `Enter` selects, `Escape` closes
- Screen reader should announce number of results

### Key ARIA attributes

```jsx
<input
  role="combobox"
  aria-expanded={isListOpen}
  aria-controls="listbox-id"
  aria-activedescendant={activeOptionId}
  aria-autocomplete="list"
  aria-haspopup="listbox"
/>
<ul id="listbox-id" role="listbox" aria-label="Suggestions">
  {options.map((opt, i) => (
    <li
      key={opt.id}
      id={`option-${opt.id}`}
      role="option"
      aria-selected={i === activeIndex}
    >
      {opt.label}
    </li>
  ))}
</ul>
```

---

## General pattern: screen reader-only text

Use a utility class to visually hide text while keeping it accessible:

```css
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

```jsx
// Usage: icon-only button with screen reader label
<button onClick={onDelete}>
  <TrashIcon aria-hidden="true" />
  <span className="sr-only">Delete item</span>
</button>
```

This is sometimes better than `aria-label` because it also works with browser translation tools
(which don't translate ARIA attributes).
