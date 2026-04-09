---
name: opencode-agents
description: "Delegate tasks to oh-my-openagent agents (librarian, oracle, sisyphus, prometheus, atlas, explore, metis, momus) via the opencode CLI. Use this skill whenever the user says 'use librarian to', 'use oracle to', 'let librarian', 'ask oracle to', '@librarian', '@oracle', or names any oh-my-openagent agent in the context of doing a task. Also triggers on Chinese equivalents: '用 librarian 做', '用 oracle 做', '让 librarian 帮'. Disambiguation: do NOT trigger for Oracle Database, Oracle Cloud, MongoDB Atlas, or general-purpose exploration verbs unrelated to oh-my-openagent."
---

# OpenCode Agents Skill

Delegate tasks to specialized oh-my-openagent subagents via the `opencode` CLI.

## Naming

| Term | Meaning |
|------|---------|
| **oh-my-openagent** | The plugin package (npm: `oh-my-openagent`, formerly `oh-my-opencode`) |
| **opencode** | The CLI binary used to invoke agents |
| **oh-my-openagent.json** | Config file at `~/.config/opencode/oh-my-openagent.json` |

> Canonical repo: https://github.com/code-yeongyu/oh-my-openagent

## Available Agents

| Agent | Mode | Specialization |
|-------|------|---------------|
| **sisyphus** | primary | Orchestration, task delegation, general execution |
| **atlas** | primary | Large codebase exploration, dependency analysis |
| **librarian** | subagent | External documentation lookup, web research, best practices |
| **oracle** | subagent | Analysis, Q&A, explaining complex concepts |
| **prometheus** | subagent | Planning, architecture design, high-level decisions |
| **explore** | subagent | Filesystem exploration, code search |
| **metis** | subagent | Strategy, trade-off analysis |
| **momus** | subagent | Code review, quality assurance, gap/completeness checking |

**Primary agents** (sisyphus, atlas) are top-level orchestrators invoked directly.
**Subagents** cannot be called directly via `--agent` — they are delegated to by Sisyphus internally via `call_omo_agent()`. To target a subagent, name it in the prompt text.

## How to Invoke

```bash
opencode run '<task prompt>'
```

Use **single quotes** to avoid shell expansion of special characters (see Shell Safety below).

### Optional Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--agent <name>` | Route to a specific **primary** agent only (sisyphus, atlas) | `opencode run --agent atlas 'analyze deps'` |
| `--dir <path>` | Set working directory (defaults to `process.cwd()`) | `opencode run --dir /project 'review code'` |
| `-m, --model <model>` | Override the model for this run | `opencode run -m gpt-4o 'summarize'` |

### Routing to Subagents

**Do NOT use `--agent` for subagents** — it will fail with "not a primary agent" or silently fall back to Sisyphus without proper delegation.

**Instead, name the subagent in the prompt text.** Sisyphus reads this as an instruction to delegate:
```bash
opencode run 'Use librarian to find the official React docs on useEffect'
opencode run 'Ask oracle to analyze the tradeoffs of this architecture'
opencode run 'Use momus to review the auth module for security issues'
```

The delegation is probabilistic LLM behavior — for simple tasks Sisyphus may use its own tools directly instead of delegating.

### Examples

```bash
opencode run 'search for best practices on LND channel management'
opencode run 'explain the difference between HTLC and PTLC in Lightning'
opencode run --agent atlas 'analyze dependencies across this monorepo'
opencode run --dir /path/to/project 'find all usages of the payment module'
```

## Execution Flow

This section describes how an **AI agent** (e.g., OpenClaw, Claude Code) should use this skill when a user requests an opencode agent task.

1. **Understand the task type** and whether the user named a specific agent.
2. **Read local context if needed** — use local tools (file reads, directory listings) to gather context and embed it in the prompt.
3. **Run the command** via exec. If the user named a specific subagent, include it explicitly in the prompt text:
   ```bash
   # User named an agent → embed it in the prompt
   opencode run 'Use librarian to search today'\''s weather in Tokyo'

   # No agent named → let Sisyphus auto-route
   opencode run 'search today'\''s weather in Tokyo'
   ```
4. **Return the output** to the user.
5. If the agent isn't in the list above, check `~/.config/opencode/oh-my-openagent.json` for the full configured agent list.

## Output Handling

- **stdout** — agent's response (typically Markdown)
- **stderr** — progress/debug info; ignore unless diagnosing failures
- **Exit code 0** — success; non-zero — failure
- For long outputs, summarize key findings before returning to the user

## Shell Safety

`opencode run` passes messages as JSON over HTTP — the message itself is never shell-executed. However, the shell on the caller side will expand special characters before the CLI receives them.

Always use **single quotes**:
```bash
# Safe
opencode run 'analyze the $HOME variable usage'

# Unsafe — shell expands $HOME before the CLI sees it
opencode run "analyze the $HOME variable usage"
```

If the task contains single quotes, escape them with `'\''`:
```bash
opencode run 'find all usages of the it'\''s pattern'
```

## Known Issues

### 1. Subagent results lost (background mode)

**Symptom**: You call `opencode run 'Use oracle to review ...'`, oracle runs but no result comes back.

**Root cause**: Sisyphus calls `call_omo_agent()` with `run_in_background=true` by default. Background subagent results are consumed internally and never returned to stdout.

**Fix**: Add `prompt_append` to the sisyphus config in `~/.config/opencode/oh-my-openagent.json` to force synchronous mode:
```json
{
  "agents": {
    "sisyphus": {
      "prompt_append": "CRITICAL RULES:\n1. When calling call_omo_agent with ANY subagent_type, you MUST set run_in_background=false (synchronous mode). NEVER use run_in_background=true — background mode causes results to be lost.\n2. When the user explicitly names a subagent (e.g. 'Use oracle to...', 'Ask librarian to...'), you MUST delegate to that subagent via call_omo_agent. Do NOT handle it yourself or refuse."
    }
  }
}
```

### 2. `--agent` with subagent names

**Symptom**: `opencode run --agent librarian '...'` fails or silently falls back.

**Root cause**: `--agent` only accepts primary agents (sisyphus, atlas). Subagent names are rejected.

**Fix**: Never use `--agent` for subagents. Name them in the prompt text instead.

## Notes

- **Config**: `~/.config/opencode/oh-my-openagent.json` — agent models, prompt_append, and settings
- **CWD**: inherited from the calling process; override with `--dir <path>`
- **Recursion**: The `call_omo_agent()` tool has built-in recursion protection (max depth 3, cycle detection). Shell-invoked `opencode run` starts an independent process tree with no cross-process guard — avoid chaining shell invocations inside tasks already started via `opencode run`.
- **If `opencode` is not in PATH**: report the error clearly and suggest installing the oh-my-openagent plugin via `npm install -g oh-my-openagent`
