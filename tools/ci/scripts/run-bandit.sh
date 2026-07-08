#!/usr/bin/env bash
# Run the Python security gate. Bandit policy (documented scoped skips) lives in
# .config/checks/bandit/bandit.yaml; the medium-severity threshold and the
# scanned scope are owned here so hosted and local CI share one definition.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

uv run --no-project --with bandit bandit \
  -r packages \
  -c .config/checks/bandit/bandit.yaml \
  --severity-level medium \
  -q
