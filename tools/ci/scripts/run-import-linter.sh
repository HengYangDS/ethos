#!/usr/bin/env bash
# Run import-linter against the ETHOS workspace package roots.
#
# CI starts from a fresh root project environment, while the import-linter
# contracts inspect workspace member packages. Keep that execution boundary
# explicit here instead of relying on an already-populated local virtualenv.
# --no-cache makes local runs recompute contracts from source exactly as CI's clean
# checkout does, so a layering violation cannot hide behind a stale mtime-keyed
# .import_linter_cache locally while CI (which has no cache) goes red.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export PYTHONPATH="${repo_root}/packages/ethos/src:${repo_root}/packages/ethos-core/src${PYTHONPATH:+:${PYTHONPATH}}"

uv run --group dev lint-imports --no-cache --config .config/checks/import-linter/contracts.ini
