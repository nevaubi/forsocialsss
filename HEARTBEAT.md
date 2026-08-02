# HEARTBEAT.md

One cycle, executed top to bottom. Steps 0 through 3 run every cycle and stay cheap. Steps 4 and 5 run only when gates open.

## Mode check

- Scheduled trigger: run the full loop below.
- API fire trigger: read prompts/routine-fire.md and handle the payload first. A reply directive (approve, edit, kill, hold, status, posted) is handled through step 1 and the cycle ends there unless the payload says otherwise. A breaking-news nudge triggers a targeted scan on that topic only, then continues from step 3 for that topic.

## 0. Orient

- Note the current datetime in America/Chicago.
- Complete the boot sequence in CLAUDE.md.
- Read the last 10 run-log entries. If the previous run errored mid-write, reconcile first: every state file must parse; repair from git history if needed.

## 1. Inbox

Read the Slack DM thread since the last processed timestamp (recorded in run-log entries).

- approve: mark the queue draft approved. Reply in-thread with the final paste-ready copy (re-run the em dash scan), the recommended posting window, and "reply 'posted <url>' when live". Move it to state/posted.json with status awaiting_manual_post. Remind once after 24h, never nag.
- edit: <notes>: revise with the draft skill, resend in the same thread, keep status drafted.
- kill: <reason>: archive the draft in queue.json with the reason. If the reason generalizes, append it to state/lessons.md.
- hold: leave the draft untouched for 24 hours.
- status: send the status digest per the slack-brief skill.
- posted <url>: record the URL and date in posted.json, status live.
- Anything else substantive from Firas: treat as instruction, act within the write policy, log it.

## 2. Scan (budgeted)

Run the pulse skill: pull deltas from sources/sources.md within budget, normalize to signals, update topic clusters with momentum, saturation, and fit scores in state/topics.json, decay stale topics, and check watchlist triggers.

## 3. Decide

For each active topic, exactly one outcome, each logged with a reason:

- ignore: momentum or fit too low.
- watchlist: promising but early. Write an explicit trigger condition into watchlist.json ("escalate if X ships", "escalate if 3+ tracked creators post on it", "revisit in 2 cycles").
- escalate: all gates pass.

Escalation gates, all required:

- momentum >= 6 and fit >= 7 and saturation <= 5 (rubrics in the pulse skill)
- the cadence governor (step 5) allows a new draft
- fewer than 2 drafts in queue with status drafted or delivered
- the topic violates nothing in identity/never.md

Maximum one escalation per cycle. If two topics qualify, take the higher fit and watchlist the other with trigger "next cycle if still qualifying".

## 4. Escalate

- Run the deep-dive skill. Output: a sourced angle memo in queue.json, status researched. Its kill criteria apply; a killed escalation is logged and dropped without regret.
- Run the draft skill on the memo. Output: post copy, status drafted, with a predicted engagement band.
- Run the slack-brief skill. Output: the draft DM, status delivered.

## 5. Cadence governor

- Target: 7 posts per rolling 14 days, computed from posted.json.
- Minimum 20 hours between posts Firas actually publishes.
- Ahead of target: raise every escalation gate by 1 point.
- 4+ days with no delivery and no post: send the one-line held summary so silence is visibly a decision.
- Posting-window defaults: Tuesday through Thursday, 08:00-10:00 or 11:30-13:00 America/Chicago. Weekends only for exceptional timeliness. These are priors; retro updates them from our own data.

## 6. Log and commit

Append one run-log line (schema in state/SCHEMA.md): timestamp, mode, signals seen, active topic count, decision, reason, spend, Slack messages sent. Commit everything with the prescribed message format, then push to origin main per the Runtime section of CLAUDE.md.

## 7. Retro trigger

If 7 or more days have passed since the last dated retro entry in state/lessons.md, run the retro skill before the final commit.

## Failure handling

- A dead source is logged and skipped, never fatal.
- Apify budget exhausted mid-scan: finish scoring with what you have, log budget_capped.
- Slack unreachable: still update state and commit; deliver next cycle.
- Never end a cycle with unparseable JSON under state/.
