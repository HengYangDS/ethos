#!/usr/bin/env python3
"""Check active non-native text carriers for structural blank-line drift."""

# ruff: noqa: E501, E701, E702
from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from collections import namedtuple
from itertools import groupby
from pathlib import Path

# fmt: off
POLICY_PATH = Path(".config/checks/whitespace/policy.toml")
HEREDOC_START = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)")
WhitespacePolicy = namedtuple("WhitespacePolicy", "max_consecutive_blank_lines forbid_leading_blank_lines forbid_trailing_blank_lines shared_extensions shell_extensions shell_filenames plain_filenames openspec_markdown_roots excluded_roots")


def load_policy(root: Path) -> WhitespacePolicy:
    config = tomllib.loads((root / POLICY_PATH).read_text(encoding="utf-8")); policy, assets, selection = (config[key] for key in ("policy", "assets", "selection"))
    strings = lambda key: frozenset(map(str, assets.get(key, [])))  # noqa: E731
    return WhitespacePolicy(int(policy["max_consecutive_blank_lines"]), bool(policy["forbid_leading_blank_lines"]), bool(policy["forbid_trailing_blank_lines"]), *(strings(key) for key in ("shared_extensions", "shell_extensions", "shell_filenames", "plain_filenames")), tuple(map(Path, assets["openspec_markdown_roots"])), tuple(map(Path, selection["excluded_roots"])))


def is_governed(path: Path, policy: WhitespacePolicy, *, root: Path) -> bool:
    shell = path.suffix in policy.shell_extensions or path.name in policy.shell_filenames
    if shell or path.suffix in policy.shared_extensions or path.name in policy.plain_filenames: return True
    if not path.is_relative_to(root): return False
    relative = path.relative_to(root)
    return path.suffix == ".md" and not relative.is_relative_to(Path("openspec/changes/archive")) and any(relative.is_relative_to(item) for item in policy.openspec_markdown_roots)


def selected_paths(root: Path, requested: tuple[Path, ...], policy: WhitespacePolicy) -> tuple[Path, ...]:
    if not requested:
        output = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True).stdout
        requested = tuple(root / raw.decode() for raw in output.split(b"\0") if raw)
    resolved = (path if path.is_absolute() else root / path for path in requested)
    return tuple(path for path in resolved if path.is_file() and path.is_relative_to(root) and not any(path.relative_to(root).is_relative_to(item) for item in policy.excluded_roots) and is_governed(path, policy, root=root))


def violations(path: Path, policy: WhitespacePolicy) -> tuple[str, ...]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if path.suffix in policy.shell_extensions or path.name in policy.shell_filenames:
        masked, delimiter = [], ""
        for line in lines:
            if delimiter and line != delimiter: masked.append("__ETHOS_HEREDOC__"); continue
            if delimiter: delimiter = ""
            elif match := HEREDOC_START.search(line): delimiter = match.group(1)
            masked.append(line)
        lines = masked
    findings = []
    if policy.forbid_leading_blank_lines and lines and not lines[0]: findings.append(f"{path}:1: leading blank line")
    if policy.forbid_trailing_blank_lines and lines and not lines[-1]: findings.append(f"{path}:{len(lines)}: trailing blank line")
    for blank, run in groupby(enumerate(lines, 1), lambda item: not item[1]):
        items = tuple(run)
        if blank and len(items) > policy.max_consecutive_blank_lines: findings.append(f"{path}:{items[0][0]}: {len(items)} consecutive blank lines; maximum is {policy.max_consecutive_blank_lines}")
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    root = Path(subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, check=True, text=True).stdout.strip())
    policy = load_policy(root); paths = selected_paths(root, tuple(map(Path, argv if argv is not None else sys.argv[1:])), policy)
    findings = [finding for path in paths for finding in violations(path, policy)]
    if findings: sys.stderr.write("\n".join(findings) + "\n")
    return bool(findings)


if __name__ == "__main__": raise SystemExit(main())
# fmt: on
