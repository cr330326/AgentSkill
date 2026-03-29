---
name: md-to-html
description: >
  Convert Markdown files to standalone HTML with auto-generated table of contents,
  syntax-highlighted code blocks, and rendered math formulas (KaTeX).
  Use this skill when the user wants to convert markdown to HTML, says "markdown to html",
  "md to html", "convert md", "generate html from markdown", "md转html", "markdown转html",
  or needs an HTML page with a TOC, code highlighting, or math rendering from a .md source.
  Also use when the user mentions "带目录的HTML", "代码高亮", "数学公式", or wants a
  self-contained HTML file from markdown content.
  Do NOT use for publishing to WeChat or other platforms (use baoyu-markdown-to-html or
  baoyu-post-to-wechat instead). Do NOT use for editing markdown itself (use a text editor).
---

# Markdown to HTML Converter

Convert Markdown files into self-contained HTML pages with a clickable table of contents,
syntax-highlighted code blocks, and beautifully rendered math formulas.

## Prerequisites

Node.js (>=16) must be available. On first run, install the required packages:

```bash
npm install marked marked-gfm-heading-id highlight.js katex
```

These four packages provide:

| Package | Purpose |
|---------|---------|
| `marked` | Markdown parsing to HTML |
| `marked-gfm-heading-id` | Generates heading IDs for TOC anchor links |
| `highlight.js` | Syntax highlighting for fenced code blocks |
| `katex` | Math formula rendering (inline `$...$` and display `$$...$$`) |

## When to use

- Convert a single `.md` file to a styled, standalone `.html` file
- Generate documentation pages with a sidebar or inline table of contents
- Produce HTML that renders code blocks with syntax colors
- Render LaTeX math notation in markdown to proper HTML math output
- Create self-contained HTML (all CSS inlined, no external dependencies at runtime)

## Workflow

### Step 1: Identify the input

Locate the markdown file the user wants to convert. Accept either:
- A file path to an existing `.md` file
- Raw markdown content provided inline

If the user provides raw content, save it to a temporary `.md` file first.

### Step 2: Run the conversion script

Execute the bundled conversion script:

```bash
node scripts/convert.mjs <input.md> [output.html]
```

- If `output.html` is omitted, it defaults to the input filename with a `.html` extension
  (e.g., `README.md` becomes `README.html`).
- The script is located in this skill's `scripts/` directory.

### Step 3: Verify and deliver

After conversion:
1. Confirm the output file was created and is non-empty
2. Report the output path to the user
3. If the user wants to preview it, suggest opening in a browser

## Features

### Table of Contents

The converter scans all `##` through `####` headings and generates a clickable TOC
at the top of the HTML document. Each TOC entry links to the corresponding heading
via anchor IDs.

### Code highlighting

Fenced code blocks with a language tag are highlighted using highlight.js. Example:

~~~markdown
```python
def greet(name):
    return f"Hello, {name}!"
```
~~~

This renders with Python syntax colors in the output HTML.

Supported languages include all languages bundled with highlight.js (Python, JavaScript,
TypeScript, Go, Rust, Java, C/C++, SQL, Bash, JSON, YAML, and many more).

### Math formulas

Both inline and display math are supported via KaTeX:

- **Inline math:** `$E = mc^2$` renders inline within text
- **Display math:** `$$\int_0^\infty e^{-x^2} dx = \frac{\sqrt{\pi}}{2}$$` renders as a centered block

Math is pre-rendered to HTML at build time, so the output HTML needs no JavaScript at runtime.

## Options

| Flag / Argument | Default | Description |
|-----------------|---------|-------------|
| First positional arg | (required) | Path to input `.md` file |
| Second positional arg | `<input>.html` | Path to output `.html` file |

## Tips

- The output HTML is fully self-contained (inlined CSS, no external requests). Share it
  as a single file or open it offline.
- For math-heavy documents, make sure to use proper LaTeX syntax inside `$` or `$$` delimiters.
- If a code block has no language tag, it renders as plain preformatted text without highlighting.
- The generated TOC only includes `##`, `###`, and `####` headings. Top-level `#` is treated
  as the document title and is not repeated in the TOC.

## Example

**Input:** `notes.md`
```markdown
# My Notes

## Introduction
Some introductory text with inline math $a^2 + b^2 = c^2$.

## Code Example
```python
print("hello")
```

## Conclusion
$$\sum_{i=1}^{n} i = \frac{n(n+1)}{2}$$
```

**Command:**
```bash
node scripts/convert.mjs notes.md notes.html
```

**Result:** A styled `notes.html` with:
- A clickable TOC listing "Introduction", "Code Example", "Conclusion"
- The Python code block rendered with syntax colors
- Both math formulas rendered as proper typeset math
