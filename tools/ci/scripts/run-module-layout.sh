#!/usr/bin/env bash
# Enforce semantic subpackage and module-layout policy.
#
# Policy lives in .config/checks/module-layout/policy.toml; this owner script is
# the reusable execution surface for local CI, hosted CI, pre-commit, and proof.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --package ethos ethos quality module-layout --json
