#!/usr/bin/env bash
# Run shell quality checks. ShellCheck policy lives in .config/checks/shell/.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

if (($#)); then
  shell_files=("$@")
else
  mapfile -t shell_files < <(git ls-files '*.sh')
fi
if ((${#shell_files[@]} == 0)); then
  exit 0
fi

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
