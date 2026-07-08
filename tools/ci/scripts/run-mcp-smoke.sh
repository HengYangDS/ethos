#!/usr/bin/env bash
# Run MCP projection smoke. This checks repo-local projection config only; it
# does not claim MCP server semantic correctness or repository proof.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/mcp_smoke.py
