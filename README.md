# forsocialsss

A LinkedIn content agent that runs on Claude Code routines. It monitors Firas's professional lanes on a heartbeat, decides when something clears the bar, researches it at primary sources, drafts in his voice, and delivers to Slack for approval. It posts nothing itself. State, memory, and every editorial decision live in this repo as commits.

## How it works

    scheduled routine (every 2-3h, Anthropic-managed cloud)
      -> fresh clone of this repo
      -> CLAUDE.md (constitution) -> HEARTBEAT.md (one cycle)
         0 orient   read state + run log
         1 inbox    handle Slack replies: approve / edit / kill / hold / status
         2 scan     pulse skill: HN, arXiv, legal tech press, Apify LinkedIn scrapers (budgeted)
         3 decide   score topics: momentum, saturation, fit -> ignore / watchlist / escalate
         4 escalate deep-dive skill -> draft skill -> slack-brief skill (max 1 per cycle)
         5 governor cadence: 1 post per 2 days target, 20h min gap, quiet hours
         6 commit   state + run-log line, every cycle
         7 retro    weekly: engagement pull, calibration, playbook + voice updates with diffs

    api fire trigger (same routine)
      <- Slack workflow webhook posts Firas's reply for instant handling
      <- manual curl for breaking-news nudges

Key files: CLAUDE.md (rules), HEARTBEAT.md (loop), identity/ (who, voice, strategy, never), playbook/ (platform knowledge with validation status), sources/ (scrapers, budgets, creators), state/ (topics, queue, posted, run log, lessons), .claude/skills/ (pulse, deep-dive, draft, slack-brief, retro), prompts/ (routine prompts).

## Setup

1. Push this repo (it ships with the initial commit ready):

       git push -u origin main

2. At claude.ai, Settings > Connectors: make sure Slack and Apify are connected and enabled for Claude Code. Both were already connected during the build.

3. At claude.ai/code, connect GitHub and select nevaubi/forsocialsss.

4. Create the routine:
   - Repository: nevaubi/forsocialsss
   - Prompt: paste from prompts/routine-heartbeat.md
   - Trigger: schedule, every 2-3 hours between 07:00 and 22:00 America/Chicago. Match the frequency to your plan's daily routine allowance; API-triggered runs are exempt from that allowance.
   - Connectors: Slack, Apify
   - Environment network allowlist: api.apify.com, hn.algolia.com, export.arxiv.org, anthropic.com, openai.com, blog.google, lawsitesblog.com, artificiallawyer.com
   - Optional env var APIFY_TOKEN only if the Apify MCP connector is unavailable in the routine environment; the fallback path calls api.apify.com directly.

5. Add an API trigger to the same routine. Store the fire URL and token. Optional but recommended: a Slack workflow (shortcut on your DM) that POSTs your reply text to the fire endpoint, so approvals and nudges execute immediately instead of waiting for the next tick. Manual equivalent:

       curl -X POST "https://api.anthropic.com/v1/claude_code/routines/ROUTINE_ID/fire" \
         -H "Authorization: Bearer ROUTINE_TOKEN" \
         -H "anthropic-version: 2023-06-01" \
         -H "anthropic-beta: experimental-cc-routine-2026-04-01" \
         -H "Content-Type: application/json" \
         -d '{"text": "breaking: <what happened>"}'

   Routines are a research preview; header and limits may change. Check the routines docs if a call 400s.

## First runs, what to expect

- Run 1-2: creator URL resolution (up to 5 per cycle), first scans, topics.json fills. Probably no draft. A held notice after quiet days is the system working, not failing.
- The first draft DM arrives when a topic actually clears momentum >= 6, fit >= 7, saturation <= 5. Reply approve, edit: <notes>, kill: <reason>, or hold.
- Posting is manual in v1: on approve you get final paste-ready copy and a window; you paste it and reply "posted <url>".
- Weekly retro DM: metrics vs phase goals, calibration, playbook updates, voice/strategy diffs if any, and 3-5 comment opportunities for you to engage manually.

## Costs

- Apify: capped at $0.30 per cycle, typical $0.10-0.15; roughly $15-30/month at 8-10 cycles/day.
- Routine runs draw down your Claude subscription usage. If a 2h cadence strains your plan's allowance, drop to 3-4h; the loop is designed to degrade gracefully.

## Safety posture

- No LinkedIn session, cookie, or credential is used anywhere, ever. All LinkedIn reads are session-free public scrapers (harvestapi suite).
- The agent never posts, comments, reacts, or connects as Firas. It drafts and suggests; he acts.
- Identity drift guard: the agent edits its own voice/strategy only during retro with diffs sent to Slack; the constitution, heartbeat, never-list, and skills are propose-only.

## Roadmap

- v1.1: PDF document generation for carousel posts when a draft warrants a real artifact.
- v1.2: official LinkedIn OAuth posting (w_member_social) so approve can mean publish, still human-gated.
- v1.3: comment-thread intelligence: track replies on Firas's posts and brief him on which to answer first.
