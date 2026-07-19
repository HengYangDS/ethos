#!/usr/bin/env bash
# Audit local/generated state boundaries so ignored runtime artifacts do not become
# durable repository truth by accident.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos python tools/ci/local_state_audit.py
