#!/usr/bin/env bash
# Run the no-compatibility-residue product gate.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --all-packages --group dev python -m ethos.cli quality no-compat --json
