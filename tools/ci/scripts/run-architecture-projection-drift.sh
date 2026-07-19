#!/usr/bin/env bash
# Check architecture projection drift. LikeC4/C4 source and Mermaid output are
# projections; docs/system/OpenSpec remain authoritative.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec "${script_dir}/with-python-runtime.sh" -- uv run --package ethos python tools/ci/architecture_projection.py
