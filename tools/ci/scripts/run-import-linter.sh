#!/usr/bin/env bash
# Run import-linter against the ETHOS workspace package roots.
#
# CI starts from a fresh root project environment, while the import-linter
# contracts inspect workspace member packages. Keep that execution boundary
# explicit here instead of relying on an already-populated local virtualenv.
# Cache is admitted only under the semantic runtime tool-cache home. Root
# .import_linter_cache / .import-linter-cache would be generated-artifact drift.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cache_dir="${IMPORT_LINTER_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/import-linter}"
mkdir -p "${cache_dir}"
export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

uv run --group dev lint-imports --cache-dir "${cache_dir}" --config .config/checks/import-linter/contracts.ini
