#!/usr/bin/env bash
# Run report-first spelling checks over current human-facing governance docs.
# The gate is lint-only and never rewrites digest-bound evidence or archives.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

python - <<'PY'
from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

config = tomllib.loads(Path(".config/checks/prose/codespell.toml").read_text())
paths = [str(item) for item in config["paths"]]
skips = [str(item) for item in config["skip"]]
ignore_words = [str(item) for item in config["ignore_words"]]
cmd = [
    "uv",
    "run",
    "--group",
    "dev",
    "codespell",
    "--toml",
    ".config/checks/prose/codespell.toml",
    "--skip",
    ",".join(skips),
    "--ignore-words-list",
    ",".join(ignore_words),
    "--count",
    "--quiet-level=2",
    *paths,
]
raise SystemExit(subprocess.run(cmd, check=False).returncode)
PY
