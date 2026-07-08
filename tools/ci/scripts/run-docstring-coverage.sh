#!/usr/bin/env bash
# Run the ETHOS public-surface docstring gate.
# The policy lives in .config/checks/docstrings/policy.toml; keep thresholds there.
set -euo pipefail

uv run --package ethos ethos quality docstrings --json
