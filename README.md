# Agent Skills

A personal collection of reusable Agent Skills for coding, research, analysis,
decision support, and tool-assisted workflows. Each skill packages focused
instructions and optional scripts, references, assets, tests, or client metadata
behind a discoverable `SKILL.md` file.

The repository favors portable skills that can be used by Codex, Claude Code,
OpenCode, and other clients that support the Agent Skills format. Client-specific
integration is kept optional where practical.

## Skills

| Skill | Purpose |
| --- | --- |
| [`agent-steering`](agent-steering/) | Authors precise behavioral constraints that prevent recurring agent failure modes. |
| [`aws-expert`](aws-expert/) | Produces sourced AWS technical answers and Slack-ready output. |
| [`critical-thinking-discussion`](critical-thinking-discussion/) | Guides issue-led Socratic discussion while maintaining a live reasoning pyramid. |
| [`ddg-search`](ddg-search/) | Performs current web research through DuckDuckGo and synthesized search services. |
| [`deep-resolve`](deep-resolve/) | Applies exhaustive root-cause analysis to difficult, high-cost decisions. |
| [`fin-analyzer`](fin-analyzer/) | Analyzes financial transaction CSVs and generates interactive reports. |
| [`liquid-glass`](liquid-glass/) | Builds Apple-style refractive Liquid Glass interfaces in HTML, CSS, and SVG. |
| [`macos-calendar-plus`](macos-calendar-plus/) | Creates and manages macOS Calendar events through AppleScript. |
| [`mcp-skill-authoring`](mcp-skill-authoring/) | Creates portable, token-efficient MCP-backed skills using the official MCP Inspector CLI. |
| [`opencode-agents`](opencode-agents/) | Delegates work to specialized oh-my-openagent agents through OpenCode. |
| [`smart-shopper`](smart-shopper/) | Researches and compares products while caching results for fast re-filtering. |

Read each skill's frontmatter before use. Its description defines when the skill
should trigger, important exclusions, and any required dependencies.

## Installation

Install individual skills with the Skills CLI:

```bash
npx skills install axot/agent-skills --skill <skill-name>
```

For example:

```bash
npx skills install axot/agent-skills --skill mcp-skill-authoring
```

## Usage

Most compatible clients can select a skill automatically from its description.
Clients may also support explicit invocation using a skill name, such as
`$mcp-skill-authoring` or `/critical-thinking-discussion`; exact syntax varies by
client.

Supporting files are relative to the skill directory. When a `SKILL.md` directs
the agent to read a reference or run a script, preserve that directory structure
when installing the skill.

## Authoring Guidelines

Every skill must have a directory whose name matches the `name` field in its
`SKILL.md` frontmatter. The frontmatter must also include a specific
`description` that states positive triggers and material exclusions.

Keep workflows scoped and executable. Prefer deterministic scripts for parsing,
calculation, or repetitive protocol work. Keep credentials out of instructions,
examples, logs, and committed configuration. Verify mutable facts against
current primary documentation, and validate observable behavior before claiming
completion.

Use [`mcp-skill-authoring`](mcp-skill-authoring/) when creating a portable skill
that invokes an MCP server without permanently loading its complete tool catalog
into model context.

## Validation

Before committing a skill:

1. Parse the YAML frontmatter and confirm the directory name matches `name`.
2. Validate referenced files, scripts, and client metadata.
3. Run syntax checks and skill-specific tests.
4. Scan for credentials and generated output that should not be committed.
5. Run `git diff --check` and inspect the complete staged diff.

The MCP authoring skill includes an offline smoke test:

```bash
bash mcp-skill-authoring/tests/smoke.sh
```

Project-wide operating rules are defined in [`AGENTS.md`](AGENTS.md).
