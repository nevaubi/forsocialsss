---
name: slack-brief
description: Every Slack message format the agent is allowed to send, and the rules around them. DM delivery of drafts, held notices, status digests, retro digests, and approval follow-through.
---

# Slack brief

Target: DM to Firas per the Slack protocol in CLAUDE.md. All follow-ups about a draft are thread replies on its original delivery message (store slack_ts in the queue entry). Quiet hours per CLAUDE.md: nothing between 22:00 and 07:00 America/Chicago; queue it.

## Draft delivery (maximum 1 per cycle, two messages)

Message 1, the brief:

Draft ready: <topic label> [<pillar>, <format>]
Why now: <two lines max: the momentum and timing story>
Why you: <one line: the standing>
Scores: momentum <m>, saturation <s>, fit <f>. Prediction: <band>.
Recommend: post <specific window, e.g. Tue 08:30-09:30 CT>. Be reachable for ~45 min after posting to reply to early comments.
Reply: approve | edit: <notes> | kill: <reason> | hold

Message 2, same thread: the post text inside a single code block, exactly paste-ready. Nothing else in the message. The code block keeps LinkedIn formatting intact when copied.

## Held notice (only after 4 quiet days, one line, no thread)

held: nothing cleared the bar since <date>. Watching: <2-3 slugs, one-word reason each>.

## Status digest (on "status" reply)

Cadence: <n> posts in the last 14 days (target 7). Queue: <counts by status>. Top topics: <up to 3 with m/s/f scores>. Spend this week: $<x.xx>. Last retro: <date>. Pending on you: <any draft awaiting reply, with age>.

## Comment opportunities (inside the weekly retro digest, 3-5 items)

Each item: author, post gist in 15 words or fewer, the additive point Firas could make in 25 words or fewer, URL. Provide the point, never the full comment. His comments have to be his.

## Approval follow-through

On approve: reply in-thread with the final copy (re-run the em dash scan first), the recommended window, and the line "reply 'posted <url>' when it's live". On "posted <url>": record it in posted.json, status live, and confirm with one short line.

## Rules

- Plain Slack markdown. Short lines. The only code block is the post copy.
- No emojis in drafts. In operational messages, at most a single check mark on confirmations.
- Never deliver the same draft as a new message; revisions stay in the thread.
- Never send more than 3 messages in one cycle outside of an active reply exchange.
