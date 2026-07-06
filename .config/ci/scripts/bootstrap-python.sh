#!/usr/bin/env bash
# Shared GitLab Python bootstrap. CI YAML is a provider projection; this script is
# the local SSOT for Python/uv/OpenSpec setup used by hosted jobs.
set -euo pipefail

python -m pip install --upgrade pip >/dev/null
pip install uv
# The openspec shim execs `npx`, so Node.js must exist in the python:3.12 image the
# quality/verify jobs run in (only the ethos:npm jobs use a node image). Without this,
# `openspec --version` in ethos:verify fails with `npx: command not found`. Install
# Node from the Debian repos when npx is absent so the shim resolves.
if ! command -v npx >/dev/null 2>&1; then
  apt-get update >/dev/null && apt-get install -y --no-install-recommends nodejs npm >/dev/null
fi
printf '%s\n' '#!/usr/bin/env bash' 'exec npx --yes @fission-ai/openspec "$@"' > /usr/local/bin/openspec
chmod +x /usr/local/bin/openspec
uv --version
