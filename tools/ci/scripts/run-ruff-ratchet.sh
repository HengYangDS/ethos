#!/usr/bin/env bash
# Enforce the Ruff ignored-rule ratchet.
#
# Ruff's main config blocks the current hard rule set. This script measures the
# explicitly frozen debt and fails when ignored-rule findings either exceed a
# baseline or fall below a stale baseline that has not been shrunk.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${ETHOS_RUNTIME_BOOTSTRAPPED:-}" != "1" && -x "${script_dir}/with-python-runtime.sh" ]]; then
  exec "${script_dir}/with-python-runtime.sh" -- \
    uv run --all-packages --group dev env ETHOS_RUNTIME_BOOTSTRAPPED=1 "$0" "$@"
fi

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
ruff_cache_dir="${RUFF_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/ruff}"
mkdir -p "${ruff_cache_dir}"
export RUFF_CACHE_DIR="${ruff_cache_dir}"

mapfile -t python_quality_paths < <(git ls-files "*.py" "*.pyi")
if [[ "${#python_quality_paths[@]}" -eq 0 ]]; then
  echo "no tracked Python files found for Ruff ratchet" >&2
  exit 1
fi

uv run --group dev python - "${python_quality_paths[@]}" <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

python_quality_paths = sys.argv[1:]
policy = tomllib.loads(Path(".config/checks/ruff/ratchet.toml").read_text(encoding="utf-8"))
baselines = {str(key): int(value) for key, value in policy["ignored_rule_baseline"].items()}
select = ",".join(sorted(baselines))
completed = subprocess.run(
    [
        "ruff",
        "check",
        "--config",
        ".config/checks/ruff/ruff.toml",
        *python_quality_paths,
        "--select",
        select,
        "--exit-zero",
        "--statistics",
    ],
    text=True,
    capture_output=True,
    check=False,
)
counts = {rule: 0 for rule in baselines}
pattern = re.compile(r"^\s*(\d+)\s+([A-Z]+\d+)\b", re.MULTILINE)
for match in pattern.finditer(completed.stdout):
    count = int(match.group(1))
    rule = match.group(2)
    if rule in counts:
        counts[rule] = count

failed = False
for rule in sorted(baselines):
    count = counts[rule]
    baseline = baselines[rule]
    print(f"{rule}: {count}/{baseline}")
    if count > baseline:
        print(f"ruff ratchet exceeded: {rule} {count}>{baseline}", file=sys.stderr)
        failed = True
    elif count < baseline:
        print(
            f"ruff ratchet baseline stale: {rule} {count}<{baseline}; "
            "shrink .config/checks/ruff/ratchet.toml to the current count",
            file=sys.stderr,
        )
        failed = True
if failed:
    print(completed.stdout, file=sys.stderr)
raise SystemExit(1 if failed else 0)
PY
