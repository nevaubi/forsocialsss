# SCHEMA.md

Contracts for every file under state/. All JSON must parse at the end of every cycle. Timestamps are ISO 8601 with offset, America/Chicago.

## topics.json

{
  "updated": "2026-08-02T14:00:00-05:00",
  "topics": [
    {
      "slug": "kebab-case-stable-id",
      "label": "Human readable topic name",
      "pillar": "P1 | P2 | P3 | P4",
      "first_seen": "iso",
      "last_signal": "iso",
      "momentum": 0,
      "saturation": 0,
      "fit": 0,
      "signal_count_24h": 0,
      "sources": ["up to 5 representative URLs"],
      "notes": "one or two lines of context",
      "status": "active | decaying | archived"
    }
  ]
}

Scores are integers 0-10 per the rubrics in .claude/skills/pulse/SKILL.md.

## watchlist.json

{
  "updated": "iso",
  "items": [
    {
      "slug": "matches a topic slug",
      "trigger": "explicit condition, e.g. 'escalate if the model actually ships' or '3+ tracked creators post on it'",
      "added": "iso",
      "expires": "iso, default added + 7 days",
      "notes": "optional"
    }
  ]
}

## queue.json

{
  "updated": "iso",
  "drafts": [
    {
      "id": "slug-YYYYMMDD",
      "slug": "topic slug",
      "pillar": "P1..P4",
      "status": "researched | drafted | delivered | approved | killed | expired",
      "angle_memo": {
        "claim": "the falsifiable, specific claim",
        "evidence": [{"point": "fact used", "url": "primary source"}],
        "why_now": "timing rationale",
        "why_firas": "standing rationale",
        "counterpoint": "the steelmanned opposite view",
        "artifact": "the concrete number, decision, or failure the post carries"
      },
      "post_text": "final copy exactly as it would be pasted",
      "format": "text | document",
      "predicted": {"band": "quiet | normal | above", "rationale": "one line"},
      "delivered_at": "iso or null",
      "slack_ts": "message ts of the delivery DM, for threading",
      "resolution": "null | approved | killed: reason | expired"
    }
  ]
}

Drafts move to expired after 72 hours delivered with no reply; a one-line note goes in the next status digest.

## posted.json

{
  "updated": "iso",
  "posts": [
    {
      "id": "slug",
      "url": "linkedin post url",
      "posted_at": "YYYY-MM-DD",
      "pillar": "P1..P4",
      "format": "text | document",
      "title": "short label",
      "doc_pages": 0,
      "summary": "two lines max",
      "predicted": {"band": "...", "rationale": "..."},
      "engagement": {"checked_at": "iso", "likes": 0, "comments": 0, "shares": 0},
      "notes": "retro observations"
    }
  ]
}

## run-log.jsonl

One JSON object per line, append only:

{"ts": "iso", "mode": "heartbeat | fire | retro | init", "signals": 0, "topics_active": 0, "decision": "escalated slug | held | inbox-only | budget_capped | error-recovered", "reason": "one line", "spend_usd": 0.0, "slack_sent": 0, "commit": "short hash or message stub"}

The inbox step also records the last processed Slack timestamp inside the reason field when relevant ("processed slack through <ts>").

## lessons.md

Markdown, append only, dated H2 entries, newest last. Retro owns it; heartbeat may append generalizable kill reasons.
