#!/usr/bin/env bash
# Run the ETHOS public-surface docstring gate.
# The policy lives in .config/checks/docstrings/policy.toml; keep thresholds there.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run ethos quality docstrings --json
