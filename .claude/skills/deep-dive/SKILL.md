---
name: deep-dive
description: Escalation research protocol that produces a sourced angle memo, or a documented kill. Run only when heartbeat gates pass. Most escalations should die here; that is the design working.
---

# Deep dive

Purpose: earn the right to draft. The output is either an angle memo in queue.json or a logged kill. Both are wins over a weak post.

## Procedure

1. Go to the primary source: the paper, the repo, the release notes, the filing, the documentation, the announcement itself. Coverage articles are context, never the citation of record.
2. Verify every claim you intend to use. A number that cannot be found at a primary source does not go in the memo.
3. Optional, budget permitting: harvestapi/linkedin-post-comments on at most 2 high-engagement posts about the topic. Purpose: what practitioners are actually asking and where the confusion is. That confusion is often the angle.
4. Find the angle. Apply these tests in order, and stop at the first failure:
   - Standing: does identity/profile.md give Firas authority or an informed-practitioner lens here?
   - Additive: what does this say that existing coverage does not? A restatement is a kill.
   - Falsifiable and specific: "X matters" is a kill. "X breaks under Y in production, here is the mitigation" survives.
   - Fit: serves a pillar and at least one priority audience.
5. Write the angle memo into queue.json per state/SCHEMA.md: claim, evidence with URLs, why_now, why_firas, counterpoint, artifact.
   - The counterpoint must be a steelman. If you cannot write a credible opposing view, you have not researched enough.
   - The artifact is mandatory: a concrete number, decision, or failure the post will carry. No artifact, no post.

## Kill criteria (log the reason, stop, move on)

- Cannot verify the central claim at a primary source.
- No angle beyond restatement, or the angle is already visible among tracked creators.
- No standing, or any contact with identity/never.md.
- Timeliness gone: would land 4+ days after peak with no evergreen value.
- The honest version of the post would be boring. Boring and true still loses to silence.

## Budget

The equivalent of 15-25 minutes of focused work. One deep-dive per cycle, maximum. Kills that generalize get one line in state/lessons.md.
