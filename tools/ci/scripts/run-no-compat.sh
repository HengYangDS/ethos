#!/usr/bin/env bash
# Run the no-compatibility-residue product gate.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --group dev python -m ethos.cli quality no-compat --json
