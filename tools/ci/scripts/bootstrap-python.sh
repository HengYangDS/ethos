#!/usr/bin/env bash
# Shared GitLab Python bootstrap. CI YAML is a provider projection; this script is
# the local SSOT for Python/uv/OpenSpec setup used by hosted jobs.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# Hosted owner scripts use `uv run --no-sync` after bootstrap. Materialize the
# same checkout-bound environment first so they cannot fall back to a default
# `.venv` or ambient interpreter.
export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"
bootstrap_venv="${repo_root}/build/runtime/bootstrap"
python -m venv "${bootstrap_venv}"
"${bootstrap_venv}/bin/pip" install --disable-pip-version-check --quiet uv
export PATH="${bootstrap_venv}/bin:${PATH}"

# The openspec shim execs `npx`, so Node.js must exist in the python:3.12 image the
# quality/verify jobs run in (only the ethos:npm jobs use a node image). Without this,
# `openspec --version` in ethos:verify fails with `npx: command not found`. Install
# Node from the Debian repos when npx is absent so the shim resolves.
if ! command -v npx >/dev/null 2>&1; then
  apt-get update >/dev/null && apt-get install -y --no-install-recommends nodejs npm jq >/dev/null
elif ! command -v jq >/dev/null 2>&1; then
  apt-get update >/dev/null && apt-get install -y --no-install-recommends jq >/dev/null
fi
printf '%s\n' '#!/usr/bin/env bash' 'exec npx --yes @fission-ai/openspec@1.6.0 "$@"' > /usr/local/bin/openspec
chmod +x /usr/local/bin/openspec
uv --version
uv sync --all-packages --group dev
