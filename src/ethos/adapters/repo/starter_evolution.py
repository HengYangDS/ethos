"""Compose versioned starter bytes against authored Git history without effects."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object_sandbox import isolated_git_objects

if TYPE_CHECKING:
    from collections.abc import Callable
    from collections.abc import Mapping
    from pathlib import Path

    GitRunner = Callable[..., subprocess.CompletedProcess[Any]]


class _CompositionError(Exception):
    """Keep source refusal distinct from unknown native execution outcomes."""

    def __init__(self, gap: str, verdict: str, detail: str = "") -> None:
        super().__init__(gap)
        self.gap = gap
        self.verdict = verdict
        self.detail = detail


def _fail(gap: str, *, verdict: str = "unknown", detail: str = "") -> NoReturn:
    raise _CompositionError(gap, verdict, detail)


def _required(
    result: subprocess.CompletedProcess[Any], gap: str
) -> subprocess.CompletedProcess[Any]:
    if result.returncode:
        _fail(gap, detail=str(result.stderr).strip())
    return result


def _safe_path(value: str) -> bool:
    path = PurePosixPath(value)
    return (
        bool(value)
        and not path.is_absolute()
        and path.as_posix() == value
        and ".." not in path.parts
        and ".git" not in path.parts
        and not any(character in value for character in ("\\", "\0", "\r", "\n"))
    )


def _oid(value: str) -> bool:
    return len(value) in {40, 64} and re.fullmatch(r"[0-9a-f]+", value) is not None


def _source_inputs(
    root: Path,
    baseline: str,
    current: str,
    old_paths: tuple[str, ...],
    new_files: Mapping[str, bytes],
) -> dict[str, object]:
    if (
        not _oid(baseline)
        or not _oid(current)
        or not old_paths
        or len(set(old_paths)) != len(old_paths)
        or not new_files
        or not all(_safe_path(path) for path in (*old_paths, *new_files))
    ):
        _fail("starter_evolution_path_unsafe", verdict="block")
    observed = run_git(root, "rev-parse", "HEAD", observation=True, check=False, timeout=10)
    if observed.returncode or observed.stdout.strip() != current:
        _fail("starter_evolution_head_changed", verdict="block")
    ancestor = run_git(
        root,
        "merge-base",
        "--is-ancestor",
        baseline,
        current,
        observation=True,
        check=False,
        timeout=10,
    )
    if ancestor.returncode == 1:
        _fail("starter_evolution_baseline_not_ancestor", verdict="block")
    _required(ancestor, "starter_evolution_baseline_unavailable")
    return {
        "baseline": baseline,
        "current": current,
        "old_paths": sorted(old_paths),
        "new_files_sha256": {
            path: hashlib.sha256(content).hexdigest() for path, content in sorted(new_files.items())
        },
    }


def _template_candidate(
    git: GitRunner, baseline: str, old_paths: tuple[str, ...], new_files: Mapping[str, bytes]
) -> tuple[str, str]:
    _require_baseline_paths(git, baseline, old_paths)
    _required(git("read-tree", baseline), "starter_evolution_object_write_failed")
    for path in sorted(set(old_paths) - new_files.keys()):
        _required(
            git("update-index", "--force-remove", "--", path),
            "starter_evolution_object_write_failed",
        )
    for path, content in sorted(new_files.items()):
        blob = _required(
            git("hash-object", "-w", "--stdin", stdin=content, text=False),
            "starter_evolution_object_write_failed",
        )
        oid = blob.stdout.decode("ascii").strip()
        _required(
            git("update-index", "--add", "--cacheinfo", f"100644,{oid},{path}"),
            "starter_evolution_object_write_failed",
        )
    tree = _required(git("write-tree"), "starter_evolution_object_write_failed").stdout.strip()
    template = _required(
        git("commit-tree", tree, "-p", baseline, stdin="chore: generated starter candidate\n"),
        "starter_evolution_object_write_failed",
    ).stdout.strip()
    return tree, template


def _require_baseline_paths(git: GitRunner, baseline: str, old_paths: tuple[str, ...]) -> None:
    """Admit only exact regular starter files from the reviewed old tree."""
    listed = _required(
        git("ls-tree", "-r", "-z", baseline), "starter_evolution_baseline_unavailable"
    )
    entries: dict[str, tuple[str, str]] = {}
    for record in filter(None, listed.stdout.split("\0")):
        metadata, path = record.split("\t", 1)
        mode, kind, _oid = metadata.split(" ", 2)
        entries[path] = mode, kind
    if not set(old_paths).issubset(entries):
        _fail("starter_evolution_baseline_paths_missing", verdict="block")
    if any(
        entries[path][0] not in {"100644", "100755"} or entries[path][1] != "blob"
        for path in old_paths
    ):
        _fail("starter_evolution_baseline_paths_unsafe", verdict="block")


def _merged_candidate(
    git: GitRunner, baseline: str, current: str, template_tree: str, template: str
) -> dict[str, object]:
    merged = git("merge-tree", "--write-tree", f"--merge-base={baseline}", current, template)
    if merged.returncode == 1:
        _fail("starter_evolution_conflict", verdict="block", detail=merged.stdout[:4000])
    _required(merged, "starter_evolution_merge_unavailable")
    merged_tree = merged.stdout.splitlines()[0]
    before = _required(
        git("rev-parse", f"{current}^{{tree}}"), "starter_evolution_merge_unavailable"
    ).stdout.strip()
    patch = _required(
        git("diff", "--binary", "--full-index", before, merged_tree),
        "starter_evolution_patch_unavailable",
    ).stdout
    names = _required(
        git("diff", "--name-only", "-z", before, merged_tree),
        "starter_evolution_patch_unavailable",
    ).stdout
    return {
        "template_tree": template_tree,
        "merged_tree": merged_tree,
        "patch": patch,
        "patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "changed_paths": sorted(filter(None, names.split("\0"))),
    }


def compose_starter_evolution(
    root: Path,
    *,
    baseline: str,
    current: str,
    old_paths: tuple[str, ...],
    new_files: Mapping[str, bytes],
) -> dict[str, object]:
    """Return one exact Git-object merge proposal, never an adopter write."""
    inputs: dict[str, object] = {}
    try:
        inputs = _source_inputs(root, baseline, current, old_paths, new_files)
        with isolated_git_objects(root) as git:
            tree, template = _template_candidate(git, baseline, old_paths, new_files)
            candidate = _merged_candidate(git, baseline, current, tree, template)
        observed = run_git(root, "rev-parse", "HEAD", observation=True, check=False, timeout=10)
        if observed.returncode or observed.stdout.strip() != current:
            _fail("starter_evolution_head_changed", verdict="block")
    except _CompositionError as error:
        return {
            "verdict": error.verdict,
            "required_gaps": [error.gap],
            "detail": error.detail,
            "source_inputs": inputs,
            "patch": "",
            "changed_paths": [],
        }
    except (OSError, UnicodeError, ValueError, subprocess.TimeoutExpired) as error:
        return {
            "verdict": "unknown",
            "required_gaps": ["starter_evolution_observation_unknown"],
            "detail": str(error),
            "source_inputs": inputs,
            "patch": "",
            "changed_paths": [],
        }
    else:
        return {"verdict": "pass", "required_gaps": [], "source_inputs": inputs, **candidate}
