#!/usr/bin/env bash
# Write a closeout evidence manifest that hashes reviewed claim/chronicle/OpenSpec
# carriers. Generated logs remain generated evidence, not repository truth.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/closeout_manifest.py
