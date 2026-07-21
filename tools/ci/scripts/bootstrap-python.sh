#!/usr/bin/env bash
# Shared GitLab Python bootstrap. CI YAML is a provider projection; this script is
# the local SSOT for Python/uv/OpenSpec setup used by hosted jobs.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
# Hosted owner scripts use `uv run --no-sync` after bootstrap. Materialize the
# same checkout-bound environment first so they cannot fall back to a default
# `.venv` or ambient interpreter.
export UV_PROJECT_ENVIRONMENT="${repo_root}/build/runtime/venv"
bootstrap_venv="${repo_root}/build/runtime/tool-cache/uv-bootstrap"
bootstrap_python="${ETHOS_BOOTSTRAP_PYTHON:-python3}"
"${bootstrap_python}" -m venv "${bootstrap_venv}"
"${bootstrap_venv}/bin/pip" install --disable-pip-version-check --quiet 'uv==0.11.29'
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
openspec_shim="${bootstrap_venv}/bin/openspec"
printf '%s\n' '#!/usr/bin/env bash' 'exec npx --yes @fission-ai/openspec@1.6.0 "$@"' > "${openspec_shim}"
chmod +x "${openspec_shim}"
if [[ -n "${GITHUB_PATH:-}" ]]; then printf '%s\n' "${bootstrap_venv}/bin" >> "${GITHUB_PATH}"; fi
uv --version
uv sync --all-packages --group dev
