#!/usr/bin/env bash
# Run MCP projection smoke. This checks repo-local projection config only; it
# does not claim MCP server semantic correctness or repository proof.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/mcp_smoke.py
