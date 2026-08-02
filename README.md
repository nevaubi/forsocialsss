# forsocialsss

A LinkedIn content agent that runs on Claude Code routines. It monitors Firas's professional lanes on a heartbeat, decides when something clears the bar, researches it at primary sources, drafts in his voice, and delivers to Slack for approval. It posts nothing itself. State, memory, and every editorial decision live in this repo as commits.

## How it works

    scheduled routine (every 2-3h, Anthropic-managed cloud)
      -> fresh clone of this repo
      -> CLAUDE.md (constitution) -> HEARTBEAT.md (one cycle)
         0 orient   read state + run log
         1 inbox    handle Slack replies: approve / edit / kill / hold / status
         2 scan     pulse skill: HN, arXiv, legal tech press, Tavily news, Apify LinkedIn + X scrapers (budgeted)
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

The live runtime is Claude Managed Agents: a scheduled deployment fires a fresh session on a cron cadence, the repo is mounted into the sandbox, and secrets are injected from a credential vault at the network boundary. Billing is per token plus a small per-session-hour charge on the Claude API.

1. Repo secrets (Settings > Secrets and variables > Actions). Exact names matter; they map straight into the deploy workflow:
   - ANTHROPIC_API_KEY, required
   - APIFY_API_KEY, LinkedIn and X scraping
   - TAVILY_API_KEY, research and verification
   - FIREWORKS_API_KEY, optional auxiliary models
   - GH_STATE_TOKEN, fine-grained PAT with contents read and write on this repo only; this is how the agent pushes state between runs
   - SLACK_BOT_TOKEN, draft delivery and approvals (step 2)
2. Slack app, about five minutes: api.slack.com/apps, create app from scratch in the workspace, add bot token scopes chat:write, im:write, im:history, install to workspace, copy the bot token (starts xoxb-) into the SLACK_BOT_TOKEN secret.
3. Provision: Actions tab, Deploy Agent workflow, Run workflow with action=provision. This creates or reuses the vault, environment, agent, and scheduled deployment, and prints the next fire times. Rerun provision any time a secret is added or rotated. Use recreate=true after editing prompts/agent-system.md, deploy/deploy.py config, or the schedule.
4. Test: run the workflow with action=run for an immediate manual cycle, then watch the session in the Claude Console (platform.claude.com) and check for the heartbeat commit and Slack DM.
5. Operate: action=status for schedule and recent runs, pause and unpause to control the cadence. Default schedule: every 2 hours, 07:15 to 21:15 America/Chicago.

Degraded modes are deliberate: without SLACK_BOT_TOKEN drafts land in outbox/ as committed markdown; without GH_STATE_TOKEN the agent cannot persist state between runs and flags every cycle as UNPUSHED, so add that one early.

Alternative runtime: the same repo runs as a Claude Code routine (subscription-billed, connector-based). Prompts for that path are in prompts/routine-heartbeat.md and prompts/routine-fire.md; point a scheduled routine at this repo with the Slack, Apify, and Tavily connectors enabled.

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
