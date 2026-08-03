# PDF report recipe

Pipeline:
1. Draft the content first as markdown in assistant-outputs/draft.md:
   title page block, a 3-5 bullet TLDR, sections with clear headers, a
   sources section at the end. Get the content right before styling.
2. Install: pip install --quiet fpdf2 markdown pypdf matplotlib
   (fpdf2 is the default engine: pure python, reliable on the runner.
   weasyprint gives finer typography if you want it: it needs
   sudo apt-get install -y libpango-1.0-0 libpangocairo-1.0-0 first and
   can take a while; only reach for it when the report warrants it.)
3. Charts: matplotlib, one chart per figure, save 2x scale PNGs into
   assistant-outputs/, brand palette, no chartjunk, axis labels always.
   Embed into the PDF at natural width.
4. Build with a python script in assistant-outputs/build_report.py using
   fpdf2: A4, 18mm margins, title page (title, date, one-line purpose),
   body with header hierarchy, page numbers in the footer, charts inline.
5. Verify before delivering:
   - run: python3 -c "from pypdf import PdfReader; r=PdfReader('assistant-outputs/report.pdf'); print(len(r.pages), 'pages'); print(r.pages[0].extract_text()[:200])"
   - view_render the PDF and inspect what you see: headers not orphaned at
     page bottoms, charts legible, margins even, palette right, nothing
     overflowing or overlapping. Fix the build script and re-render; up to
     two fix rounds.
6. deliver_file with a descriptive title, and say in the reply what is in
   the report and what sources fed it.

Checklist: TLDR present, every section under a header, every number
sourced, no orphan headers at page bottoms (add page breaks), no em dashes,
footer page numbers, palette respected.
