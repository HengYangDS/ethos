#!/usr/bin/env bash
# Run the report-first file format boundary audit.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/format_selection.py
