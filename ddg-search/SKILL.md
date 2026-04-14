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
---

# DDG Search

Server: `npx --yes @oevortex/ddg_search@1.2.2`, JSON-RPC over stdio.

```bash
_MCP_INIT='{"jsonrpc":"2.0","method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"cli","version":"1.0.0"}},"id":1}\n{"jsonrpc":"2.0","method":"notifications/initialized"}\n'
_MCP_SRV="npx --yes @oevortex/ddg_search@1.2.2"

mcp() { printf "${_MCP_INIT}$1" | eval "$_MCP_SRV" 2>/dev/null | grep -m1 "\"id\":$2"; }

# Discover tools and schemas
mcp '{"jsonrpc":"2.0","method":"tools/list","id":2}\n' 2

# Call a tool
mcp '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"TOOL_NAME","arguments":ARGS_JSON},"id":3}\n' 3
```
