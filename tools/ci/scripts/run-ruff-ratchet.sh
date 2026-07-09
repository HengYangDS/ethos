#!/usr/bin/env bash
# Enforce the Ruff ignored-rule ratchet.
#
# Ruff's main config blocks the current hard rule set. This script measures the
# explicitly frozen debt and fails when any ignored rule grows past its baseline.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"
ruff_cache_dir="${RUFF_CACHE_DIR:-${repo_root}/build/runtime/tool-cache/ruff}"
mkdir -p "${ruff_cache_dir}"
export RUFF_CACHE_DIR="${ruff_cache_dir}"

uv run --group dev python - <<'PY'
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

policy = tomllib.loads(Path(".config/checks/ruff/ratchet.toml").read_text(encoding="utf-8"))
baselines = {str(key): int(value) for key, value in policy["ignored_rule_baseline"].items()}
select = ",".join(sorted(baselines))
completed = subprocess.run(
    [
        "ruff",
        "check",
        "--config",
        ".config/checks/ruff/ruff.toml",
        ".",
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
if failed:
    print(completed.stdout, file=sys.stderr)
raise SystemExit(1 if failed else 0)
PY
