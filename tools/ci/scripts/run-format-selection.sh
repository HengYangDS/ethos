#!/usr/bin/env bash
# Run the report-first file format boundary audit.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos python tools/ci/format_selection.py
