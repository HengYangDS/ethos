#!/usr/bin/env bash
# Run ETHOS from the current checkout through the semantic Python runtime.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --group dev ethos "$@"
