#!/usr/bin/env node

/**
 * Markdown to HTML converter with TOC, code highlighting, and KaTeX math.
 *
 * Usage:
 *   node convert.mjs <input.md> <output.html> [options]
 *
 * Options:
 *   --title "Title"   Override the page title
 *   --no-toc          Disable table of contents
 *   --theme dark      Use dark theme (default: light)
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

// Resolve skill directory for template lookup
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------
const args = process.argv.slice(2);

if (args.length < 2 || args.includes("--help") || args.includes("-h")) {
  console.error(
    "Usage: node convert.mjs <input.md> <output.html> [--title T] [--no-toc] [--theme dark|light]"
  );
  process.exit(1);
}

const inputPath = path.resolve(args[0]);
const outputPath = path.resolve(args[1]);

function getFlag(name, defaultValue) {
  const idx = args.indexOf(name);
  if (idx === -1) return defaultValue;
  if (typeof defaultValue === "boolean") return true;
  return args[idx + 1] || defaultValue;
}

const noToc = args.includes("--no-toc");
const theme = getFlag("--theme", "light");
const customTitle = getFlag("--title", "");

// ---------------------------------------------------------------------------
// Load dependencies
// ---------------------------------------------------------------------------
let marked, hljs, katex;

try {
  ({ marked } = await import("marked"));
  hljs = (await import("highlight.js")).default;
  katex = (await import("katex")).default;
} catch (e) {
  console.error(
    "Missing dependencies. Install them with:\n  npm install --no-save marked highlight.js katex"
  );
  console.error(e.message);
  process.exit(1);
}

// ---------------------------------------------------------------------------
// Read input
// ---------------------------------------------------------------------------
if (!fs.existsSync(inputPath)) {
  console.error(`Input file not found: ${inputPath}`);
  process.exit(1);
}

const mdContent = fs.readFileSync(inputPath, "utf-8");

// ---------------------------------------------------------------------------
// KaTeX pre-processing
// ---------------------------------------------------------------------------
// Replace $$...$$ (display) and $...$ (inline) BEFORE marked processes the text.
// We use placeholders to avoid marked escaping the HTML.

const mathPlaceholders = [];

function placeholderKey(index) {
  return `%%%MATH_PLACEHOLDER_${index}%%%`;
}

function renderKatex(latex, displayMode) {
  try {
    return katex.renderToString(latex, {
      displayMode,
      throwOnError: false,
      output: "html",
    });
  } catch (err) {
    // Return raw latex wrapped in a code element on error
    const escapedLatex = latex
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return displayMode
      ? `<pre class="katex-error"><code>${escapedLatex}</code></pre>`
      : `<code class="katex-error">${escapedLatex}</code>`;
  }
}

// Display math: $$...$$  (must come before inline to avoid conflicts)
let processed = mdContent.replace(
  /\$\$([\s\S]+?)\$\$/g,
  (_match, latex) => {
    const html = renderKatex(latex.trim(), true);
    const idx = mathPlaceholders.length;
    mathPlaceholders.push(html);
    return placeholderKey(idx);
  }
);

// Inline math: $...$  (avoid matching $$ and currency like $100)
processed = processed.replace(
  /(?<!\$)\$(?!\$)(?!\d)(.+?)(?<!\$)\$(?!\$)/g,
  (_match, latex) => {
    const html = renderKatex(latex.trim(), false);
    const idx = mathPlaceholders.length;
    mathPlaceholders.push(html);
    return placeholderKey(idx);
  }
);

// ---------------------------------------------------------------------------
// Heading collection for TOC
// ---------------------------------------------------------------------------
const tocItems = [];
let headingCounter = 0;

const renderer = new marked.Renderer();

const originalHeading = renderer.heading.bind(renderer);

renderer.heading = function ({ text, depth }) {
  if (depth >= 2 && depth <= 4) {
    headingCounter++;
    const id = `heading-${headingCounter}`;
    tocItems.push({ id, text, depth });
    return `<h${depth} id="${id}">${text}</h${depth}>`;
  }
  headingCounter++;
  const id = `heading-${headingCounter}`;
  return `<h${depth} id="${id}">${text}</h${depth}>`;
};

// ---------------------------------------------------------------------------
// Configure marked
// ---------------------------------------------------------------------------
marked.setOptions({
  renderer,
  highlight: function (code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value;
    }
    return hljs.highlightAuto(code).value;
  },
  gfm: true,
  breaks: false,
});

// ---------------------------------------------------------------------------
// Render Markdown -> HTML body
// ---------------------------------------------------------------------------
let bodyHtml = marked.parse(processed);

// Restore math placeholders
for (let i = 0; i < mathPlaceholders.length; i++) {
  bodyHtml = bodyHtml.replace(placeholderKey(i), mathPlaceholders[i]);
}

// ---------------------------------------------------------------------------
// Build TOC HTML
// ---------------------------------------------------------------------------
let tocHtml = "";
if (!noToc && tocItems.length > 0) {
  tocHtml += '<nav class="toc" aria-label="Table of Contents">\n';
  tocHtml += "<h2>Table of Contents</h2>\n<ul>\n";
  for (const item of tocItems) {
    const indent = "  ".repeat(item.depth - 2);
    tocHtml += `${indent}<li class="toc-level-${item.depth}"><a href="#${item.id}">${item.text}</a></li>\n`;
  }
  tocHtml += "</ul>\n</nav>\n";
}

// ---------------------------------------------------------------------------
// Determine page title
// ---------------------------------------------------------------------------
let pageTitle = customTitle;
if (!pageTitle) {
  // Try to extract first h1 from original markdown
  const h1Match = mdContent.match(/^#\s+(.+)$/m);
  if (h1Match) {
    pageTitle = h1Match[1].trim();
  } else {
    pageTitle = path.basename(inputPath, path.extname(inputPath));
  }
}

// ---------------------------------------------------------------------------
// Load and fill template
// ---------------------------------------------------------------------------
const templatePath = path.join(__dirname, "template.html");
let templateHtml;

if (fs.existsSync(templatePath)) {
  templateHtml = fs.readFileSync(templatePath, "utf-8");
} else {
  // Fallback inline template
  templateHtml = `<!DOCTYPE html>
<html lang="en" data-theme="{{THEME}}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}}</title>
{{HEAD_ASSETS}}
<style>body{font-family:sans-serif;max-width:800px;margin:2rem auto;padding:0 1rem;}</style>
</head>
<body>
{{TOC}}
<main>{{BODY}}</main>
</body>
</html>`;
}

// Replace placeholders
const themeClass = theme === "dark" ? "dark" : "light";

const output = templateHtml
  .replace(/\{\{TITLE\}\}/g, pageTitle)
  .replace(/\{\{THEME\}\}/g, themeClass)
  .replace(/\{\{TOC\}\}/g, tocHtml)
  .replace(/\{\{BODY\}\}/g, bodyHtml);

// ---------------------------------------------------------------------------
// Write output
// ---------------------------------------------------------------------------
fs.mkdirSync(path.dirname(outputPath), { recursive: true });
fs.writeFileSync(outputPath, output, "utf-8");

console.log(`Converted: ${inputPath}`);
console.log(`Output:    ${outputPath}`);
console.log(`Title:     ${pageTitle}`);
console.log(`Theme:     ${themeClass}`);
console.log(`TOC items: ${tocItems.length}`);
console.log(`Math formulas processed: ${mathPlaceholders.length}`);
