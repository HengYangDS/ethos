#!/usr/bin/env bash
# Run the Python security gate. Bandit policy (documented scoped skips) lives in
# .config/checks/bandit/bandit.yaml; the medium-severity threshold and the
# tracked-Python scope are owned here so hosted and local CI share one definition.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

mapfile -t python_security_paths < <(git ls-files "*.py")
if [[ "${#python_security_paths[@]}" -eq 0 ]]; then
  echo "no tracked Python files found for Bandit" >&2
  exit 1
fi

uv run --no-project --with bandit bandit \
  -c .config/checks/bandit/bandit.yaml \
  --severity-level medium \
  -q \
  "${python_security_paths[@]}"
