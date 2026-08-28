---
name: mcp-skill-authoring
description: >-
  Create or revise portable Agent Skills that call MCP servers lazily through
  the official Model Context Protocol Inspector CLI, avoiding the baseline
  context cost of registering every MCP tool. Use when authoring a Codex,
  Claude Code, OpenCode, or cross-client SKILL.md that needs MCP tools with low
  token usage, especially when native MCP tool search is unavailable or
  inconsistent across clients. Do not use for implementing MCP servers,
  ordinary native MCP registration, or one-off MCP calls that do not need a
  reusable skill.
---

# Token-Efficient MCP Skill Authoring

Create cross-client skills that invoke an MCP server only after the skill is
selected. Use the official `@modelcontextprotocol/inspector` CLI as the MCP
client. Keep MCP registration optional because clients differ in whether they
defer tool schemas.

## Required Design

The generated skill must:

1. Keep its trigger metadata concise so the always-visible skill catalog stays
   small.
2. Start the MCP server through MCP Inspector only when the skill is invoked.
3. Discover a live tool schema only when the required schema is unknown or may
   have changed.
4. Filter `tools/list` output to the one relevant tool before returning it to
   the model.
5. Invoke tools with `--tool-args-json` and consume machine-readable output with
   `--format json`.
6. Keep credentials in environment variables or the server's supported auth
   store. Never place secrets in `SKILL.md`, arguments, logs, or examples.
7. Require explicit user approval immediately before write, delete, publish,
   submit, permission-changing, or otherwise consequential calls.
8. Pass runtime or user-controlled JSON as data through a validated file or an
   argument array. Never splice it into shell source or a quoted command
   template.
9. Default to one compact `SKILL.md` containing direct Inspector commands. Do
   not create wrapper scripts or supporting files merely to avoid repeating a
   short command.

Do not duplicate the server's complete tool catalog or schemas in the skill.
Do not implement raw JSON-RPC, parse protocol traffic with `grep`, construct
commands with `eval`, or require FastMCP. These approaches add maintenance,
quoting, framing, and protocol-version failure modes that MCP Inspector already
handles.

## Authoring Workflow

### 1. Inspect the target

Determine:

- The local stdio command or remote HTTP URL.
- Required environment variables and authentication flow.
- The Node.js engine requirement of the current Inspector `latest` release,
  verified from the package registry and official documentation.
- Which calls are read-only, mutating, destructive, or externally visible.
- Expected startup and tool-call latency.

Prefer authoritative server documentation and a live `initialize` or
`tools/list` result over copied schemas.

### 2. Choose the invocation form

Choose exactly one target form: a fixed local stdio command and argument array,
or a fixed remote URL with its transport. Use the transport-specific structure
in `references/target-skill-template.md`; do not leave both branches active in
the generated skill.

For a stdio server with flag arguments, use a checked-in Inspector session
config with separate `command` and `args` fields. Do not rely on the bare `--`
separator for a durable skill: its observed CLI parsing can differ from the
documentation and between Inspector releases. Direct targets are acceptable
only for simple commands whose arguments cannot collide with Inspector options.

Query the package registry and official Inspector documentation during
authoring to verify the current CLI contract and Node.js engine requirement.
Invoke `@modelcontextprotocol/inspector@latest` in the generated skill rather
than freezing the package at the version observed during authoring.

### 3. Keep the generated skill compact

Keep the normal deliverable to one `SKILL.md`. Define the Inspector command and
one server target as shell arrays, then invoke Inspector directly from the
skill's command blocks. Expected call frequency is not a reason to create a
wrapper.

Add a separate file only when the target requires it. A stdio server whose
flags collide with Inspector options may require a session config. Genuinely
long server-specific guidance may require a reference. Add a script only when
the user requests one or when the required operation cannot be expressed
safely and clearly as a direct Inspector command. State the reason when adding
any supporting file.

When the tool schema is already verified and stable, call the tool directly.
When it is unknown or drift-prone, run `tools/list` and immediately select only
the required tool definition. Do not show the model the complete tool list.

Keep the canonical filter block from the target template directly in
`SKILL.md`. It should accept a tool name as data, parse Inspector JSON with a
JSON parser, print only the matching tool, and fail on both zero and duplicate
matches. Do not interpolate the tool name into executable shell text, and do
not duplicate the filter block within the same skill.

Do not pipe Inspector directly into the filter. Capture Inspector output, check
and preserve its exit status, and only then parse the successful JSON. A shell
pipeline can replace Inspector's authentication or connectivity exit code with
the parser's exit code.

### 4. Call the tool

Use one JSON object for arguments so strings, booleans, arrays, and nested
objects preserve their types. Use the canonical `tools/call` command from the
target template and replace every placeholder before delivery.

Treat a nonzero exit status as failure. MCP Inspector uses stable failure
classes, including exit code 3 for authentication, 4 for an unreachable server,
and 5 for either a missing tool or a tool execution error. Read the JSON error
envelope instead of scraping prose. Refresh discovery only when the tool is
missing or its schema is stale. For a tool execution error, inspect the returned
payload and verify remote state before any retry. Never blindly retry a
consequential call because it may have partially succeeded.

### 5. Control token use

- Do not run `tools/list` before every call.
- Do not paste a full tool catalog into `SKILL.md`.
- Filter discovery output before it enters model context.
- Ask servers for compact output when supported.
- Save binary or large artifacts to files instead of returning encoded content.
- Strip images or verbose metadata when the server supports it and the task does
  not need them.
- Keep examples to the minimum needed to demonstrate the invocation contract.

Native MCP registration may still be offered as an optional client-specific
path. Do not rely on it for portable token behavior because schema deferral is a
client feature, not an MCP protocol guarantee.

## Validation

Before delivering the generated skill:

1. Confirm its directory name matches the frontmatter `name`.
2. Confirm `name` and `description` are present and the description states both
   positive triggers and important exclusions.
3. Confirm the generated skill invokes `@modelcontextprotocol/inspector@latest`,
   states the current Node.js engine requirement, retains one transport branch,
   and contains no unresolved placeholders.
4. Run an Inspector `initialize` or `tools/list` probe against the configured
   server.
5. Verify exact tool discovery returns one schema, not the complete catalog.
6. Run one harmless read-only tool call when credentials and access permit.
7. Verify authentication and unreachable-server handling with a safe probe,
   fixture, or existing error. Do not invalidate real credentials or disrupt a
   working server merely to force an error.
8. Inspect executable scripts and command blocks for actual FastMCP invocation,
   raw JSON-RPC construction, or `eval` execution. Do not flag explanatory prose
   that names a prohibited pattern.
9. Validate the direct command blocks with apostrophes, newlines, dollar signs,
   backticks, and command-substitution text as data. Verify Inspector exit codes
   3 and 4 survive discovery and zero or duplicate tool matches fail. If the
   target requires a session config, also verify complex stdio arguments remain
   separate values.
10. Inspect the final files and report anything that could not be executed.

Run `bash tests/smoke.sh` to verify the reusable patterns in this skill before
changing its template. Do not add a test artifact to a generated target skill
unless that target includes separate executable logic that needs it.

## Template

Read `references/target-skill-template.md` when drafting the target skill. Adapt
the template to the server rather than copying placeholders or irrelevant
sections unchanged.

## Authoritative References

- MCP Inspector CLI: https://modelcontextprotocol.io/docs/tools/inspector/cli
- MCP Inspector overview: https://modelcontextprotocol.io/docs/tools/inspector
- MCP tools specification: https://modelcontextprotocol.io/specification/latest/server/tools
