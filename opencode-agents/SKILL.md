---
name: opencode-agents
description: Delegate tasks to OpenCode agents (librarian, oracle, sisyphus, prometheus, atlas, explore, metis, momus) via the oh-my-opencode plugin. Use this skill whenever the user says "use librarian to", "use oracle to", "let librarian", "ask oracle to", "@librarian", "@oracle", or names any oh-my-opencode agent in the context of doing a task. Also triggers on Chinese equivalents: "用 librarian 做", "用 oracle 做", "让 librarian 帮". Do NOT use local tools when the user explicitly asks to route through an opencode agent.
---

# OpenCode Agents Skill

Delegate tasks to specialized OpenCode agents via the oh-my-opencode plugin system.

## Available Agents

| Agent | Specialization |
|-------|---------------|
| **librarian** | Literature research, external documentation lookup, best practices search |
| **oracle** | Analysis, Q&A, explaining complex concepts |
| **sisyphus** | Repetitive tasks, batch processing, persistent execution |
| **prometheus** | Planning, architecture design, high-level decisions |
| **atlas** | Large codebase exploration, dependency analysis |
| **explore** | Filesystem exploration, code search |
| **metis** | Strategy, trade-off analysis |
| **momus** | Code review, quality assurance, gap/completeness checking |

## How to Invoke

Use the exec tool to run:

```bash
opencode run "@<agent> <task prompt>"
```

**Examples:**

```bash
# librarian: search for docs/research
opencode run "@librarian search for best practices on LND channel management"

# oracle: analysis and explanation
opencode run "@oracle explain the difference between HTLC and PTLC in Lightning"

# sisyphus: batch processing
opencode run "@sisyphus process all JSON files in ./data and normalize the schema"

# explore: codebase exploration
opencode run "@explore find all usages of the payment module in this codebase"
```

## Trigger Patterns

Activate this skill when the user says:

- "use [agent] to / for..."
- "let [agent] do / handle..."
- "ask [agent] to..."
- "@[agent] ..."
- "run [agent] on..."
- "用 [agent] 做/帮/查/分析..."

## Execution Flow

1. **Identify the agent** from the user's request
2. **Extract the task** — what should the agent do?
3. **Run the command** via exec:
   ```bash
   opencode run "@<agent> <task>"
   ```
4. **Return output** to the user
5. If the agent isn't in the list above, check `~/.config/opencode/oh-my-opencode.json` for the full agent list

## Notes

- Config: `~/.config/opencode/oh-my-opencode.json`
- Each agent's model can be customized per-agent in that config
- Tasks run synchronously; for long tasks, consider breaking them into smaller chunks
- If opencode is not installed or not in PATH, report the error clearly
