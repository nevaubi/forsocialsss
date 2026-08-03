# Slide deck recipe

Pipeline:
1. Outline first, in the conversation or a scratch file: one line per
   slide, title plus the single point that slide makes. A slide makes one
   point. 8-14 slides for a normal briefing.
2. Install: pip install --quiet python-pptx matplotlib
3. Build with a script in assistant-outputs/build_deck.py using python-pptx:
   16:9 (Presentation().slide_width = Inches(13.333), height 7.5), title
   slide (title, date, purpose line), section slides, closing slide with
   next actions.
4. Layout rules: max 5 bullets per slide, max 12 words per bullet, titles
   under 8 words, 20pt+ body, 32pt+ titles, brand palette from the skills
   README, charts as full-slide or half-slide matplotlib PNGs, no stock
   imagery unless Firas asked for visual flair (then generate_image for a
   title background at 16:9 and keep text contrast high).
5. Verify: reopen with python-pptx, iterate slides, print each slide's
   shape count and title text; confirm no empty slides, no overflowing
   text frames (word_wrap on, autosize off, keep bullets short instead).
6. deliver_file the .pptx with a title; summarize the slide list in the
   reply so Firas can sanity-check the structure without opening it.

Checklist: one point per slide, bullet and word caps respected, consistent
title positions, palette respected, closing slide has concrete next steps,
no em dashes.
