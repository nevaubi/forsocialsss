# lessons.md

Append-only editorial memory. Dated entries, newest last. Retro writes here; heartbeat may add kill reasons that generalize. Never rewrite history.

## 2026-08-02, founding decisions

- Session-free scraping only (harvestapi suite on Apify). Firas's LinkedIn session is never used anywhere, local or cloud. Reason: a restricted account ends the entire project; the trend signal does not require his login.
- Approval-gated manual posting for v1. The agent's product is judgment and drafts, not clicks. Official-API posting is a later upgrade, never cookie-based automation.
- Two-tier write policy adopted, informed by published research on identity drift in agents allowed to rewrite their own persona files. Self-improvement flows through weekly retro with diffs sent to Slack, not silent rewrites.
- Baseline recorded: 2026-08-01 document post on a 42-follower account, 1 like and 0 comments at 24 hours, posted Friday night off-peak. Cold-start floor, logged so future comparisons stay honest.

## 2026-08-02, founder directives and first live scan

- Founder directive: shift weight toward architecture takes, trending AI news reaction, and legal AI specifically. Pillars rebalanced in strategy.md (P1 legal AI 40%, P2 architecture 35%, P3 news 20%, P4 5%). P3 carries a 24-48h freshness rule and a ban on summary-only news posts.
- X added as a leading-indicator source and Tavily as the continuous research and verification layer. First X pull (81 tweets) validated a filter rule now encoded in sources.md: roughly half of AI-engineering keyword results are course-bait or crypto-token promotion; discard on sight, verify everything surviving at primary sources.
- Writing craft imported from four skill packs into playbook and the draft skill: accepted honest hook patterns (time-anchor, year-pivot, honest curiosity gap, contrarian, sparing anaphora), an expanded AI-tell scan list, and the lead-with-the-concrete rule. Rejected as bait or off-voice: comment-gating, R.I.P. formulas, emotional cold-opens, gratitude tagging, listicle counts.
- First seeded topic board: the standout candidate is legora-wexler-litigation-ai (fit 10, saturation 3): litigation fact intelligence is literally Firas's day job.

## 2026-08-02, runtime migration to Claude Managed Agents

- Founder directive: run on the Claude Managed Agents API backend, not Claude Code routines. Rationale accepted: server-side cron (scheduled deployments), vault-injected secrets that the agent never sees in plaintext, native repo mounting, and API billing under Firas's control. Tradeoff logged: per-token plus per-session-hour billing instead of subscription, so the early-exit budget discipline in HEARTBEAT.md now saves real money.
- Architecture consequence: every scheduled run is a fresh sandbox, so git push is the only persistence. The Runtime section of CLAUDE.md defines the push fallback chain and the UNPUSHED flag; losing a cycle's decisions silently is the failure mode to guard hardest against.
- Deploy tooling lives in deploy/deploy.py plus the Deploy Agent workflow; provisioning is idempotent by resource name and rerunnable after any secret rotation.

## 2026-08-02, first scheduled heartbeat

- Time-boxed topic dropped as designed: yc-qm-open-source-harness was archived at saturation 7 because a 187K-follower creator published the exact generic teardown its watchlist trigger named. Generalizable: when a topic's obvious angle is reachable by any large account, the trigger window is roughly 24 hours, so either escalate on the first cycle with a non-obvious angle or let it go.
- The pulse post-search returns only the newest posts when sorted by date, which measures live conversation rather than accumulated coverage. Saturation scoring should not read a thin "right now" sample as an empty field; cross-check against tracked creators and press before calling an angle unclaimed.
- Runtime gap logged: the Slack bot token carries chat:write only, so conversations.open, conversations.history and users.info fail with missing_scope. DM delivery works by posting to the user ID directly, but no reply keyword can be processed until im:history, im:write, im:read and users:read are added. Requested from Firas in Slack; do not work around it with any other channel.
