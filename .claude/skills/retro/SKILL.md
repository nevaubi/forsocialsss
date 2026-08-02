---
name: retro
description: Weekly self-improvement cycle. Measure real engagement, score prediction calibration, mine comments, update the playbook and identity files within the write policy, log lessons, and send the digest.
---

# Retro

Runs when HEARTBEAT step 7 fires (7+ days since the last retro entry) or when Firas replies "retro now".

## Procedure

1. Measure. harvestapi/linkedin-profile-posts on Firas's own profile, scrapeComments true, maxComments 25, retro budget cap applies. Update the engagement block for every post 21 days old or newer in posted.json.
2. Calibrate. Compare each post's predicted band to actuals relative to the account baseline. Record hit or miss in the post's notes. Three misses in the same direction across the log means the prediction rubric is biased: propose the rubric change (Tier B, skills are propose-only).
3. Mine. Read the comments and commenters on his posts. Who is actually showing up: roles, seniority, lanes? Which lines got quoted, questioned, or pushed back on? Extract at most 3 findings; pushback is the most valuable finding, not a problem.
4. Playbook. Update playbook/linkedin-craft.md entries where local evidence now exists: mark validated or refuted with the date and the data. Never delete a prior; supersede it and note it in the change log.
5. Sources. Score signal quality per creator (which tracked creators produced signals that reached escalation this month?). Prune persistent zeros, add up to 2 newly discovered high-signal authors found via post-search results (Tier A). Tune the seed query pool the same way.
6. Identity. If the evidence justifies changes to identity/voice.md or identity/strategy.md, apply the minimal edit and post the full diff plus the evidence to Slack (Tier B). Anything touching identity/never.md, CLAUDE.md, HEARTBEAT.md, prompts/, or skills: describe the proposal in Slack and do not apply it.
7. Lessons. Append one dated entry to state/lessons.md: what worked, what did not, one process change for next week.
8. Digest to Slack: metrics summary against the phase goals in strategy.md, the findings, diffs applied and proposals pending, and 3-5 comment opportunities per the slack-brief format.
9. Commit: retro: <ISO week> <one-line summary>.

## Honesty rules

- Small-n humility. Under 10 published posts, every finding is directional and the digest says so explicitly.
- Never optimize toward anything on the never list. If a bait-adjacent pattern is winning numerically, flag the conflict to Firas instead of adopting it. The account is playing a long game on credibility.
- Engagement is calibration data. The optimization target is the quality bar and audience fit, in that order.
