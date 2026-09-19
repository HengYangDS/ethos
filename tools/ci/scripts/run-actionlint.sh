#!/usr/bin/env bash
# Validate the selected workflow using locked mise supply, never an ambient fallback.
set -euo pipefail
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${repo_root}"
exec "${script_dir}/with-python-runtime.sh" -- uv run --frozen --offline python -c \
	'from tools.ci.ci_projection import check_workflow; raise SystemExit(check_workflow())'
