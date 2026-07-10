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
python_quality_roots=("packages" "tools" "tests")
mkdir -p "${ruff_cache_dir}"

# The Python law is repository-wide: product packages, repository tools, and tests
# all pass through the same Ruff config and formatter. No Python root is a side lane.
uv run --group dev ruff check --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" "${python_quality_roots[@]}"
uv run --group dev ruff format --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" --check "${python_quality_roots[@]}"
tools/ci/scripts/run-ruff-ratchet.sh
