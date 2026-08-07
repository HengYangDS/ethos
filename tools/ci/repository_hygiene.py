"""Cross-platform repository hygiene owner."""

from __future__ import annotations

import json
import re
import subprocess
import tokenize
import tomllib
from io import StringIO
from pathlib import Path
from typing import Any

POLICY_RELATIVE_PATH = Path(".config/checks/repository-hygiene/policy.toml")
DEFAULT_POLICY: dict[str, Any] = {
    "max_tracked_bytes": 1024 * 1024,
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
}
PYTHON_SUPPRESSIONS = (
    (re.compile(r"(?i)\bnoqa\b"), "noqa"),
    (re.compile(r"(?i)\b(?:type|pyright|mypy)\s*:\s*ignore\b"), "type-ignore"),
    (re.compile(r"(?i)\bpragma\s*:\s*no\s*cover\b"), "coverage-ignore"),
    (re.compile(r"(?i)\bfmt\s*:\s*off\b"), "format-off"),
    (re.compile(r"(?i)\bfmt\s*:\s*on\b"), "format-on"),
    (re.compile(r"(?i)\bnosec\b"), "security-ignore"),
)
SHELL_SUPPRESSIONS = (
    (re.compile(r"(?i)^\s*#\s*shellcheck\s+disable\b"), "shellcheck-disable"),
    (re.compile(r"(?i)^\s*#\s*shfmt\s*:\s*(?:off|on|ignore)\b"), "format-ignore"),
)
CONFLICT_MARKERS = ("<<<<<<< ", "=======", ">>>>>>> ")


def _string_list(policy: dict[str, Any], key: str) -> list[str]:
    value = policy.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        msg = f"{POLICY_RELATIVE_PATH}: {key} must be a string list"
        raise ValueError(msg)
    return value


def _load_policy(root: Path) -> tuple[int, frozenset[str], frozenset[str], tuple[str, ...]]:
    path = root / POLICY_RELATIVE_PATH
    policy = DEFAULT_POLICY | (
        tomllib.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    )
    maximum = policy.get("max_tracked_bytes")
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum <= 0:
        msg = f"{POLICY_RELATIVE_PATH}: max_tracked_bytes must be a positive integer"
        raise ValueError(msg)
    return (
        maximum,
        frozenset(_string_list(policy, "text_suffixes")),
        frozenset(_string_list(policy, "text_names")),
        tuple(_string_list(policy, "root_host_residue")),
    )


def _tracked_paths(root: Path) -> tuple[Path, ...]:
    raw = subprocess.check_output(("git", "ls-files", "-z"), cwd=root)
    return tuple(root / item.decode() for item in raw.split(b"\0") if item)


def _suppression_failures(relative: str, suffix: str, text: str) -> list[str]:
    if suffix in {".py", ".pyi"}:
        comments = (
            token
            for token in tokenize.generate_tokens(StringIO(text).readline)
            if token.type == tokenize.COMMENT
        )
        return [
            f"{relative}:{comment.start[0]}: forbidden quality suppression: {label}"
            for comment in comments
            for pattern, label in PYTHON_SUPPRESSIONS
            if pattern.search(comment.string)
        ]
    if suffix == ".sh":
        return [
            f"{relative}:{line_number}: forbidden quality suppression: {label}"
            for line_number, line in enumerate(text.splitlines(), start=1)
            for pattern, label in SHELL_SUPPRESSIONS
            if pattern.search(line)
        ]
    return []


def _text_failures(relative: str, suffix: str, data: bytes, text: str) -> list[str]:
    failures: list[str] = []
    if not data.endswith(b"\n"):
        failures.append(f"{relative}: missing final newline")
    if b"\r" in data:
        failures.append(f"{relative}: non-LF line ending")
    if any(line.startswith(CONFLICT_MARKERS) for line in text.splitlines()):
        failures.append(f"{relative}: possible merge conflict marker")
    if suffix == ".json":
        try:
            json.loads(text)
        except json.JSONDecodeError as error:
            failures.append(f"{relative}: JSON parse failed: {error}")
    return [*failures, *_suppression_failures(relative, suffix, text)]


def audit(root: Path) -> tuple[str, ...]:
    """Return deterministic repository hygiene failures."""
    root = root.resolve()
    maximum, text_suffixes, text_names, root_residue = _load_policy(root)
    failures: list[str] = []
    for name in root_residue:
        path = Path(name)
        if path.is_absolute() or len(path.parts) != 1:
            failures.append(
                f"{POLICY_RELATIVE_PATH}: root_host_residue must contain root filenames only: "
                f"{name}"
            )
        elif (root / path).exists():
            failures.append(f"{name}: host-local root residue is not repository truth; remove it")
    for path in _tracked_paths(root):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.stat().st_size > maximum:
            failures.append(f"{relative}: tracked file exceeds {maximum} bytes")
        if path.suffix not in text_suffixes and path.name not in text_names:
            continue
        data = path.read_bytes()
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if data:
            failures.extend(_text_failures(relative, path.suffix, data, text))
    return tuple(failures)
