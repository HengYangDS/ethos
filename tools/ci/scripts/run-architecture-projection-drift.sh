#!/usr/bin/env bash
# Check architecture projection drift. LikeC4/C4 source and Mermaid output are
# projections; docs/system/OpenSpec remain authoritative.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos python tools/ci/architecture_projection.py
