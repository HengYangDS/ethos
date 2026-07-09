#!/usr/bin/env bash
# Run product-boundary and contributor-policy gates through the ETHOS command plane.
# This keeps active product surfaces and release metadata neutral, while
# historical evidence remains classified as historical instead of product default.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

run_ethos_quality() {
  local check="$1"
  if [[ -n "${ETHOS_PYTHON:-}" ]]; then
    "${ETHOS_PYTHON}" -m ethos.cli quality "${check}" --json
  elif [[ -n "${PYTHON:-}" ]]; then
    "${PYTHON}" -m ethos.cli quality "${check}" --json
  elif [[ -x "${repo_root}/.venv/bin/python" ]]; then
    "${repo_root}/.venv/bin/python" -m ethos.cli quality "${check}" --json
  else
    uv run --package ethos python -m ethos.cli quality "${check}" --json
  fi
}

run_ethos_quality product-boundary
run_ethos_quality contributor-policy
run_ethos_quality governance-kernel
