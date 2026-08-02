# sources.md

Signal registry and budgets. The pulse skill reads this every cycle. Query tuning, creator rotation, and sub-budget adjustments are Tier A with evidence; the hard caps are Tier B.

## Hard caps (Tier B)

- Apify spend per heartbeat cycle: $0.30 hard cap, $0.15 typical target.
- Apify spend per retro: $0.30 hard cap.
- On cap: stop scraping immediately, score with what you have, log budget_capped in the run log.

## LinkedIn, session-free scrapers on Apify

Access path: the Apify MCP connector attached to the routine. Fallback: direct HTTPS to api.apify.com with the APIFY_TOKEN environment variable. Never any cookie- or session-based LinkedIn access (hard rule 4).

Unit prices below are the observed bronze-tier per-event rates; re-check them quarterly.

1. harvestapi/linkedin-post-search ($0.002 per post): the trend corpus. Per cycle: at most 2 searchQueries, maxPosts 15 each, postedLimit past-24h, sortBy date. Choose queries from active topic keywords first, then rotate the seed pool below.
2. harvestapi/linkedin-profile-posts ($0.002 per post): tracked-creator sweep. Per cycle: at most 10 creators, round-robin through sources/creators.json using rotation_cursor, maxPosts 3 each, postedLimit past-week, includeReposts false.
3. harvestapi/linkedin-post-comments ($0.002 per comment): deep-dive only. At most 2 posts, maxItems 20 each. Purpose: what practitioners are actually asking about the topic.
4. harvestapi/linkedin-profile-search: creator URL resolution during bootstrap only. searchQuery = name plus strongest keyword, maxItems 3, at most 5 resolutions per cycle.
5. harvestapi/linkedin-profile-posts on Firas's own profile (https://www.linkedin.com/in/firas-shaher/): retro only, weekly, scrapeComments true, maxComments 25.

## Seed query pool (rotate at most 2 per cycle; retro tunes)

"multi-agent systems", "context engineering", "AI agents production", "agent memory", "AI evals", "RAG retrieval quality", "legal AI", "litigation technology", "law firm AI adoption", "AI compliance audit", "Claude Code", "AI agents finance research"

## Non-LinkedIn sources, free, every cycle

- Hacker News (Algolia API): https://hn.algolia.com/api/v1/search_by_date?tags=story&query=QUERY&numericFilters=points%3E20 for pillar queries, plus the front page via https://hn.algolia.com/api/v1/search?tags=front_page
- arXiv API: http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.CL&sortBy=submittedDate&sortOrder=descending&max_results=15 (scan titles and abstracts only)
- Vendor primary sources by fetch when a claim references them: anthropic.com/news, openai.com/news, blog.google/technology/ai. Verify at the primary source before citing anything.
- Legal tech press by fetch, headline scan: lawsitesblog.com, artificiallawyer.com
- Platform web search: verification and why-now context during deep-dive. Not a primary trend source.

## Network allowlist for the routine environment

api.apify.com, hn.algolia.com, export.arxiv.org, anthropic.com, openai.com, blog.google, lawsitesblog.com, artificiallawyer.com, plus the platform's built-in web search and fetch.

## Source hygiene

- Primary sources outrank coverage. A claim sourced only to a growth blog is a prior, not a fact.
- Every signal record keeps its URL. Drafts cite only from the angle memo.
- A source that returns nothing useful for 14 consecutive days gets flagged in the retro digest for pruning.
