#!/usr/bin/env bash
# Run import-linter against the ETHOS workspace package roots.
#
# CI starts from a fresh root project environment, while the import-linter
# contracts inspect workspace member packages. Keep that execution boundary
# explicit here instead of relying on an already-populated local virtualenv.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

uv run --group dev lint-imports --config .config/checks/import-linter/contracts.ini
