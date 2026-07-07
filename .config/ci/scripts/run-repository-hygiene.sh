#!/usr/bin/env bash
# Run repository hygiene checks that are broader than one language tool.
#
# This owner script absorbs the useful pre-commit-hooks class of checks without
# making pre-commit or hosted CI the policy owner.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "${repo_root}"

python - <<'PY'
from __future__ import annotations

import json
import subprocess
from pathlib import Path

TEXT_SUFFIXES = {
    ".cfg",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".py",
    ".pyi",
    ".sh",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
TEXT_NAMES = {"AGENTS.md", "CHANGELOG.md", "CONTRIBUTING.md", "README.md"}
MAX_TRACKED_BYTES = 1024 * 1024
failures: list[str] = []
raw = subprocess.check_output(["git", "ls-files", "-z"])
paths = [Path(item.decode()) for item in raw.split(b"\0") if item]
for path in paths:
    if not path.exists() or not path.is_file():
        continue
    size = path.stat().st_size
    if size > MAX_TRACKED_BYTES and not path.as_posix().startswith("uv.lock"):
        failures.append(f"{path}: tracked file exceeds {MAX_TRACKED_BYTES} bytes")
    if path.suffix not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
        continue
    data = path.read_bytes()
    if not data:
        continue
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        continue
    if not data.endswith(b"\n"):
        failures.append(f"{path}: missing final newline")
    if b"\r\n" in data or b"\r" in data:
        failures.append(f"{path}: non-LF line ending")
    conflict_markers = ("<<<<<<< ", "=======", ">>>>>>> ")
    if any(line.startswith(conflict_markers) for line in text.splitlines()):
        failures.append(f"{path}: possible merge conflict marker")
    if path.suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as exc:
            failures.append(f"{path}: JSON parse failed: {exc}")

    human_guidance_surface = path.suffix in {".md", ".txt", ".rst"}
    if human_guidance_surface:
        forbidden_stash_patterns = (
            "git stash",
            "commit or stash",
            "stash, then retry",
            "stash-diff",
        )
        stash_policy_allowlist = (
            "do not use",
            "must not use",
            "reject",
            "forbidden",
            "not an accepted",
            "not admitted",
            "does not authorize",
            "not put into",
            "observation-only",
            "observe_only_stash_read",
            "git_stash_forbidden",
            "not_git_stash",
            "hidden change carrier",
        )
        lines = text.splitlines()
        for lineno, line in enumerate(lines, start=1):
            lowered_line = line.lower()
            window = "\n".join(lines[max(0, lineno - 2) : min(len(lines), lineno + 2)]).lower()
            if any(pattern in lowered_line for pattern in forbidden_stash_patterns) and not any(
                allowed in window for allowed in stash_policy_allowlist
            ):
                failures.append(
                    f"{path}:{lineno}: stash is not an accepted backup or closeout carrier"
                )

if failures:
    for failure in failures:
        print(failure)
    raise SystemExit(1)
PY
