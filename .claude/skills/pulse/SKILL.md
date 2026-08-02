---
name: pulse
description: Budgeted multi-source scan that converts raw signals into scored topic state. Run every heartbeat cycle at step 2. Cheap situational awareness; output is updated state, not prose.
---

# Pulse

## Procedure

1. Load sources/sources.md and state/topics.json. Compute the remaining Apify budget for this cycle.
2. Bootstrap check: for any sources/creators.json entry with "resolve": true, resolve the canonical profile via harvestapi/linkedin-profile-search (searchQuery = name plus their strongest keyword, maxItems 3). Pin linkedinUrl and set status active. After 2 failed attempts across cycles, set status unresolvable. At most 5 resolutions per cycle; count them against budget.
3. Pull sources in this order, stopping the moment the cap is hit:
   a. Free first: Hacker News (front page plus 1-2 pillar queries), arXiv scan, legal tech headline scan.
   b. harvestapi/linkedin-post-search: at most 2 queries. Choose active-topic keywords first, then rotate the seed pool.
   c. harvestapi/linkedin-profile-posts: next block of at most 10 creators by rotation_cursor; advance and persist the cursor in creators.json.
4. Normalize every item worth keeping into a signal: {source, url, author, ts, gist (max 40 words), topic_guess}. Discard obvious noise (job posts, pure promo, giveaways) before it costs tokens.
5. Cluster signals into topics. Merge into existing slugs aggressively; create a new slug only for genuinely distinct subjects. Update signal_count_24h, last_signal, and representative sources (keep the 5 best URLs, primary sources preferred).
6. Score every touched topic:

   Momentum, 0-10:
   - 0-2: a single mention anywhere
   - 3-5: multiple mentions inside one source class
   - 6-7: cross-source presence within 24h, or one high-authority primary event (model release, major filing, significant paper, vendor launch)
   - 8-10: broad multi-source surge, tracked creators plus HN plus press
   Decay: no new signal for 48h, halve the score and mark decaying; none for 7 days, archive.

   Saturation, 0-10:
   - 0-2: few or no tracked creators have touched it
   - 3-5: several posts exist but obvious angles remain open
   - 6-8: most tracked creators have posted, angles converging
   - 9-10: exhausted, joke-stage
   Add 2 if the visible peak was more than 72h ago.

   Fit, 0-10 = pillar match (0-4) + Firas standing per identity/profile.md (0-3) + audience value (0-3).
   A topic he cannot add engineering insight to caps at 5 regardless of the components.

7. Check watchlist triggers against the fresh state; any that fire go to the decision step flagged as triggered.
8. Write topics.json and watchlist.json. Report to the heartbeat: signals processed, topics touched, spend, and anything budget_capped.

## Rules

- Free sources always run before paid ones.
- No drafting and no Slack inside pulse. Ever.
- Track every paid event count and price it at the unit rates in sources.md for the spend field.
- If a scraper errors, log it, skip it, continue.
