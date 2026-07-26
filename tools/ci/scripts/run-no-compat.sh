#!/usr/bin/env bash
# Execute the no-compat gate through the singular proof surface.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${script_dir}/with-python-runtime.sh" -- uv run ethos prove --execute --gate no-compat --json
