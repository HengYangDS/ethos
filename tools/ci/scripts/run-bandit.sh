#!/usr/bin/env bash
# Run the Python security gate. Bandit policy (documented scoped skips) lives in
# .config/checks/bandit/bandit.yaml; the medium-severity threshold and the
# tracked-Python scope are owned here so hosted and local CI share one definition.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

# Bandit 1.9.4 still constructs stevedore entry-point managers with the legacy
# ``verify_requirements`` argument. Current stevedore emits a third-party
# deprecation warning for that call, which is promoted to an error by the
# repository-wide warning policy before Bandit can inspect product code. Scope
# the compatibility filter to Bandit's process; all repository warnings remain
# errors in tests and the other quality gates.
bandit_warning_filters="${PYTHONWARNINGS:+${PYTHONWARNINGS},}ignore:The verify_requirements argument is now a no-op and is deprecated for removal.:DeprecationWarning:stevedore.extension,ignore:FileType is deprecated. Simply open files after parsing arguments.:PendingDeprecationWarning"

python_security_paths=()
while IFS= read -r -d "" path; do python_security_paths+=("${path}"); done < <(git ls-files -z "*.py")
if [[ "${#python_security_paths[@]}" -eq 0 ]]; then
  echo "no tracked Python files found for Bandit" >&2
  exit 1
fi

PYTHONWARNINGS="${bandit_warning_filters}" uv run --no-project --with bandit bandit \
  -c .config/checks/bandit/bandit.yaml \
  --severity-level medium \
  -q \
  "${python_security_paths[@]}"
