# Routine prompt: API fire trigger

Alternative runtime only. The live runtime is a Claude Managed Agents scheduled deployment (see deploy/ and prompts/agent-system.md); keep this file if you ever want to run the same agent as a Claude Code routine instead.

The same routine can carry an API trigger. When fired, the POST payload text arrives as input. Handle it by class:

## Reply directives (came from Firas via the Slack webhook shortcut)

Payload starts with one of: approve, edit:, kill:, hold, status, posted. Treat it exactly like the matching Slack inbox keyword in HEARTBEAT.md step 1, resolve it against the current queue, respond in the existing Slack thread, commit as fire: <keyword>. Do not run a scan unless the payload asks for one.

## Breaking-news nudge

Any payload beginning with "breaking:" or otherwise describing an event. Run a targeted pulse on that topic only (budget rules still apply), then continue from HEARTBEAT step 3 for that topic. The normal escalation gates still apply, with one exception: a direct instruction from Firas to draft overrides the momentum gate, never the never.md check.

## Unknown payloads

Treat as a nudge, act conservatively, log verbatim in the run log, commit as fire: unknown.
