# Routine prompt: scheduled heartbeat

Alternative runtime only. The live runtime is a Claude Managed Agents scheduled deployment (see deploy/ and prompts/agent-system.md); keep this file if you ever want to run the same agent as a Claude Code routine instead.

Paste the block below as the prompt of the scheduled routine at claude.ai/code.

---

You are the agent defined by this repository. Read CLAUDE.md first and follow it exactly, including the boot sequence. Then execute HEARTBEAT.md end to end for one cycle in scheduled mode.

Requirements:
- Stay within the budgets in sources/sources.md. Stop scraping the moment a cap is hit.
- All LinkedIn data comes from the session-free Apify actors listed in sources/sources.md. Never any cookie or credentialed access.
- Slack communication only through the formats in .claude/skills/slack-brief/SKILL.md.
- Commit every state change before finishing, using the message formats in CLAUDE.md. A quiet cycle still gets a run-log line and a commit.
- If anything fails, follow the failure handling section of HEARTBEAT.md and still commit the log.
