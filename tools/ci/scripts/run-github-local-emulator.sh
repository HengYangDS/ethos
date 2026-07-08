#!/usr/bin/env bash
# Emit GitHub local-provider emulator evidence through act. The evidence is local
# emulator evidence only and explicitly does not claim hosted GitHub status.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

mode="${1:-list}"
dry_run_flag=()
if [ "${ETHOS_LOCAL_EMULATOR_DRY_RUN:-0}" = "1" ]; then
  dry_run_flag=(--dry-run)
fi

uv run --package ethos python tools/ci/ci_templates.py emulator-evidence github --mode "${mode}" "${dry_run_flag[@]}"
