#!/usr/bin/env bash
# Enforce semantic subpackage and module-layout policy.
#
# Policy lives in .config/checks/module-layout/policy.toml; this owner script is
# the reusable execution surface for local CI, hosted CI, pre-commit, and proof.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos ethos quality module-layout --json
