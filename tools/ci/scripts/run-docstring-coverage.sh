#!/usr/bin/env bash
# Run the ETHOS public-surface docstring gate.
# The policy lives in .config/checks/docstrings/policy.toml; keep thresholds there.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

uv run --package ethos ethos quality docstrings --json
