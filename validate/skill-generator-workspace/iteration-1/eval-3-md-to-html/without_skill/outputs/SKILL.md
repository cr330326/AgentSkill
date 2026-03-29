---
name: md-to-html
description: >
  Converts Markdown files to standalone HTML with auto-generated table of contents,
  syntax-highlighted code blocks, and KaTeX math formula rendering. Use when the user
  asks to "convert markdown to html", "md to html", "generate html from markdown",
  "markdown with TOC", or needs a styled HTML page from a .md file.
---

# Markdown to HTML Converter

Convert Markdown files into self-contained, styled HTML pages with:
- **Auto-generated Table of Contents** from headings (h2-h4)
- **Syntax-highlighted code blocks** via highlight.js
- **Math formula rendering** via KaTeX (inline `$...$` and display `$$...$$`)

## Prerequisites

The conversion script requires three npm packages. Install them before first use:

```bash
npm install --no-save marked highlight.js katex
```

Check that they are available:

```bash
node -e "require('marked'); require('highlight.js'); require('katex'); console.log('OK')"
```

If the check prints `OK`, proceed. If it fails, install them in a temporary location:

```bash
npm install --prefix /tmp/md-to-html marked highlight.js katex
```

Then run the convert script with `NODE_PATH=/tmp/md-to-html/node_modules`.

## Workflow

### Step 1: Identify the input file

- The user provides a `.md` file path (absolute or relative).
- Read the file to confirm it exists and is valid Markdown.

### Step 2: Determine output path

- Default: same directory and basename as input, with `.html` extension.
  - Example: `notes.md` -> `notes.html`
- If the user specifies an output path, use that instead.

### Step 3: Run the conversion

Execute the bundled conversion script:

```bash
node "<skill-directory>/convert.mjs" "<input.md>" "<output.html>"
```

Replace `<skill-directory>` with the absolute path to the directory containing this SKILL.md.

The script:
1. Reads the Markdown file.
2. Extracts headings (h2-h4) to build a table of contents.
3. Converts `$...$` to inline KaTeX and `$$...$$` to display KaTeX.
4. Renders Markdown to HTML via `marked` with highlight.js for code blocks.
5. Injects everything into the HTML template (`template.html` in the same directory).
6. Writes the final self-contained HTML file.

### Step 4: Report the result

Tell the user:
- The output file path.
- How many headings were found for the TOC.
- Remind them the HTML is fully self-contained (all CSS/JS loaded from CDNs) and can be opened directly in a browser.

## Options

| Flag | Description | Default |
|------|-------------|---------|
| `--title "Custom Title"` | Override the page title | First h1 or filename |
| `--no-toc` | Disable table of contents generation | TOC enabled |
| `--theme dark` | Use dark color scheme | `light` |

Example with options:

```bash
node "<skill-directory>/convert.mjs" input.md output.html --title "My Notes" --theme dark
```

## Error Handling

| Error | Resolution |
|-------|------------|
| `Cannot find module 'marked'` | Run `npm install --no-save marked highlight.js katex` |
| Input file not found | Verify the path. Use the Read tool to check it exists. |
| KaTeX parse error | The math formula has syntax errors. Show the user the specific formula and the error message so they can fix it. KaTeX errors are non-fatal; the raw LaTeX is preserved in the output. |

## Example

User says: "Convert my README.md to HTML"

```bash
# 1. Install deps if needed
npm install --no-save marked highlight.js katex

# 2. Convert
node "/path/to/skill/convert.mjs" README.md README.html

# 3. Done - README.html is ready to open in a browser
```

## Limitations

- External images referenced in Markdown are not embedded; they remain as URLs.
- Very large files (>10MB) may be slow to process.
- KaTeX supports most LaTeX math but not every package. See https://katex.org/docs/supported for coverage.
