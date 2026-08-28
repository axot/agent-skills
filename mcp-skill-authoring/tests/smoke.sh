#!/usr/bin/env bash
set -euo pipefail

SKILL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
SKILL_FILE="$SKILL_DIR/SKILL.md"
TEMPLATE_FILE="$SKILL_DIR/references/target-skill-template.md"
TEST_DIR="$(mktemp -d)"
cleanup_test_dir() {
  node -e 'require("node:fs").rmSync(process.argv[1], {recursive: true, force: true})' "$TEST_DIR"
}
trap cleanup_test_dir EXIT

ARGS_FILE="$TEST_DIR/arguments.json"
LIST_FILE="$TEST_DIR/tools.json"
SENTINEL_FILE="$TEST_DIR/runtime-json-was-executed"

node -e '
const fs = require("fs");
const file = process.argv[1];
const sentinel = process.argv[2];
const value = {
  apostrophe: "O\u0027Brien",
  newline: "first\nsecond",
  dollar: "$HOME",
  backticks: "`touch ignored`",
  substitution: `$(touch ${sentinel})`,
};
fs.writeFileSync(file, JSON.stringify(value));
' "$ARGS_FILE" "$SENTINEL_FILE"

ARGS_JSON="$(
  node -e '
const fs = require("fs");
const value = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
if (!value || Array.isArray(value) || typeof value !== "object") {
  process.exit(2);
}
process.stdout.write(JSON.stringify(value));
' "$ARGS_FILE"
)"

node -e '
const value = JSON.parse(process.argv[1]);
if (value.apostrophe !== "O\u0027Brien") process.exit(1);
if (value.newline !== "first\nsecond") process.exit(1);
if (value.dollar !== "$HOME") process.exit(1);
if (value.backticks !== "`touch ignored`") process.exit(1);
' "$ARGS_JSON"

if [ -e "$SENTINEL_FILE" ]; then
  echo "runtime JSON was executed as shell code" >&2
  exit 1
fi

node -e '
const fs = require("fs");
fs.writeFileSync(process.argv[1], JSON.stringify({
  result: {
    tools: [
      {name: "alpha", inputSchema: {}},
      {name: "beta", inputSchema: {type: "object"}},
      {name: "duplicate", inputSchema: {}},
      {name: "duplicate", inputSchema: {type: "object"}},
    ],
  },
}));
' "$LIST_FILE"

filter_tool() {
  node -e '
const fs = require("fs");
const file = process.argv[1];
const name = process.argv[2];
const document = JSON.parse(fs.readFileSync(file, "utf8"));
const matches = document.result?.tools?.filter((tool) => tool.name === name) ?? [];
if (matches.length !== 1) process.exit(5);
process.stdout.write(JSON.stringify(matches[0]));
' "$LIST_FILE" "$1"
}

EXACT_TOOL="$(filter_tool beta)"
node -e 'if (JSON.parse(process.argv[1]).name !== "beta") process.exit(1)' "$EXACT_TOOL"

set +e
filter_tool missing >/dev/null 2>&1
MISSING_STATUS=$?
filter_tool duplicate >/dev/null 2>&1
DUPLICATE_STATUS=$?
set -e

if [ "$MISSING_STATUS" -ne 5 ] || [ "$DUPLICATE_STATUS" -ne 5 ]; then
  echo "zero or duplicate tool matches did not fail with exit 5" >&2
  exit 1
fi

fake_inspector() {
  return "$1"
}

for EXPECTED_STATUS in 3 4; do
  set +e
  fake_inspector "$EXPECTED_STATUS" >"$TEST_DIR/inspector.json"
  INSPECTOR_STATUS=$?
  set -e
  if [ "$INSPECTOR_STATUS" -ne "$EXPECTED_STATUS" ]; then
    echo "Inspector exit $EXPECTED_STATUS was not preserved" >&2
    exit 1
  fi
done

SESSION_CONFIG="$TEST_DIR/inspector-session.json"
node -e '
const fs = require("fs");
fs.writeFileSync(process.argv[1], JSON.stringify({
  mcpServers: {
    target: {
      command: "/absolute/path/to/server",
      args: ["--config", "/path/to/server.conf", "--verbose"],
    },
  },
}));
' "$SESSION_CONFIG"

node -e '
const fs = require("fs");
const config = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const server = config.mcpServers?.target;
if (server?.command !== "/absolute/path/to/server") process.exit(1);
if (JSON.stringify(server.args) !== JSON.stringify(["--config", "/path/to/server.conf", "--verbose"])) process.exit(1);
' "$SESSION_CONFIG"

if grep -Eq '@modelcontextprotocol/inspector@[0-9]' "$SKILL_FILE" "$TEMPLATE_FILE"; then
  echo "Inspector must use latest instead of a numeric version" >&2
  exit 1
fi

if ! grep -Fq '@modelcontextprotocol/inspector@latest' "$SKILL_FILE"; then
  echo "authoring instructions do not require the Inspector latest tag" >&2
  exit 1
fi

LATEST_TEMPLATE_LINES="$(grep -Fc '@modelcontextprotocol/inspector@latest' "$TEMPLATE_FILE")"
if [ "$LATEST_TEMPLATE_LINES" -ne 2 ]; then
  echo "target template must use the Inspector latest tag in metadata and setup" >&2
  exit 1
fi

if ! grep -Fq 'Default to one compact `SKILL.md`' "$SKILL_FILE"; then
  echo "authoring instructions do not require the compact single-file default" >&2
  exit 1
fi

if grep -Fq 'Use a bundled script for filtering when' "$SKILL_FILE"; then
  echo "authoring instructions still promote a wrapper for repeated use" >&2
  exit 1
fi

if ! grep -Fq 'Repeated use is not a reason to create a' "$TEMPLATE_FILE"; then
  echo "target template does not preserve the no-wrapper default" >&2
  exit 1
fi

echo "smoke tests passed"
