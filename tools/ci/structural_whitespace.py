#!/usr/bin/env python3
"""Check active non-native text carriers for structural blank-line drift."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

POLICY_PATH = Path(".config/checks/whitespace/policy.toml")
HEREDOC_START = re.compile(r"<<-?\s*['\"]?([A-Za-z_][A-Za-z0-9_]*)")


@dataclass(frozen=True)
class WhitespacePolicy:
    """Immutable structural layout rules for shared text carriers."""

    max_consecutive_blank_lines: int
    forbid_leading_blank_lines: bool
    forbid_trailing_blank_lines: bool
    shared_extensions: frozenset[str]
    shell_extensions: frozenset[str]
    shell_filenames: frozenset[str]
    plain_filenames: frozenset[str]
    openspec_markdown_roots: tuple[Path, ...]
    excluded_roots: tuple[Path, ...]


def _strings(payload: dict[str, object], key: str) -> frozenset[str]:
    value = payload.get(key, [])
    return frozenset(str(item) for item in value) if isinstance(value, list) else frozenset()


def load_policy(root: Path) -> WhitespacePolicy:
    """Load the tracked shared-layout policy."""
    payload = tomllib.loads((root / POLICY_PATH).read_text(encoding="utf-8"))
    policy = payload["policy"]
    assets = payload["assets"]
    selection = payload["selection"]
    return WhitespacePolicy(
        max_consecutive_blank_lines=int(policy["max_consecutive_blank_lines"]),
        forbid_leading_blank_lines=bool(policy["forbid_leading_blank_lines"]),
        forbid_trailing_blank_lines=bool(policy["forbid_trailing_blank_lines"]),
        shared_extensions=_strings(assets, "shared_extensions"),
        shell_extensions=_strings(assets, "shell_extensions"),
        shell_filenames=_strings(assets, "shell_filenames"),
        plain_filenames=_strings(assets, "plain_filenames"),
        openspec_markdown_roots=tuple(
            Path(str(item)) for item in assets["openspec_markdown_roots"]
        ),
        excluded_roots=tuple(Path(str(item)) for item in selection["excluded_roots"]),
    )


def tracked_files(root: Path) -> tuple[Path, ...]:
    """Return the repository-owned carrier set."""
    completed = subprocess.run(["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True)
    return tuple(root / raw.decode("utf-8") for raw in completed.stdout.split(b"\0") if raw)


def is_excluded(path: Path, root: Path, policy: WhitespacePolicy) -> bool:
    """Return whether a tracked path belongs to immutable or generated history."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return True
    return any(relative.is_relative_to(excluded) for excluded in policy.excluded_roots)


def is_shell(path: Path, policy: WhitespacePolicy) -> bool:
    """Return whether a selected carrier is a Shell file."""
    return path.suffix in policy.shell_extensions or path.name in policy.shell_filenames


def is_governed(path: Path, policy: WhitespacePolicy, *, root: Path) -> bool:
    """Return whether one carrier lacks a native blank-line formatter."""
    if (
        is_shell(path, policy)
        or path.suffix in policy.shared_extensions
        or path.name in policy.plain_filenames
    ):
        return True
    try:
        relative = path.relative_to(root)
    except ValueError:
        return False
    return (
        path.suffix == ".md"
        and not relative.is_relative_to(Path("openspec/changes/archive"))
        and any(relative.is_relative_to(directory) for directory in policy.openspec_markdown_roots)
    )


def structural_lines(path: Path, policy: WhitespacePolicy) -> list[str]:
    """Mask embedded heredocs before evaluating the outer Shell layout."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not is_shell(path, policy):
        return lines
    masked: list[str] = []
    delimiter = ""
    for line in lines:
        if delimiter:
            if line == delimiter:
                delimiter = ""
                masked.append(line)
            else:
                masked.append("__ETHOS_HEREDOC__")
            continue
        match = HEREDOC_START.search(line)
        if match:
            delimiter = match.group(1)
        masked.append(line)
    return masked


def selected_paths(
    root: Path, requested: tuple[Path, ...], policy: WhitespacePolicy
) -> tuple[Path, ...]:
    """Resolve tracked default input or repository-relative explicit paths."""
    candidates = tuple(requested) or tracked_files(root)
    return tuple(
        path
        for path in (item if item.is_absolute() else root / item for item in candidates)
        if path.is_file()
        and not is_excluded(path, root, policy)
        and is_governed(path, policy, root=root)
    )


def violations(path: Path, policy: WhitespacePolicy) -> tuple[str, ...]:
    """Return deterministic line-addressed blank-line violations."""
    lines = structural_lines(path, policy)
    findings: list[str] = []
    if policy.forbid_leading_blank_lines and lines and not lines[0]:
        findings.append(f"{path}:1: leading blank line")
    if policy.forbid_trailing_blank_lines and lines and not lines[-1]:
        findings.append(f"{path}:{len(lines)}: trailing blank line")
    start = 0
    length = 0
    for index, line in enumerate([*lines, "__ETHOS_END__"], start=1):
        if not line:
            if not length:
                start = index
            length += 1
            continue
        if length > policy.max_consecutive_blank_lines:
            findings.append(
                f"{path}:{start}: {length} consecutive blank lines; maximum is "
                f"{policy.max_consecutive_blank_lines}"
            )
        length = 0
    return tuple(findings)


def main(argv: list[str] | None = None) -> int:
    """Run the shared structural-layout gate from the current repository root."""
    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout.strip()
    )
    policy = load_policy(root)
    requested = tuple(Path(value) for value in (argv if argv is not None else sys.argv[1:]))
    findings = [
        finding
        for path in selected_paths(root, requested, policy)
        for finding in violations(path, policy)
    ]
    if findings:
        sys.stderr.write("\n".join(findings) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
