# sources.md

Signal registry and budgets. The pulse skill reads this every cycle. Query tuning, creator rotation, and sub-budget adjustments are Tier A with evidence; the hard caps are Tier B.

## Hard caps (Tier B)

- Apify spend per heartbeat cycle: $0.30 hard cap, $0.15 typical target.
- Apify spend per retro: $0.30 hard cap.
- On cap: stop scraping immediately, score with what you have, log budget_capped in the run log.

## LinkedIn, session-free scrapers on Apify

Access path: direct HTTPS to api.apify.com with an Authorization: Bearer APIFY_API_KEY header (vault-injected environment variable). Run-sync endpoints keep it to one call per actor run. Never any cookie- or session-based LinkedIn access (hard rule 4).

Unit prices are observed bronze-tier per-event rates; re-check quarterly.

1. harvestapi/linkedin-post-search ($0.002 per post): the trend corpus. Per cycle: at most 2 searchQueries, maxPosts 15 each, postedLimit 24h, sortBy date. Input note, observed 2026-08-02: postedLimit only accepts any, 1h, 24h, week, month, 3months, 6months, year; "past-week" style values fail with invalid-input and burn a call. Choose queries from active topic keywords first, then rotate the seed pool below. Tuning note, observed 2026-08-02 (postedLimit week, sortBy date, 2 queries, 30 posts): every returned post was under two hours old, so sortBy date makes postedLimit almost irrelevant and gives a "what is being posted right now" sample. That is the right instrument for live saturation and the wrong one for finding the week's best posts on a topic; use sortBy relevance when the question is who owns an angle already.
2. harvestapi/linkedin-profile-posts ($0.002 per post): tracked-creator sweep. Per cycle: at most 10 creators, round-robin through sources/creators.json using rotation_cursor, maxPosts 3 each, postedLimit past-week, includeReposts false.
3. harvestapi/linkedin-post-comments ($0.002 per comment): deep-dive only. At most 2 posts, maxItems 20 each.
4. harvestapi/linkedin-profile-search: creator URL resolution during bootstrap only. maxItems 3, at most 5 resolutions per cycle.
5. harvestapi/linkedin-profile-posts on Firas's own profile (https://www.linkedin.com/in/firas-shaher/): retro only, weekly, scrapeComments true, maxComments 25.

## X (Twitter), session-free via Apify

Actor: kaitoeasyapi/twitter-x-data-tweet-scraper-pay-per-result-cheapest ($0.00022 per tweet). Purpose: earliest signal on AI engineering discourse; X leads LinkedIn by 1-3 days on most technical topics.

- Per cycle: at most 2 searchTerms, maxItems 30 total, queryType Top.
- Query template: "<topic phrase>" min_faves:<floor> -filter:retweets lang:en since:<48h ago date>. Floors: broad terms like "AI agents" use min_faves:400, mid terms like "multi-agent" or "context engineering" use 100, niche terms like "legal AI" use 40.
- Handle watch, rotate 1 query some cycles: from:askalphaxiv OR from:trailofbits OR from:ZachAbramowitz OR from:DailyDoseOfDS_ OR from:_avichawla (paper breakdowns, agent security, legal AI market). Retro maintains this list.
- Noise filter, validated 2026-08-02 on an 81-tweet pull: roughly half of keyword results are course-listicle bait ("Don't waste 2 years...", "$500 course" framing) or crypto agent-token promotion. Discard on sight; do not let them into topic scores except as saturation evidence. Treat surviving X claims as leads to verify at primary sources, never as citable facts.

## Tavily, continuous research layer (REST with TAVILY_API_KEY)

POST https://api.tavily.com/search with the TAVILY_API_KEY environment variable in the JSON body. Bills against Firas's Tavily account quota; keep calls purposeful.

- Every cycle: 1-2 tavily_search calls, topic news, time_range day or week: one on the highest-momentum active topic, and on alternating cycles one standing sweep of "legal AI" news.
- Deep-dive: tavily_search advanced plus crawl/extract of the primary source behind the angle memo. Tavily is the default verification path before any claim enters a memo.
- tavily_research: reserved for retro-level questions at most once weekly; it is the expensive call.

## Seed query pool (rotate at most 2 per cycle per platform; retro tunes)

"AI architecture", "agent harness", "multi-agent systems", "context engineering", "agent memory", "AI evals", "AI agents production", "legal AI", "litigation AI", "litigation technology", "law firm AI adoption", "legal tech acquisition", "AI compliance audit", "AI agent security"

## Non-LinkedIn free sources, every cycle

- Hacker News (Algolia API): https://hn.algolia.com/api/v1/search_by_date?tags=story&query=QUERY&numericFilters=points%3E20 plus front page via https://hn.algolia.com/api/v1/search?tags=front_page
- arXiv API: https://export.arxiv.org/api/query?search_query=cat:cs.AI&sortBy=submittedDate&sortOrder=descending&max_results=15 (titles and abstracts only). Observed 2026-08-02: the http scheme returns an empty body in the sandbox and the OR-joined category query returns nothing; use https and a single category, then a second call for cs.CL if needed. Observed 2026-08-02 19:20 CT: export.arxiv.org returned DNS resolution failure in the sandbox on both attempts this cycle even over https, so the source was logged dead and skipped. If it fails on two consecutive cycles, raise it in the retro as an allowlist or DNS question rather than retrying inside the scan.
- Vendor primary sources by fetch when a claim references them: anthropic.com/news, openai.com/news, blog.google/technology/ai
- Legal tech press by fetch, headline scan: lawsitesblog.com, artificiallawyer.com, law.com/legaltechnews, complexdiscovery.com

## Network access under the Managed Agents runtime

Sandbox egress is limited to the allowlist in deploy/deploy.py: api.apify.com, api.tavily.com, slack.com, github.com and githubusercontent, hn.algolia.com, export.arxiv.org, api.fireworks.ai. Press sites, vendor blogs, and everything else on this page are read through the built-in web_fetch and web_search tools, which are governed separately from sandbox networking.

## Source hygiene

- Primary sources outrank coverage. A claim sourced only to a growth blog or an X thread is a prior, not a fact.
- Every signal record keeps its URL. Drafts cite only from the angle memo.
- A source that returns nothing useful for 14 consecutive days gets flagged in the retro digest for pruning.
