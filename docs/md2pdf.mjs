/**
 * Markdown → PDF (A4, 11 pt, marginesy 2 cm) przez Chrome w trybie headless.
 *
 *   node docs/md2pdf.mjs docs/PLIK.md [docs/PLIK.pdf]
 *
 * Nie używamy pandoca ani LaTeX-a, żeby nie dokładać zależności — Chrome i tak
 * jest w systemie (testy E2E Playwrighta). Styl jest celowo oszczędny: ten sam
 * biały, jednokolorowy język wizualny co aplikacja.
 */

import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, resolve } from 'node:path';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';

const args = process.argv.slice(2);
/** `--compact` = 10,5 pt i ciaśniejsza interlinia; dolna granica czytelności. */
const compact = args.includes('--compact');
const [input, output] = args.filter((a) => !a.startsWith('--'));
if (!input) {
  console.error('Użycie: node docs/md2pdf.mjs <plik.md> [plik.pdf]');
  process.exit(1);
}
const pdfPath = resolve(output ?? input.replace(/\.md$/, '.pdf'));
const source = readFileSync(resolve(input), 'utf8');

/* --- minimalny markdown → HTML ------------------------------------------- */

const escapeHtml = (s) =>
  s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

/** Formatowanie w linii: `kod`, **pogrubienie**, *kursywa*, [tekst](url). */
const inline = (s) =>
  escapeHtml(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*]+)\*/g, '$1<em>$2</em>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>');

const render = (md) => {
  const out = [];
  const lines = md.split('\n');
  let i = 0;
  let listType = null;

  const closeList = () => {
    if (listType) {
      out.push(`</${listType}>`);
      listType = null;
    }
  };

  while (i < lines.length) {
    const line = lines[i];

    // blok kodu
    if (line.startsWith('```')) {
      closeList();
      const body = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith('```')) {
        body.push(lines[i]);
        i += 1;
      }
      i += 1;
      out.push(`<pre><code>${escapeHtml(body.join('\n'))}</code></pre>`);
      continue;
    }

    // tabela
    if (line.includes('|') && /^\s*\|/.test(line) && /^\s*\|[\s:|-]+\|\s*$/.test(lines[i + 1] ?? '')) {
      closeList();
      const cells = (row) =>
        row.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const head = cells(line);
      i += 2;
      const body = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) {
        body.push(cells(lines[i]));
        i += 1;
      }
      out.push(
        `<table><thead><tr>${head.map((c) => `<th>${inline(c)}</th>`).join('')}</tr></thead>` +
          `<tbody>${body
            .map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`)
            .join('')}</tbody></table>`,
      );
      continue;
    }

    const heading = line.match(/^(#{1,4})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      out.push(`<h${level}>${inline(heading[2])}</h${level}>`);
      i += 1;
      continue;
    }

    if (/^\s*(---|___|\*\*\*)\s*$/.test(line)) {
      closeList();
      out.push('<hr>');
      i += 1;
      continue;
    }

    const ordered = line.match(/^\s*\d+\.\s+(.*)$/);
    const bullet = line.match(/^\s*[-*]\s+(.*)$/);
    if (ordered || bullet) {
      const want = ordered ? 'ol' : 'ul';
      if (listType !== want) {
        closeList();
        out.push(`<${want}>`);
        listType = want;
      }
      out.push(`<li>${inline((ordered ?? bullet)[1])}</li>`);
      i += 1;
      continue;
    }

    if (line.trim() === '') {
      closeList();
      i += 1;
      continue;
    }

    // obrazek w osobnym akapicie
    const image = line.match(/^!\[([^\]]*)\]\(([^)]+)\)\s*$/);
    if (image) {
      closeList();
      out.push(`<p class="figure"><img src="${image[2]}" alt="${escapeHtml(image[1])}"></p>`);
      i += 1;
      continue;
    }

    // akapit (łączymy kolejne linie)
    closeList();
    const para = [line];
    i += 1;
    while (i < lines.length && lines[i].trim() !== '' && !/^[#\-*>|`]|^\d+\./.test(lines[i])) {
      para.push(lines[i]);
      i += 1;
    }
    out.push(`<p>${inline(para.join(' '))}</p>`);
  }

  closeList();
  return out.join('\n');
};

const html = `<!doctype html>
<html lang="pl"><head><meta charset="utf-8"><title>${escapeHtml(basename(input))}</title>
<style>
  @page { size: A4; margin: 2cm; }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    font-family: -apple-system, "Helvetica Neue", Arial, sans-serif;
    font-size: ${compact ? '10.5pt' : '11pt'};
    line-height: ${compact ? '1.3' : '1.45'};
    color: #111111;
  }
  h1 { font-size: ${compact ? '16pt' : '19pt'}; letter-spacing: -0.02em; margin: 0 0 ${compact ? '3pt' : '4pt'}; }
  h2 { font-size: 13pt; letter-spacing: -0.01em; margin: 14pt 0 4pt; }
  h3 { font-size: 11.5pt; margin: 10pt 0 3pt; }
  h4 { font-size: 11pt; margin: 8pt 0 2pt; }
  p { margin: 0 0 ${compact ? '4.5pt' : '6pt'}; }
  ul, ol { margin: 0 0 6pt; padding-left: 18pt; }
  li { margin: 0 0 2pt; }
  code {
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 9.5pt;
    background: #F4F4F4;
    padding: 1px 3px;
    border-radius: 3px;
  }
  pre {
    background: #F7F7F7;
    border: 1px solid #E6E6E6;
    border-radius: 4px;
    padding: 7pt 9pt;
    margin: 0 0 7pt;
    overflow-x: auto;
  }
  pre code { background: none; padding: 0; font-size: 9pt; line-height: 1.35; }
  table { border-collapse: collapse; width: 100%; margin: 0 0 8pt; font-size: ${compact ? '9pt' : '10pt'}; }
  th, td { border: 1px solid #E6E6E6; padding: ${compact ? '3pt 5pt' : '4pt 6pt'}; text-align: left; vertical-align: top; }
  th { background: #F7F7F7; font-weight: 600; }
  hr { border: 0; border-top: 1px solid #E6E6E6; margin: 10pt 0; }
  a { color: #2340D9; text-decoration: none; }
  img { max-width: 100%; border: 1px solid #E6E6E6; border-radius: 4px; }
  .figure { margin: 6pt 0 8pt; }
  h1, h2, h3, h4 { break-after: avoid; }
  pre, table, .figure { break-inside: avoid; }
</style></head><body>
${render(source)}
</body></html>`;

const work = mkdtempSync(`${tmpdir()}/md2pdf-`);
const htmlPath = `${work}/doc.html`;
writeFileSync(htmlPath, html, 'utf8');

try {
  execFileSync(
    CHROME,
    [
      '--headless',
      '--disable-gpu',
      '--no-sandbox',
      '--no-pdf-header-footer',
      `--print-to-pdf=${pdfPath}`,
      `file://${htmlPath}`,
    ],
    { stdio: 'pipe' },
  );
  console.log(`✓ ${pdfPath}`);
} finally {
  rmSync(work, { recursive: true, force: true });
}
