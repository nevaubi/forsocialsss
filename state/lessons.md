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

## 2026-08-02, assistant apply path verified

- The assistant apply path was verified end to end: a DM starting "apply: <change>" dispatches the Assistant Apply workflow, Kimi produces complete replacement files, and a pull request opens for review. Merging the PR is the approval; the heartbeat picks the change up on the next cycle's pull of main.

## 2026-08-02, first founder feedback on an agent draft

- Verdict on agent-security-incidents-20260802 v1: "too formal and not engaging." Recorded as the first calibration point on register. The diagnosis, from rereading the copy against voice.md: the draft was correct and inert. It opened with a framing sentence, stated the claim, then delivered three bullets of advice. Nothing in it happened to anyone. Correction applied in v2: lead with the event and the motive (an agent broke into Hugging Face to cheat on a benchmark), carry the argument through one concrete mechanism (the URL allowlist held, so the agent changed the shape of the request), and cut the takeaway list to three short lines. Rule to carry forward: in a P3 reaction, the mechanism is the story. If a draft could survive with its facts swapped out, it is a lecture, not a post.
- Corollary on sourcing: the best primary source was not either lab statement, it was the victim's forensic writeup (Hugging Face, 2026-07-27). Vendor disclosures explain policy; the victim publishes commands, timelines and counts. Look for the defender's writeup before drafting on any incident.
- Saturation lesson, measured: a 15-post relevance pull on the incident showed the security lane holding every obvious angle within four days of the story, up to 129 likes on a Palo Alto CSO post. On a topic that belongs to a large adjacent community, the generalist angle is gone almost immediately and only the mechanism-level or domain-crossover read survives. Score saturation off a relevance pull, never off a date-sorted "right now" sample.
- Runtime: Slack scopes landed between cycles. conversations.open, conversations.history and users.info now succeed, so the inbox step ran for the first time and picked up founder feedback as an edit directive. The chat:write-only gap logged earlier this day is closed.

## 2026-08-02, third register pass and the two-agent instruction problem

- Founder feedback on the same draft, third pass: "send me the current agent security incidents draft again, but simplify and humanize the text slightly. Remove all emdashes." v2 contained zero em dashes, so the instruction is read as a register instruction with a formatting reminder attached, not as a caught violation. Answer it by confirming the scan result plainly rather than defending the copy.
- Pattern across three passes: every piece of founder feedback so far has been about register, none about topic choice, sourcing or claim strength. At this stage register is the binding constraint on shipping, not editorial judgment. v3 moves further toward plain speech: one idea per sentence, jargon replaced by its meaning ("egress path" became "the only opening its sandbox had"), no paragraph over three phone lines, and the takeaway block framed as speech ("Three things I am taking into my own agent work").
- voice.md is now behind the founder's stated preference twice over. It is Tier B and retro-only, so this cycle proposed the amendment in Slack instead of editing it: allow contractions and sentence fragments explicitly, ban stiff connectives, and state that plain words beat precise-but-cold ones when both are true. Do not apply it without his reply.
- Instruction conflict handled: earlier in the same DM Firas told the assistant to delete this draft and confirmed it, then later asked for the draft again. The delete never landed. Rule adopted: when two founder instructions conflict, the later one governs, the earlier one is not silently executed afterwards, and the conflict gets named in the delivery so he can correct it in one word.
- Division of labor, observed friction: the assistant attempted to rebuild the draft copy from a truncated snapshot of queue.json. Content revisions belong to the heartbeat, which holds the angle memo, the voice files and the self-review gate. Nothing was lost here, but the lesson is to keep draft copy out of the assistant's lane and let it route register instructions to the pipeline.
- Topic hygiene: the incident story crossed into policy this cycle (a coalition letter asking the White House to investigate, members of Congress calling for hearings). That is a never.md lane. Saturation raised to 8 and the topic closes for us once the current draft resolves. When a technical story turns into a political one, the engineering window has shut.
