#!/usr/bin/env bash
# Run ETHOS from the current Work Lane with semantic uv runtime homes.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

export UV_PROJECT_ENVIRONMENT="${UV_PROJECT_ENVIRONMENT:-${repo_root}/build/runtime/venv}"
export UV_CACHE_DIR="${UV_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/uv}"
mkdir -p "${UV_PROJECT_ENVIRONMENT}" "${UV_CACHE_DIR}"

exec uv run --package ethos ethos "$@"
