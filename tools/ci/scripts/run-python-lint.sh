#!/usr/bin/env bash
# Run Python lint, format, and Ruff ignored-rule ratchet as one proof gate.
#
# This is the owner script for the Python lint proof surface. CI and `ethos prove`
# call this script instead of duplicating the command set.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --group dev ruff check .
uv run --group dev ruff format --check .
tools/ci/scripts/run-ruff-ratchet.sh
