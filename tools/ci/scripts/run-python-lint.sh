#!/usr/bin/env bash
# Run Python lint, format, and Ruff ignored-rule ratchet as one proof gate.
#
# This is the owner script for the Python lint proof surface. CI and `ethos prove`
# call this script instead of duplicating the command set.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

ruff_config_path=".config/checks/ruff/ruff.toml"
ruff_cache_dir="${RUFF_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/ruff}"
mkdir -p "${ruff_cache_dir}"

# The Python law is repository-wide: packages/tools/tests are required but not sufficient.
# Every tracked Python source file passes through the same Ruff config
# and formatter so agent skills, CI adapters, tests, and product packages cannot
# become side lanes.
python_quality_paths=()
while IFS= read -r python_quality_path; do
  if [[ -n "${python_quality_path}" ]]; then
    python_quality_paths+=("${python_quality_path}")
  fi
done < <(git ls-files "*.py" "*.pyi")
if [[ "${#python_quality_paths[@]}" -eq 0 ]]; then
  echo "no tracked Python files found for Ruff" >&2
  exit 1
fi

uv run --group dev ruff check --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" "${python_quality_paths[@]}"
uv run --group dev ruff format --cache-dir "${ruff_cache_dir}" --config "${ruff_config_path}" --check "${python_quality_paths[@]}"
tools/ci/scripts/run-ruff-ratchet.sh
