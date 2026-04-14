# AWS Knowledge MCP Server (CLI Usage)

Use `fastmcp list` and `fastmcp call` to interact with the server directly. Run `list` first to discover available tools and their input schemas dynamically, then `call` to invoke them.

```bash
_MCP=https://knowledge-mcp.global.api.aws

# Discover tools and their input schemas
uvx fastmcp list "$_MCP" --input-schema --json

# Call a tool (construct target and arguments from the list output)
uvx fastmcp call "$_MCP" --target TOOL_NAME --input-json '{"key":"value"}' --json
```
