#!/usr/bin/env bash
# Run the ETHOS governance-kernel gate through the command plane.
# This proves product and governed repositories share one kernel and command loop;
# profiles and adapters may vary proof depth, never command semantics.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

ethos_python="${ETHOS_PYTHON:-${PYTHON:-${UV_PROJECT_ENVIRONMENT}/bin/python}}"
"${ethos_python}" -m ethos.cli quality governance-kernel --json
