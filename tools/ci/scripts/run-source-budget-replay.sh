#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel)"
exec "$ROOT/tools/ci/scripts/with-python-runtime.sh" -- \
  uv run --locked --all-packages --group dev python "$ROOT/tools/ci/source_budget_replay.py" \
  --root "$ROOT" "$@"
