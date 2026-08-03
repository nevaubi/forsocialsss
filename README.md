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
2. Slack app, about five minutes: api.slack.com/apps, create app from scratch in the workspace, then under OAuth and Permissions add these bot token scopes: chat:write, im:read, im:write, im:history, users:read, reactions:read, reactions:write, channels:read, channels:history, channels:join, groups:read, groups:history, mpim:read, mpim:history, files:read. Install (or reinstall after any scope change) to the workspace and copy the bot token (starts xoxb-) into the SLACK_BOT_TOKEN secret. For full workspace search, also add the user token scope search:read, reinstall, and copy the user token (starts xoxp-) into a SLACK_USER_TOKEN secret, then rerun provision.
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

## The assistant

A second agent runs alongside the heartbeat: Kimi K3 on the Fireworks serverless endpoint, polling the same Slack DM every 5 minutes (assistant/assistant.py, Assistant Chat workflow). No command syntax: the assistant is an agentic tool loop. Questions get grounded answers from the repo, run log, live deployment status, and web research through Tavily when the answer lives outside the repo. Plain-language instructions ("raise the news weight to 25", "adjust the heartbeat system prompt", "add a new skill file") are executed like an engineer would: read the target files, make exact-match edits (whole-file writes only for new files), verify with py_compile or yaml checks in a credential-scrubbed shell, review the diff, then commit straight to main with the commit link in the reply. "Revert that" undoes the last assistant commit. Asking for a pull request routes through the Assistant Apply workflow for review instead. It also produces deliverables: PDF reports (fpdf2/weasyprint), slide decks (python-pptx), and infographics (PIL/matplotlib, with FLUX image generation on the existing Fireworks key for illustrative art), following the recipes and quality checklists in assistant-skills/ and uploading results to the DM. File uploads need the files:write bot scope on the Slack app. Structural guards live in the commit tool: path traversal blocked, the hard rules section of CLAUDE.md cannot be removed, em dashes cannot be committed, and any edit gutting most of a file is held until the word confirm appears. The heartbeat pulls main every cycle, so changes take effect on its next fire. Handled messages get a robot_face reaction; heartbeat keywords (approve, edit:, kill:, hold, status, posted, retro now) are left for the heartbeat.

## Instant replies (Cloudflare Worker)

The cron poller answers within about 5 minutes. For replies in a few seconds, deploy assistant/worker.js as a Cloudflare Worker; Slack then pushes each DM to it the moment it is sent. The poller stays on as the fallback and as the apply: handler, and the robot_face reaction keeps the two from double-answering. Setup, about ten minutes:

1. dash.cloudflare.com, free account, Workers and Pages, Create Worker, any name, then paste the contents of assistant/worker.js over the starter code and deploy. Copy the worker URL.
2. In the worker's Settings, Variables and Secrets, add type-Secret entries: SLACK_BOT_TOKEN (the xoxb token), SLACK_SIGNING_SECRET (Slack app, Basic Information, Signing Secret), FIREWORKS_API_KEY. Optional: ANTHROPIC_API_KEY (adds live deployment status to answers) and GH_DISPATCH_TOKEN (a GitHub token with actions write; makes apply: dispatch the PR workflow instantly instead of waiting for the cron).
3. In the Slack app, Event Subscriptions, toggle Enable, set Request URL to the worker URL (Slack verifies it immediately; the worker answers the challenge), then under Subscribe to bot events add message.im and save. Reinstall if Slack prompts.
4. DM the bot. The reply should land in a few seconds, threaded, with a robot_face reaction on your message.

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
