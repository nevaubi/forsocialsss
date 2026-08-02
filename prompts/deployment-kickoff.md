Scheduled heartbeat fired. Boot per your system prompt, then run one HEARTBEAT.md cycle in scheduled mode.

Requirements for this run:

- Stay within the budgets in sources/sources.md. Stop scraping the moment a cap is hit.
- All LinkedIn and X data comes from the session-free Apify actors listed in sources/sources.md, called over REST with the APIFY_API_KEY environment variable. Never any cookie or credentialed access.
- Verification and research go through Tavily REST with TAVILY_API_KEY, plus the built-in web_search and web_fetch tools.
- Slack communication only through the formats in .claude/skills/slack-brief/SKILL.md, using the Slack Web API with SLACK_BOT_TOKEN per the Runtime section of CLAUDE.md.
- Commit every state change and push to origin main before finishing, using the message formats in CLAUDE.md. A quiet cycle still gets a run-log line, a commit, and a push.
- If anything fails, follow the failure handling section of HEARTBEAT.md, degrade per the Runtime section of CLAUDE.md, and still commit the log.
