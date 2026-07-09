#!/usr/bin/env bash
# Run the ETHOS governance-kernel gate through the command plane.
# This proves product and governed repositories share one kernel and command loop;
# profiles and adapters may vary proof depth, never command semantics.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

if [[ -n "${ETHOS_PYTHON:-}" ]]; then
  "${ETHOS_PYTHON}" -m ethos.cli quality governance-kernel --json
elif [[ -n "${PYTHON:-}" ]]; then
  "${PYTHON}" -m ethos.cli quality governance-kernel --json
elif [[ -x "${repo_root}/.venv/bin/python" ]]; then
  "${repo_root}/.venv/bin/python" -m ethos.cli quality governance-kernel --json
else
  uv run --package ethos python -m ethos.cli quality governance-kernel --json
fi
