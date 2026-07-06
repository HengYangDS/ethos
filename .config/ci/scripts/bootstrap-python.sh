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
# GitLab checks out CI_COMMIT_SHA as a detached HEAD; tests/unit/product/test_orient.py
# reads ambient git state and needs an attached branch (detached -> orient reports an
# empty head -> test_orient_* red in ethos:verify). Re-attach to a branch at the SAME
# commit, CI-only (the CI_COMMIT_SHA guard keeps developer/local checkouts untouched, so
# bootstrap-as-local-SSOT never silently creates a branch). No content change:
# `git rev-parse HEAD` for prove --expect-head (.gitlab-ci.yml) is unchanged.
if [ -n "${CI_COMMIT_SHA:-}" ] && ! git symbolic-ref -q HEAD >/dev/null 2>&1; then
  git checkout -B "${CI_COMMIT_REF_NAME:-ci}" "${CI_COMMIT_SHA}"
fi
uv --version
