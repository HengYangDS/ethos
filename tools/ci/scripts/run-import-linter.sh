#!/usr/bin/env bash
# Run import-linter against the sole ETHOS Python package.
# Cache is admitted only under the semantic runtime tool-cache home. Root
# .import_linter_cache / .import-linter-cache would be generated-artifact drift.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cache_dir="${IMPORT_LINTER_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/import-linter}"
mkdir -p "${cache_dir}"
export PYTHONPATH="${repo_root}/src${PYTHONPATH:+:${PYTHONPATH}}"

uv run --group dev lint-imports --cache-dir "${cache_dir}" --config .config/checks/import-linter/contracts.ini
