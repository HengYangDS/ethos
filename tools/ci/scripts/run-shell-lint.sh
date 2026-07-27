#!/usr/bin/env bash
# Run shell quality checks. ShellCheck policy lives in .config/checks/shell/.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

shell_files=("$@")
if (($# == 0)); then
  while IFS= read -r target; do
    [[ -f "${target}" ]] && shell_files+=("${target}")
  done < <(git ls-files '*.sh' '.githooks/*')
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

shellcheck --rcfile=.config/checks/shell/.shellcheckrc "${shell_files[@]}"
