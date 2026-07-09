#!/usr/bin/env bash
# Run Python lint, format, and Ruff ignored-rule ratchet as one proof gate.
#
# This is the owner script for the Python lint proof surface. CI and `ethos prove`
# call this script instead of duplicating the command set.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

ruff_config_path=".config/checks/ruff/ruff.toml"
ruff_cache_dir="${RUFF_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/ruff}"
mkdir -p "${ruff_cache_dir}"

uv run --group dev ruff check --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" .
uv run --group dev ruff format --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" --check .
tools/ci/scripts/run-ruff-ratchet.sh
