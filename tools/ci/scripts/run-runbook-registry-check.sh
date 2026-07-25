#!/usr/bin/env bash
# Check runbook registry entries against configured commands and evidence labels.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run python tools/ci/runbook_registry.py
