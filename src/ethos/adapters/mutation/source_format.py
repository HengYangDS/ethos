"""Admit and apply one complete native source-format patch against exact preimages."""

from __future__ import annotations

import difflib
import json
import stat
import subprocess
from typing import TYPE_CHECKING

from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.gates.formatting import FormattedFile
from ethos.adapters.gates.formatting import prepare_source_format
from ethos.adapters.gates.formatting import source_format_failure
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import run_git

if TYPE_CHECKING:
    from pathlib import Path


def _patch(prepared: tuple[FormattedFile, ...]) -> str:
    parts = []
    for item in prepared:
        if item.before == item.after:
            continue
        left, right = "a/" + item.path, "b/" + item.path
        before = item.before.decode("utf-8").splitlines(keepends=True)
        after = item.after.decode("utf-8").splitlines(keepends=True)
        patch = list(difflib.unified_diff(before, after, fromfile=left, tofile=right))
        patch[:2] = [
            f"--- {json.dumps(left, ensure_ascii=False)}\n",
            f"+++ {json.dumps(right, ensure_ascii=False)}\n",
        ]
        material = [
            line if line.endswith("\n") else line + "\n\\ No newline at end of file\n"
            for line in patch
        ]
        parts.append(
            "diff --git "
            f"{json.dumps(left, ensure_ascii=False)} {json.dumps(right, ensure_ascii=False)}\n"
            + "".join(material)
        )
    return "".join(parts)


def format_source(
    root: Path,
    *,
    paths: tuple[str, ...] = (),
    apply: bool = False,
    authorize: bool = False,
    expect_head: str = "",
    check: bool = False,
) -> dict[str, object]:
    """Preview, check or apply one selected native journey without changing the index."""
    try:
        result = _format_source(
            root,
            paths=paths,
            apply=apply,
            authorize=authorize,
            expect_head=expect_head,
            check=check,
        )
    except (OSError, ValueError, TypeError, subprocess.SubprocessError) as error:
        return source_format_failure(root, error)
    else:
        return result


def _format_source(
    root: Path,
    *,
    paths: tuple[str, ...],
    apply: bool,
    authorize: bool,
    expect_head: str,
    check: bool,
) -> dict[str, object]:
    head = current_tracked_head(root)
    index = run_git(root, "write-tree", check=True).stdout.strip()
    prepared = prepare_source_format(root, paths=paths)
    changed = tuple(item for item in prepared if item.before != item.after)
    report: dict[str, object] = {
        "verdict": "pass",
        "state": "ready",
        "head": head,
        "files": [item.path for item in prepared],
        "changed_paths": [item.path for item in changed],
        "file_count": len(prepared),
        "changed_count": len(changed),
        "ignored_paths": [item.path for item in prepared if item.ignored],
        "required_gaps": [],
    }
    if check:
        report.update(
            verdict="block" if changed else "pass",
            state="failed" if changed else "passed",
            required_gaps=[f"source_format_drift:{item.path}" for item in changed],
        )
        return report
    if not apply:
        return report
    if not authorize or expect_head != head:
        message = "authorization_required" if not authorize else "expect_head_mismatch"
        raise ValueError(message)
    patch = _patch(changed)
    admission = prewrite_guard(
        root=root,
        paths=[root / item.path for item in changed],
        editor_root=root,
        require_editor_root=True,
        patch=patch,
    )
    if admission["verdict"] != "pass":
        return {
            **report,
            "verdict": admission["verdict"],
            "state": "blocked",
            "required_gaps": admission["required_gaps"],
            "admission": admission,
        }
    if (
        current_tracked_head(root) != head
        or run_git(root, "write-tree", check=True).stdout.strip() != index
        or any(
            (root / item.path).is_symlink()
            or (root / item.path).read_bytes() != item.before
            or stat.S_IMODE((root / item.path).stat().st_mode) != item.mode
            for item in prepared
        )
    ):
        message = "source_format_preimage_changed"
        raise ValueError(message)
    if patch:
        result = run_git(root, "apply", "--whitespace=nowarn", "-", stdin=patch, check=False)
        if result.returncode:
            message = "source_format_apply_refused:" + result.stderr
            raise ValueError(message)
        for item in changed:
            (root / item.path).chmod(item.mode)
    if (
        any(
            (root / item.path).read_bytes() != item.after
            or stat.S_IMODE((root / item.path).stat().st_mode) != item.mode
            for item in prepared
        )
        or run_git(root, "write-tree", check=True).stdout.strip() != index
    ):
        message = "source_format_postimage_mismatch"
        raise ValueError(message)
    return {**report, "state": "formatted"}
