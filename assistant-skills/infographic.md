# Infographic recipe

Use deterministic composition: PIL plus matplotlib. You cannot see the
render, so control it through code and measurements, then let Firas judge
aesthetics.

Pipeline:
1. Decide the format: LinkedIn portrait 1080x1350, square 1080x1080, or
   wide 1920x1080. Single clear message at the top, 3-5 supporting facts
   or a single chart, source line at the bottom.
2. Install: pip install --quiet pillow matplotlib
3. Compose in assistant-outputs/build_graphic.py: PIL canvas in the brand
   palette, title block (bold, 64-88px at 1080 width), stat blocks or an
   embedded matplotlib chart rendered at 2x and pasted, footer with source
   and date. Load fonts via PIL truetype from
   /usr/share/fonts/truetype/dejavu/ (DejaVuSans.ttf, DejaVuSans-Bold.ttf).
4. generate_image only for a hero or background illustration; overlay a
   semi-transparent ink panel behind any text on top of it so contrast
   holds regardless of what FLUX produced.
5. Verify: reopen with PIL, print size and mode; measure text widths with
   font.getbbox before drawing so nothing overflows the canvas; keep 64px
   side margins at 1080 width.
6. deliver_file the PNG; state the dimensions and intended platform in the
   reply.

Checklist: one message, readable at thumbnail size (test: title occupies
at least 8 percent of canvas height), margins respected, source line
present, palette respected, no em dashes.
