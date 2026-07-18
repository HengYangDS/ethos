#!/usr/bin/env bash
# Run product-boundary and contributor-policy gates through the ETHOS command plane.
# This keeps active product surfaces and release metadata neutral, while
# historical evidence remains classified as historical instead of product default.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --package ethos env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

run_ethos_quality() {
  local check="$1"
  uv run --package ethos python -m ethos.cli quality "${check}" --json
}

run_ethos_quality product-boundary
run_ethos_quality contributor-policy
run_ethos_quality governance-kernel
