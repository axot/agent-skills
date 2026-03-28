---
name: ddg-search
description: >
  General-purpose web search using DuckDuckGo and AI-synthesized search engines.
  Use this skill for web searches, current information, fact-checking, news, and research
  on any topic where live internet data is needed. Supports all languages.
  Three modes: fast web results, AI-synthesized answers (IAsk.ai, great for deep questions
  and academic research), and Monica AI synthesis.
  Trigger on: "search for", "look up", "find information about", "what is the latest",
  "search the web", "find out about", "what happened with", "current status of",
  "recent news", "is X still true", "查一下", "搜索", "查资料", "上网查", "検索して", "調べて",
  any question requiring real-time or post-training web data.
  Do NOT trigger for: code exploration, local file analysis, codebase-internal questions,
  or well-established facts fully covered by training knowledge.
  Note: if the `agent-reach` skill is also available, prefer `ddg-search` for pure web
  search tasks; prefer `agent-reach` when the task involves social platforms (Twitter,
  Reddit, YouTube, WeChat, Bilibili, etc.) or platform-specific APIs.
mcp:
  ddg-search:
    command: npx
    args:
      - "@oevortex/ddg_search@1.2.2"
---

# DDG Search — Usage Guide

> **When NOT to search**: Skip search for well-established facts your training covers
> reliably (e.g. "what is a list comprehension"). Search when the answer may have changed,
> when you need citable sources, or when the user explicitly asks you to look something up.

## Tool Selection

| Tool | Best for | Latency | Caching |
|------|----------|---------|---------|
| `ddg-search_web-search` | URLs, snippets, news, source discovery | Fast | 5 min (query string only) |
| `ddg-search_iask-search` | Deep questions, academic, analysis, how-to | Slow (≤30s) | 5 min (query+mode+detail) |
| `ddg-search_monica-search` | Conversational synthesis, fallback | Slow (≤60s) | **None** — every call hits the API |

## `ddg-search_web-search` — Standard Results

Parameters:
- `query` (required): search query in any language
- `mode`: `"short"` (default) or `"detailed"`
  - `"short"` → title + URL + snippet (1 HTTP request, fast)
  - `"detailed"` → additionally fetches each result's full page via Jina Reader (headless browser, handles JS-rendered pages). Content returned as **cleaned Markdown**. Parallel fetches, 8s per URL / 15s total timeout.
- `numResults`: 1–20, default **3**

> ⚠️ **Cache footgun**: The cache key is the **query string only**. If you run
> `web-search(query="X", mode="short")` then `web-search(query="X", mode="detailed")`
> within 5 minutes, you'll get the cached short results.
> **Request `mode="detailed"` on the first call.** To bust the cache, slightly rephrase
> the query. To read a single URL directly, use the `webfetch` tool instead.

## `ddg-search_iask-search` — AI-Synthesized Answers

Parameters:
- `query` (required): natural language question
- `mode` (default: `"thinking"` at runtime): controls the AI persona
  - `"question"` — everyday factual questions
  - `"academic"` — scholarly research, citations, scientific topics
  - `"forums"` — community opinions, personal experiences, troubleshooting
  - `"wiki"` — encyclopedic background, concepts, definitions, history
  - `"thinking"` — complex multi-step reasoning and deep analysis
- `detailLevel`: `"concise"` | `"detailed"` | `"comprehensive"` (default: standard)

## `ddg-search_monica-search` — Monica AI Synthesis

Parameters:
- `query` (required): up to 5,000 characters

No mode control. Use when:
- `iask-search` is slow or unavailable
- You want a second synthesis perspective

> **Rate limiting**: Monica enforces a 429 rate limit — space out repeated Monica calls.
> No caching — every call hits the API.

## Multilingual Queries

Query in the language that yields the best results for the topic:
- Japanese, Korean, Chinese topics → query in that language
- Global/tech topics → English often yields richer results
- For cross-cultural topics, run parallel queries in multiple languages

## Common Workflows

### Quick fact check
```
ddg-search_web-search(query="...", numResults=5)
```

### Deep research
```
ddg-search_iask-search(query="...", mode="thinking", detailLevel="comprehensive")
ddg-search_web-search(query="...", numResults=5)
webfetch(url="https://...")
```

### Current events / news
```
ddg-search_web-search(query="... site:reuters.com OR site:bbc.com", mode="detailed", numResults=5)
```

### Technical how-to or academic topic
```
ddg-search_iask-search(query="...", mode="academic", detailLevel="detailed")
```

### Community opinions / troubleshooting
```
ddg-search_iask-search(query="...", mode="forums", detailLevel="detailed")
```

## When Things Go Wrong

- **Empty results** → rephrase the query (different keywords, add/remove qualifiers) and retry
- **Monica 429 rate limit** → switch to `iask-search` or `web-search` instead
- **iask-search timeout** → fall back to `monica-search` or `web-search`
- **All three fail** → tell the user you couldn't retrieve live results and offer to answer from training knowledge with caveats

## Citation Format (Required)

Every piece of information sourced from search must be cited **inline**, at the exact sentence where it appears — not just in a list at the end.

**Correct — inline citation:**
> DeepSeek R1 achieved 79.8% on AIME 2024, matching OpenAI o1 ([Epoch AI](https://epoch.ai/...)).
> Supabase Pro costs $25/month and includes auth, storage, and realtime ([Supabase Pricing](https://supabase.com/pricing)).

**Wrong — end-only citation:**
> DeepSeek R1 achieved 79.8% on AIME 2024.
> ...
> Sources: Epoch AI, Supabase Pricing

The reader should be able to click the link at the point of the claim. A "Sources" section at the end is fine as a summary but never replaces inline citations.

## Query Tips

- Be specific: `"Python asyncio error handling 2024"` beats `"Python async"`
- Use quotes for exact phrases: `"model collapse" definition`
- Add time signals when recency matters: include `"2025"` or `"latest"`
- Site filter for trusted sources: `query site:docs.python.org`
- Comparisons: use `"X vs Y"` with `web-search`, or `iask-search` with `mode="thinking"`
