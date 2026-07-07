from __future__ import annotations

import hashlib
import subprocess
import sys
from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.shadow.execution import ROOT_OPTION_COMMANDS
from ethos.adapters.shadow.execution import embedded_backend
from ethos.repository.profile import profile_evidence_roots

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path


def identity_envelope(
    target: Path,
    commands: Iterable[tuple[str, ...]],
    *,
    product_root: Path,
    comparisons: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    target = target.resolve()
    product_root = product_root.resolve()
    return {
        "target_root": target.as_posix(),
        "target_head": git_head(target),
        "product_head": git_head(product_root),
        "changed_paths": changed_paths(target),
        "commands": [command_label_from_tuple(command) for command in commands],
        "external_commands": [external_command_label(target, command) for command in commands],
        "embedded_commands": embedded_command_labels(target, commands, comparisons),
        "evidence_inputs": evidence_inputs(target),
    }


def command_label_from_tuple(command: tuple[str, ...]) -> str:
    return "ethos " + " ".join(command) + " --json"


def external_command_label(target: Path, command: tuple[str, ...]) -> str:
    if command not in ROOT_OPTION_COMMANDS:
        return " ".join([sys.executable, "-m", "ethos.cli", *command, "--json"])
    return " ".join(
        [
            sys.executable,
            "-m",
            "ethos.cli",
            *command,
            "--root",
            target.resolve().as_posix(),
            "--json",
        ]
    )


def embedded_command_labels(
    target: Path,
    commands: Iterable[tuple[str, ...]],
    comparisons: list[dict[str, Any]] | None,
) -> list[str]:
    labels: list[str] = []
    if comparisons is not None:
        for comparison in comparisons:
            embedded = comparison.get("embedded") if isinstance(comparison, dict) else None
            backend = embedded.get("backend") if isinstance(embedded, dict) else None
            command = backend.get("command") if isinstance(backend, dict) else None
            if isinstance(command, str) and command:
                labels.append(command)
        if labels:
            return labels
    for command in commands:
        backend = embedded_backend(target, command)
        label = backend.get("command")
        if isinstance(label, str) and label:
            labels.append(label)
    return labels


def git_head(root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return ""
    return completed.stdout.strip() if completed.returncode == 0 else ""


def changed_paths(root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "-uall"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
            timeout=5,
        )
    except (subprocess.SubprocessError, OSError):
        return []
    paths: list[str] = []
    for line in completed.stdout.splitlines():
        if not line:
            continue
        raw = line[3:] if len(line) > 3 else line
        if " -> " in raw:
            raw = raw.split(" -> ", 1)[1]
        if raw:
            paths.append(raw.strip())
    return sorted(dict.fromkeys(paths))


def evidence_inputs(target: Path) -> list[dict[str, Any]]:
    candidates = evidence_root_candidates(target)
    return [item for item in (evidence_input(target, path) for path in candidates) if item]


def evidence_root_candidates(target: Path) -> list[str]:
    return sorted(profile_evidence_roots(target))


def evidence_input(target: Path, relative: str) -> dict[str, Any] | None:
    path = target / relative
    if not path.exists():
        return None
    if path.is_file():
        digest = file_sha256(path)
        kind = "file"
    elif path.is_dir():
        digest = tree_sha256(path)
        kind = "directory"
    else:
        return None
    return {"path": relative, "kind": kind, "sha256": digest}


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in sorted(p for p in path.rglob("*") if p.is_file()):
        if ".git" in file_path.parts:
            continue
        rel = file_path.relative_to(path).as_posix()
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(file_path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
