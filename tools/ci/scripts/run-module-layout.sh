#!/usr/bin/env bash
# Enforce semantic subpackage and module-layout policy.
#
# Policy lives in .config/checks/module-layout/policy.toml; this owner script is
# the reusable execution surface for local CI, hosted CI, pre-commit, and proof.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos ethos quality module-layout --json
