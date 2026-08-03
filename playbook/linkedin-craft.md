# linkedin-craft.md

Working model of LinkedIn distribution, 2026. Tier A file owned by retro. Every entry is tagged:

- prior: from industry analysis, unvalidated on this account
- validated / refuted: confirmed or contradicted by our own data, with date and evidence

Update entries with evidence, never silently. Never delete a prior; supersede it and keep the history in the change log.

## Distribution model

- prior: Ranking favors an interest graph over the social graph. Topical expertise and relevance can out-distribute follower count; LinkedIn rebuilt the feed to boost subject-matter experts and suppress low-value viral content. Net positive for a cold-start expert account.
- prior: Dwell time is the dominant signal (depth scoring). Commonly cited pattern: under 3 seconds of dwell correlates with ~1.2% engagement and limited distribution; 61+ seconds correlates with maximum distribution. Meaningful comments (10+ words) weigh far above likes; saves and private shares are the strongest signals after comments.
- prior: Engagement bait is actively suppressed. Pod detection is claimed near 97% accuracy with lasting reach penalties for participants.
- prior: External links cut reach heavily, commonly cited around 60%. The link-in-first-comment workaround is reported penalized as of early 2026 by at least one analysis; other sources still recommend it. Our default: no links. When a primary source matters, name it in text and add the link in comments only when truly necessary, then measure.
- prior: Early comment velocity matters and author replies inside the first hour help distribution. This requires Firas: every draft brief includes a reminder to be reachable for ~45 minutes after posting.

## Format model

- prior: PDF document posts generate roughly 2-3x the dwell of text posts; each swipe extends the clock. The cited sweet spot is 8-15 slides. Note: his baseline doc was 30 pages, well past the cited range; completion behavior unknown at this sample size.
- prior: Text posts: 150-300 words, line breaks every 1-2 sentences, hook must win the "...see more" click within the first 1-3 lines (roughly the first 200 characters).
- prior: Hashtags: 0-3 niche tags at most, a weakening lever overall; generic tags are worthless.
- prior: Timing: Tuesday through Thursday, 8-10am and around midday local time test best in aggregate studies, but consistency beats timing.
- prior: Short native video with captions gets a distribution boost. Out of scope for v1; revisit if Firas wants to record.

## Account context

- validated 2026-08-02: baseline post (30-page document, P2, posted Friday ~18:50 CT, 42-follower account) reached 1 like and 0 comments in 24 hours. Recorded as the cold-start floor, not as format signal. n=1.

## Change log

- 2026-08-02: initial priors compiled from 2026 industry analyses (connectsafely.ai, digitalapplied.com, Hootsuite, teract.ai, meet-lea.com, postiv.ai, dataslayer.ai). Confidence moderate; sources conflict on the link-in-comments question. Nothing here is law until validated locally.

## Craft library (imported 2026-08-02 from writing skill packs; style intel, prior status)

- prior: sweet-spot text length restated as 900-1300 characters, consistent with the 150-300 word rule above; re-hook before the fold when repurposing anything longer.
- prior: lead with the concrete thing (artifact, number, event, output) and explain after the example, never before it. Proof replaces adjectives.
- prior: the specificity upgrade beats the general claim: "teams ship 14 features a quarter and move no metric" outperforms "teams prioritize badly". Apply it during self-review to any generic sentence.
- Hook pattern menu and the rejected-as-bait list live in .claude/skills/draft/SKILL.md; rejections (comment-gating, R.I.P. formulas, emotional cold-opens, gratitude tagging, listicle counts) stand regardless of their engagement numbers because never.md outranks the playbook.
- AI-tell scan list (also in the draft skill): "not just X, it's Y", stacked triads, "here's the kicker", "let's unpack", hedging stacks, uniform sentence rhythm, comment-farming closers, throat-clearing openers.
- observed 2026-08-02: on X, AI-engineering keyword feeds are dominated by course-listicle bait accounts recycling identical formulas ("Don't waste 2 years...", timestamp menus, "$500 course" comparisons). Useful as saturation signal and as an anti-style reference; never as substance.

## Change log (continued)

- 2026-08-02: craft library imported and reconciled with voice/never rules; conflicting formulas rejected rather than adopted.

## Register and revision

- observed 2026-08-02 (n=1, founder feedback on draft agent-security-incidents-20260802): a technically clean draft was rejected as "too formal and not engaging." Evidence in the copy itself: a framing opener, the claim stated before any event, and a three-bullet advisory block carrying most of the payload. Revision that was accepted for redelivery led with the event and the agent's motive, spent the middle on one traceable mechanism (a URL allowlist that held while the agent switched to local file reads), and shortened the advisory block. Working rule until data contradicts it: the reader should meet a specific thing that happened before meeting the argument about it.
- observed 2026-08-02: on incident topics, the victim's technical writeup outranks the vendor disclosure as source material. The Hugging Face timeline supplied counts, commands and a defensible mechanism narrative; the lab statements supplied policy language. Draft from the defender's document.
- observed 2026-08-02 (Apify post-search, 15 posts, past week, sortBy relevance): incidents that belong to a large adjacent professional community saturate within about four days across that community's accounts, including accounts with six-figure reach. Sorting by relevance rather than date is the only way to see this; a date-sorted pull reads the same field as empty. Escalate such topics only on a mechanism-level or domain-crossover angle, and treat day 5 onward as a kill candidate.

## Change log (continued)

- 2026-08-02: register and revision section added from the first founder feedback on an agent draft plus the relevance-sorted saturation pull behind it.

- observed 2026-08-02 (n=3 founder feedback events, one draft): all three rounds of feedback concerned register, none concerned topic, sourcing or claim strength. Sequence: "too formal and not engaging", then "too formal" as a standing instruction for future drafts, then "simplify and humanize slightly". Working rule: for this account, plainness is the highest-leverage craft variable, ahead of hook engineering. Concretely, prefer the plain word over the precise-but-cold one when both are true, cut clauses rather than sentences, keep paragraphs under three phone lines, and frame takeaway blocks as speech rather than as a checklist.
- observed 2026-08-02 (Apify post-search, 15 posts, relevance, "AI evals"): the LinkedIn evals lane is occupied but narrow. It is LLM-as-judge economics, judge validation against human labels, "evals are the new PRDs" (360 likes), and internal-versus-customer eval gaps. No post in the sample connected the lab containment incidents to eval design itself. Saturation is not a single number per subject area: adjacent lanes can be crowded while the specific mechanism angle sits empty. Score the angle, not the keyword.
- observed 2026-08-02 (same instrument, "agent memory"): explainer content dominates and wins on volume (824 likes for a short-term versus long-term memory explainer), while the security-adjacent framing (memory as a write target whose poisoning survives every later session) sits almost unclaimed. Where an explainer wave has taken the topic, the remaining angle is usually the failure mode.
