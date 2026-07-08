#!/usr/bin/env bash
# Check runbook registry entries against configured commands and evidence labels.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/runbook_registry.py
