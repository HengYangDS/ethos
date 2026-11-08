"""Prepare and fence exact index patches for the existing prewrite owner."""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_patch import unified_patch_changes

if TYPE_CHECKING:
    from collections.abc import Callable


def index_patch_prewrite(
    root: Path,
    paths: list[Path],
    patch: str,
    evaluate: Callable[[dict[str, str]], dict[str, object]],
) -> dict[str, object]:
    """Evaluate one disposable postimage and independently fence its real prestate."""
    refused = _patch_scope(root, paths, patch)
    if refused:
        return refused
    index = run_git(root, "rev-parse", "--path-format=absolute", "--git-path", "index", check=False)
    head = run_git(root, "rev-parse", "--verify", "HEAD", check=False)
    if index.returncode or head.returncode:
        return _refusal("prewrite_index_prestate_unavailable", verdict="unknown")
    source = Path(index.stdout.strip())
    try:
        before, gap = _index_preimage(root, source)
        if gap:
            return _refusal(gap, verdict="unknown")
        with tempfile.TemporaryDirectory(prefix="ethos-index-prewrite-") as directory:
            workspace = Path(directory)
            candidate = workspace / "index"
            candidate.write_bytes(before)
            objects = workspace / "objects"
            objects.mkdir()
            environment = {
                "GIT_INDEX_FILE": candidate.as_posix(),
                "GIT_OBJECT_DIRECTORY": objects.as_posix(),
                "GIT_ALTERNATE_OBJECT_DIRECTORIES": (
                    Path(git_common_dir(root)) / "objects"
                ).as_posix(),
            }
            expected_tree, gap = _apply_candidate(root, patch, environment)
            if gap:
                return _refusal(
                    gap,
                    verdict="unknown" if gap == "prewrite_index_prestate_unavailable" else "block",
                )
            report = evaluate(environment)
            report = _bind_request(report, source, before, patch, expected_tree)
            refused = _prestate_drift(root, source, before, head.stdout, index.stdout)
            return (
                _refusal(
                    refused,
                    verdict="unknown" if refused == "prewrite_index_locked" else "block",
                    report=report,
                )
                if refused
                else report
            )
    except (OSError, ValueError) as error:
        return _refusal(
            "prewrite_index_observation_unavailable",
            verdict="unknown",
            report={"observation": {"error": str(error)}},
        )


def _index_preimage(root: Path, source: Path) -> tuple[bytes, str]:
    if Path(f"{source}.lock").exists():
        return b"", "prewrite_index_locked"
    shared = run_git(root, "rev-parse", "--shared-index-path", check=False)
    if shared.returncode:
        return b"", "prewrite_index_prestate_unavailable"
    if shared.stdout.strip():
        return b"", "prewrite_index_split_index_unavailable"
    before = source.read_bytes()
    return before, "" if before else "prewrite_index_prestate_unavailable"


def _apply_candidate(root: Path, patch: str, index_env: dict[str, str]) -> tuple[str, str]:
    expected_tree = run_git(root, "write-tree", check=False, env=index_env)
    if expected_tree.returncode:
        return "", "prewrite_index_prestate_unavailable"
    for options in (("--check",), ()):
        applied = run_git(
            root,
            "apply",
            "--cached",
            *options,
            "--whitespace=error-all",
            "-",
            stdin=patch.encode("utf-8"),
            text=False,
            check=False,
            env=index_env,
        )
        if applied.returncode:
            return "", "prewrite_patch_preimage_mismatch"
    return expected_tree.stdout.strip(), ""


def _patch_scope(root: Path, paths: list[Path], patch: str) -> dict[str, object]:
    if not patch:
        return _refusal("prewrite_index_patch_required")
    changes, gap = unified_patch_changes(root, patch)
    if gap:
        return _refusal(gap)
    try:
        root_path = root.resolve()
        relative = {
            (path if path.is_absolute() else root_path / path).relative_to(root_path)
            for path in paths
        }
    except ValueError:
        return _refusal("prewrite_patch_paths_mismatch")
    if any(".." in path.parts for path in relative):
        return _refusal("prewrite_patch_paths_mismatch")
    requested = sorted(path.as_posix() for path in relative)
    affected = {
        str(path)
        for change in changes
        for path in (change["old_path"], change["path"])
        if path != "/dev/null"
    }
    if sorted(affected) != requested:
        return _refusal("prewrite_patch_paths_mismatch")
    return {}


def _prestate_drift(root: Path, source: Path, before: bytes, head: str, index: str) -> str:
    if Path(f"{source}.lock").exists():
        return "prewrite_index_locked"
    current_head = run_git(root, "rev-parse", "--verify", "HEAD", check=False)
    current_index = run_git(
        root,
        "rev-parse",
        "--path-format=absolute",
        "--git-path",
        "index",
        check=False,
    )
    if current_head.returncode or current_index.returncode:
        message = "prewrite_index_prestate_unavailable"
        raise ValueError(message)
    if current_head.stdout != head:
        return "prewrite_index_head_changed_during_admission"
    if current_index.stdout != index or source.read_bytes() != before:
        return "prewrite_index_index_changed_during_admission"
    return ""


def _bind_request(
    report: dict[str, object],
    index: Path,
    before: bytes,
    patch: str,
    expected_tree: str,
) -> dict[str, object]:
    binding = {
        "target": "index",
        "index_path": index.as_posix(),
        "expected_index_tree": expected_tree,
        "index_preimage_sha256": hashlib.sha256(before).hexdigest(),
        "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
    }
    subject = report.get("request_binding")
    if isinstance(subject, dict) and isinstance(subject.get("expected_state"), dict):
        subject["expected_state"].update(binding)
    decision = report.get("decision")
    if isinstance(decision, dict):
        subject = decision.get("subject")
        if isinstance(subject, dict) and isinstance(subject.get("expected_state"), dict):
            subject["expected_state"].update(binding)
        basis = decision.get("decision_basis")
        if isinstance(basis, dict) and isinstance(basis.get("state_bindings"), list):
            basis["state_bindings"].extend(binding)
    return {**report, "index_prewrite": binding}


def _refusal(
    gap: str,
    *,
    verdict: str = "block",
    report: dict[str, object] | None = None,
) -> dict[str, object]:
    result = dict(report or {})
    previous = result.get("required_gaps", [])
    gaps = list(dict.fromkeys([gap, *(previous if isinstance(previous, list) else [])]))
    result.update(
        verdict=verdict,
        error=gap,
        required_gaps=gaps,
        next_action="observe the current index and prepare a new exact patch",
        user_decision_required=False,
    )
    decision = result.get("decision")
    if isinstance(decision, dict):
        decision.update(
            verdict=verdict, why=[gap], required_gaps=gaps, next_action="repair_required_gap"
        )
    return result
