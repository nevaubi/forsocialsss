---
name: draft
description: Turn a completed angle memo into a LinkedIn post in Firas's voice, formatted for 2026 distribution, with a mandatory self-review gate. Reads voice.md and never.md fresh every time.
---

# Draft

Read identity/voice.md and identity/never.md immediately before writing. From the files, not from memory.

## Structure patterns (choose exactly one)

1. War story (best for P1): the situation in one line, the constraint that made it hard, the decision and why, what broke or held, the transferable rule. Pattern level only; no client detail survives the never.md check.
2. Contrarian with receipts (P2, P3): the common claim, why it fails in production, the evidence (this is where the artifact lives), what to do instead, and the honest limits of the correction.
3. Teardown (P2, P3): what shipped or changed in one line, how it actually works in 3-5 tight mechanisms, what it changes for builders, one caution.

## Mechanics

- Hook: first line 12 words or fewer, specific, no questions. Lines one and two must survive the "...see more" cut (about the first 200 characters). Test: would a staff engineer stop scrolling.
- Body: 150-300 words. Line breaks every 1-2 sentences. Hyphen bullets for mechanisms, parallel construction, every bullet a complete thought.
- One idea per post. The artifact appears by the midpoint, not saved for the end.
- Close: the second-to-last line carries the substance. The last line may be generous ("worth reading if you run agents in prod") but never begging and never a question mark aimed at comments.
- Links: none in the body. Name the source in text ("the Anthropic post", "the paper"). Add "link in comments" only when the source is genuinely needed, per the playbook's link policy.
- Hashtags: 0-3 niche tags on the final line, or none. No @mentions unless the person is central to the story and large enough that tagging is not reach-borrowing.
- Format: text by default. Document format only when Firas has a real artifact (a deck, a diagram, a guide he made). Never generate a decorative document to game dwell.

## Self-review gate (all must pass; fix it or kill it)

1. Search the draft for the em dash character. Zero tolerance, including in any "link in comments" note.
2. Scan against every ban in voice.md and never.md, line by line.
3. Every number and claim traces to the angle memo's evidence list.
4. Read it as a skeptical staff engineer. Anything cringe, salesy, or obvious gets deleted.
5. Delete-the-first-sentence test: if the post is stronger starting at line two, do it and re-hook.
6. Mobile render check: no paragraph over 3 lines at roughly 40 characters per line.
7. Voice check: does it sound like the About section in identity/profile.md, or like LinkedIn.
8. Would Firas defend every sentence in an engineering review. If any sentence needs an excuse, cut it.

## Output

Write post_text, format, and predicted {band: quiet | normal | above, rationale} into the queue entry, status drafted. The prediction is scored by retro; make it honest, not hopeful.
