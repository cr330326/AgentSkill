#!/usr/bin/env node

/**
 * convert.mjs -- Markdown to self-contained HTML converter
 *
 * Features:
 *   - Auto-generated table of contents from ## / ### / #### headings
 *   - Syntax-highlighted code blocks via highlight.js
 *   - KaTeX math rendering for $...$ (inline) and $$...$$ (display)
 *   - Fully self-contained output (all CSS inlined)
 *
 * Usage:
 *   node convert.mjs <input.md> [output.html]
 */

import { readFileSync, writeFileSync } from "fs";
import { basename } from "path";
import { Marked } from "marked";
import { gfmHeadingId, getHeadingList } from "marked-gfm-heading-id";
import hljs from "highlight.js";
import katex from "katex";

// ---------------------------------------------------------------------------
// Args
// ---------------------------------------------------------------------------
const inputPath = process.argv[2];
if (!inputPath) {
  console.error("Usage: node convert.mjs <input.md> [output.html]");
  process.exit(1);
}
const outputPath =
  process.argv[3] || inputPath.replace(/\.md$/i, "") + ".html";

const mdSource = readFileSync(inputPath, "utf-8");

// ---------------------------------------------------------------------------
// KaTeX pre-processing: replace math delimiters before marked sees them
// ---------------------------------------------------------------------------
function renderMath(src) {
  // Display math first ($$...$$)
  src = src.replace(/\$\$([\s\S]+?)\$\$/g, (_match, tex) => {
    try {
      return katex.renderToString(tex.trim(), { displayMode: true, throwOnError: false });
    } catch {
      return `<pre class="math-error">${tex}</pre>`;
    }
  });
  // Inline math ($...$) -- avoid matching $$ and currency like $100
  src = src.replace(/(?<!\$)\$(?!\$)([^\n$]+?)\$(?!\$)/g, (_match, tex) => {
    try {
      return katex.renderToString(tex.trim(), { displayMode: false, throwOnError: false });
    } catch {
      return `<code class="math-error">${tex}</code>`;
    }
  });
  return src;
}

const processedMd = renderMath(mdSource);

// ---------------------------------------------------------------------------
// Marked setup
// ---------------------------------------------------------------------------
const marked = new Marked();

marked.use(gfmHeadingId());

marked.use({
  renderer: {
    code({ text, lang }) {
      const language = lang && hljs.getLanguage(lang) ? lang : null;
      const highlighted = language
        ? hljs.highlight(text, { language }).value
        : hljs.highlightAuto(text).value;
      const langLabel = language || "";
      return `<pre><code class="hljs${langLabel ? ` language-${langLabel}` : ""}">${highlighted}</code></pre>\n`;
    },
  },
});

const htmlBody = marked.parse(processedMd);
const headings = getHeadingList();

// ---------------------------------------------------------------------------
// Build table of contents (## through ####)
// ---------------------------------------------------------------------------
function buildToc(headings) {
  const tocItems = headings.filter((h) => h.level >= 2 && h.level <= 4);
  if (tocItems.length === 0) return "";

  const lines = tocItems.map((h) => {
    const indent = "  ".repeat(h.level - 2);
    return `${indent}<li><a href="#${h.id}">${h.text}</a></li>`;
  });

  return `<nav class="toc">\n<h2>Table of Contents</h2>\n<ul>\n${lines.join("\n")}\n</ul>\n</nav>`;
}

const tocHtml = buildToc(headings);

// ---------------------------------------------------------------------------
// Extract document title from first # heading (if any)
// ---------------------------------------------------------------------------
const titleMatch = mdSource.match(/^#\s+(.+)$/m);
const title = titleMatch ? titleMatch[1].trim() : basename(inputPath, ".md");

// ---------------------------------------------------------------------------
// Read highlight.js and KaTeX CSS to inline
// ---------------------------------------------------------------------------
import { createRequire } from "module";
const require = createRequire(import.meta.url);

const hljsCss = readFileSync(
  require.resolve("highlight.js/styles/github.css"),
  "utf-8"
);
const katexCss = readFileSync(
  require.resolve("katex/dist/katex.min.css"),
  "utf-8"
);

// ---------------------------------------------------------------------------
// Assemble final HTML
// ---------------------------------------------------------------------------
const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${title}</title>
<style>
/* === KaTeX === */
${katexCss}
/* === Highlight.js === */
${hljsCss}
/* === Document styles === */
:root {
  --max-width: 800px;
  --text: #24292f;
  --bg: #ffffff;
  --link: #0969da;
  --toc-bg: #f6f8fa;
  --border: #d0d7de;
  --code-bg: #f6f8fa;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.6;
  max-width: var(--max-width);
  margin: 0 auto;
  padding: 2rem 1.5rem;
}
h1, h2, h3, h4 { margin-top: 1.5em; margin-bottom: 0.5em; }
h1 { font-size: 2em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid var(--border); padding-bottom: 0.3em; }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
pre {
  background: var(--code-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1em;
  overflow-x: auto;
}
code { font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 0.9em; }
:not(pre) > code { background: var(--code-bg); padding: 0.2em 0.4em; border-radius: 3px; }
.toc {
  background: var(--toc-bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 1em 1.5em;
  margin-bottom: 2em;
}
.toc h2 { font-size: 1.1em; margin: 0 0 0.5em 0; border: none; padding: 0; }
.toc ul { list-style: none; padding-left: 1em; margin: 0; }
.toc li { margin: 0.25em 0; }
blockquote {
  border-left: 4px solid var(--border);
  margin: 1em 0;
  padding: 0.5em 1em;
  color: #57606a;
}
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid var(--border); padding: 0.5em 0.75em; text-align: left; }
th { background: var(--toc-bg); }
img { max-width: 100%; }
.katex-display { overflow-x: auto; overflow-y: hidden; }
</style>
</head>
<body>
${tocHtml}
${htmlBody}
</body>
</html>`;

writeFileSync(outputPath, html, "utf-8");
console.log(`Converted: ${inputPath} -> ${outputPath}`);
