from __future__ import annotations

import shlex
import shutil
import tempfile
import tomllib
from pathlib import Path

from ethos.adapters.repo.git import git_stdout
from ethos.adapters.repo.git import run_git
from ethos.normalization.coercion import repository_path_matches
from ethos.repository.policy.references.closure import product_reference_gaps
from ethos.repository.policy.references.declarations import native_owned_references_from_files
from ethos.repository.policy.references.observation import product_references_from_files

_UNIFIED_DIFF_HEADER_PART_COUNT = 4
_REFERENCE_KINDS = ("import", "distribution", "executable", "reference", "command", "value")
_OWNER_SUFFIXES = (".json", ".py", ".toml")


def patch_admission(
    *,
    root: Path,
    requested_paths: tuple[str, ...],
    baseline_head: str,
    patch: str,
) -> dict[str, object]:
    """Validate a patch against its baseline scope and product closure."""
    if not patch:
        return {
            "verdict": "pass",
            "state": "not_requested",
            "reason": "not_requested",
            "baseline_head": baseline_head,
            "paths": [],
            "references": {},
        }
    changes, parse_gap = _unified_patch_changes(patch)
    patch_paths = sorted({str(change["path"]) for change in changes})
    requested = sorted(set(requested_paths))
    reason = parse_gap
    if not reason and patch_paths != requested:
        reason = "prewrite_patch_paths_mismatch"
    if not reason and not baseline_head:
        reason = "prewrite_patch_baseline_missing"
    if not reason and not _patch_applies(root, patch, check_preimage=True):
        reason = "prewrite_patch_preimage_mismatch"
    scope = _baseline_scope_patterns(root, baseline_head) if not reason else ()
    if not reason:
        reason = next(
            (
                f"product_path_not_admitted_at_baseline:{change['path']}"
                for change in changes
                if change["new"] is True
                and not any(
                    repository_path_matches(str(change["path"]), pattern) for pattern in scope
                )
            ),
            "",
        )
    references: dict[str, set[str]] = {}
    if not reason:
        baseline_references = _baseline_product_references(root, baseline_head)
        try:
            references = _patch_references(
                root,
                patch,
                changes,
                declared_commands=baseline_references["command"],
            )
        except (OSError, UnicodeError, ValueError):
            reason = "prewrite_patch_postimage_failed"
    if not reason:
        gaps = product_reference_gaps(baseline_references, references)
        reason = gaps[0] if gaps else ""
    return {
        "verdict": "block" if reason else "pass",
        "state": "admitted" if not reason else "blocked",
        "reason": reason or "baseline_product_closure_matched",
        "baseline_head": baseline_head,
        "paths": patch_paths,
        "references": {key: sorted(value) for key, value in references.items() if value},
    }


def _patch_applies(root: Path, patch: str, *, check_preimage: bool = False) -> bool:
    command = ["apply", "--whitespace=error-all", "-"]
    if check_preimage:
        command.insert(2, "--check")
    return run_git(root, *command, stdin=patch, text=True, check=False).returncode == 0


def _baseline_product_references(root: Path, head: str) -> dict[str, frozenset[str]]:
    paths = git_stdout(root, "ls-tree", "-r", "--name-only", head).splitlines()
    files = {
        path: git_stdout(root, "show", f"{head}:{path}")
        for path in paths
        if path.endswith(_OWNER_SUFFIXES)
    }
    return native_owned_references_from_files(files)


def _unified_patch_changes(patch: str) -> tuple[list[dict[str, object]], str]:
    changes: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for line in patch.splitlines():
        if line.startswith(("GIT binary patch", "Binary files ")):
            return changes, "prewrite_patch_binary_unsupported"
        if line.startswith("diff --git "):
            current = _new_patch_change(line)
            if current is None:
                return changes, "prewrite_patch_invalid"
            changes.append(current)
        elif current is not None:
            _update_patch_change(current, line)
    if not changes or any(not change["path"] for change in changes):
        return changes, "prewrite_patch_invalid"
    return changes, ""


def _new_patch_change(line: str) -> dict[str, object] | None:
    try:
        parts = shlex.split(line)
    except ValueError:
        return None
    if len(parts) != _UNIFIED_DIFF_HEADER_PART_COUNT:
        return None
    return {
        "old_path": _patch_path(parts[2]),
        "path": _patch_path(parts[3]),
        "new": False,
    }


def _update_patch_change(change: dict[str, object], line: str) -> None:
    if line.startswith("--- "):
        change["old_path"] = _patch_path(line[4:].split("\t", 1)[0])
        change["new"] = change["old_path"] == "/dev/null"
    elif line.startswith("+++ "):
        path = _patch_path(line[4:].split("\t", 1)[0])
        if path != "/dev/null":
            change["path"] = path


def _patch_path(raw: str) -> str:
    if raw == "/dev/null":
        return raw
    return raw.removeprefix("a/").removeprefix("b/")


def _baseline_scope_patterns(root: Path, head: str) -> tuple[str, ...]:
    paths = git_stdout(
        root,
        "ls-tree",
        "-r",
        "--name-only",
        head,
        "--",
        "openspec/changes",
    ).splitlines()
    patterns: list[str] = []
    for path in paths:
        if not path.endswith("/commitment.toml") or "/archive/" in path:
            continue
        text = git_stdout(root, "show", f"{head}:{path}")
        try:
            scope = tomllib.loads(text).get("scope", [])
        except tomllib.TOMLDecodeError:
            continue
        if not isinstance(scope, list):
            continue
        patterns.extend(item for item in scope if isinstance(item, str) and item)
    return tuple(dict.fromkeys(patterns))


def _patch_references(
    root: Path,
    patch: str,
    changes: list[dict[str, object]],
    *,
    declared_commands: tuple[str, ...] | frozenset[str] = (),
) -> dict[str, set[str]]:
    with tempfile.TemporaryDirectory(prefix="ethos-prewrite-postimage-") as temporary:
        workspace = Path(temporary)
        for change in changes:
            old_path = str(change["old_path"])
            if old_path == "/dev/null":
                continue
            relative = Path(old_path)
            if relative.is_absolute() or ".." in relative.parts:
                msg = "prewrite patch path escapes root"
                raise ValueError(msg)
            source = root / relative
            if not source.is_file():
                msg = "prewrite patch preimage missing"
                raise ValueError(msg)
            target = workspace / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        if not _patch_applies(workspace, patch):
            msg = "prewrite patch postimage application failed"
            raise ValueError(msg)
        files: dict[str, str] = {}
        for change in changes:
            path = str(change["path"])
            relative = Path(path)
            if relative.is_absolute() or ".." in relative.parts:
                msg = "prewrite patch path escapes root"
                raise ValueError(msg)
            target = workspace / relative
            if target.is_file():
                files[path] = target.read_text(encoding="utf-8")
        return product_references_from_files(
            files,
            root=root,
            declared_commands=declared_commands,
            include_declarations=False,
        )
