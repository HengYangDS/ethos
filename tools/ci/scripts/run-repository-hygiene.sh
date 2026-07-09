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
import tomllib
from pathlib import Path
from typing import Any

POLICY_PATH = Path(".config/checks/repository-hygiene/policy.toml")
DEFAULT_POLICY: dict[str, Any] = {
    "max_tracked_bytes": 1024 * 1024,
    "large_file_allow_prefixes": ["uv.lock"],
    "text_suffixes": [
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
    ],
    "text_names": ["AGENTS.md", "CHANGELOG.md", "CONTRIBUTING.md", "README.md"],
    "root_host_residue": [".DS_Store", "Thumbs.db", "Desktop.ini"],
    "forbidden_stash_patterns": [
        "git stash",
        "commit or stash",
        "stash, then retry",
        "stash-diff",
    ],
    "stash_policy_allowlist": [
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
    ],
}


def load_policy() -> dict[str, Any]:
    """Load repository hygiene policy with deterministic defaults."""
    if not POLICY_PATH.exists():
        return DEFAULT_POLICY
    data = tomllib.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return DEFAULT_POLICY | data


def string_list(policy: dict[str, Any], key: str) -> list[str]:
    """Return a policy string-list value or an empty list for malformed input."""
    value = policy.get(key, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


policy = load_policy()
text_suffixes = set(string_list(policy, "text_suffixes"))
text_names = set(string_list(policy, "text_names"))
large_file_allow_prefixes = tuple(string_list(policy, "large_file_allow_prefixes"))
root_host_residue = string_list(policy, "root_host_residue")
forbidden_stash_patterns = tuple(
    pattern.lower() for pattern in string_list(policy, "forbidden_stash_patterns")
)
stash_policy_allowlist = tuple(
    pattern.lower() for pattern in string_list(policy, "stash_policy_allowlist")
)
max_tracked_bytes = int(policy.get("max_tracked_bytes", DEFAULT_POLICY["max_tracked_bytes"]))

failures: list[str] = []

for residue in root_host_residue:
    residue_path = Path(residue)
    if residue_path.is_absolute() or len(residue_path.parts) != 1:
        failures.append(
            f"{POLICY_PATH}: root_host_residue must contain root filenames only: {residue}"
        )
        continue
    if residue_path.exists():
        failures.append(f"{residue}: host-local root residue is not repository truth; remove it")

raw = subprocess.check_output(["git", "ls-files", "-z"])
paths = [Path(item.decode()) for item in raw.split(b"\0") if item]
for path in paths:
    if not path.exists() or not path.is_file():
        continue
    size = path.stat().st_size
    if size > max_tracked_bytes and not path.as_posix().startswith(
        large_file_allow_prefixes
    ):
        failures.append(f"{path}: tracked file exceeds {max_tracked_bytes} bytes")
    if path.suffix not in text_suffixes and path.name not in text_names:
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
        lines = text.splitlines()
        for lineno, line in enumerate(lines, start=1):
            lowered_line = line.lower()
            window = "\n".join(
                lines[max(0, lineno - 2) : min(len(lines), lineno + 2)]
            ).lower()
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
