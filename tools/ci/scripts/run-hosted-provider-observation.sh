#!/usr/bin/env bash
# Capture hosted provider observation envelopes for GitHub and GitLab.
# Default mode is dry-run/tool-discovery only; set ETHOS_HOSTED_OBSERVATION_EXECUTE=1
# to query provider CLIs. Either mode is observation evidence, never repository proof.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

args=()
if [ "${ETHOS_HOSTED_OBSERVATION_EXECUTE:-0}" = "1" ]; then
  args+=(--execute)
fi

if [ "${#args[@]}" -eq 0 ]; then
  uv run python tools/ci/hosted_observation.py
else
  uv run python tools/ci/hosted_observation.py "${args[@]}"
fi
