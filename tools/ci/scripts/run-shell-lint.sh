#!/usr/bin/env bash
# Run shell quality checks. ShellCheck policy lives in .config/checks/shell/.
# Structural layout comes from .config/checks/whitespace/policy.toml.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

if (($#)); then
  shell_files=("$@")
else
  shell_files=()
  while IFS= read -r target; do
    shell_files+=("${target}")
  done < <(git ls-files '*.sh')
fi
(( ${#shell_files[@]} )) || exit 0

if ! command -v shellcheck >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y --no-install-recommends shellcheck
  else
    echo "shellcheck is required for shell lint" >&2
    exit 127
  fi
fi

shellcheck --shell=bash --severity=style "${shell_files[@]}"
python tools/ci/structural_whitespace.py "${shell_files[@]}"
