#!/usr/bin/env bash
# Run the ETHOS governance-kernel gate through the command plane.
# This proves product and governed repositories share one kernel and command loop;
# profiles and adapters may vary proof depth, never command semantics.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --all-packages --group dev python -m ethos.cli quality governance-kernel --json
