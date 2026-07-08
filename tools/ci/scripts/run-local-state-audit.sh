#!/usr/bin/env bash
# Audit local/generated state boundaries so ignored runtime artifacts do not become
# durable repository truth by accident.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/local_state_audit.py
