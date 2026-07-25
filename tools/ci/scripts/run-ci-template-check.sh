#!/usr/bin/env bash
# Check that hosted forge CI files remain projections over tracked templates.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run python tools/ci/ci_templates.py check-templates --json
