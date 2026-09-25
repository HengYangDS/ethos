"""Compose versioned starter bytes against authored Git history without effects."""

from __future__ import annotations

import hashlib
import re
import subprocess
import tomllib
from collections.abc import Mapping
from importlib import metadata
from pathlib import Path
from pathlib import PurePosixPath
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from typing import Any
from typing import NoReturn

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_object import read_objects
from ethos.adapters.repo.git_object_sandbox import isolated_git_objects
from ethos.adapters.repo.profile import repository_identity
from ethos.adapters.repo.starter.generation import compose_starter

if TYPE_CHECKING:
    from collections.abc import Callable

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
    old_files: Mapping[str, str],
    new_files: Mapping[str, bytes],
) -> dict[str, object]:
    old_paths = tuple(old_files)
    if (
        not _oid(baseline)
        or not _oid(current)
        or not old_paths
        or not new_files
        or not all(_safe_path(path) for path in (*old_paths, *new_files))
    ):
        _fail("starter_evolution_path_unsafe", verdict="block")
    if not all(
        isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest)
        for digest in old_files.values()
    ):
        _fail("starter_evolution_baseline_digest_invalid", verdict="block")
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
        "old_files_sha256": dict(sorted(old_files.items())),
        "new_files_sha256": {
            path: hashlib.sha256(content).hexdigest() for path, content in sorted(new_files.items())
        },
    }


def _template_candidate(
    root: Path,
    git: GitRunner,
    baseline: str,
    old_files: Mapping[str, str],
    new_files: Mapping[str, bytes],
) -> tuple[str, str]:
    _require_baseline_paths(root, git, baseline, old_files)
    old_paths = tuple(old_files)
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


def _require_baseline_paths(
    root: Path, git: GitRunner, baseline: str, old_files: Mapping[str, str]
) -> None:
    """Admit only exact regular starter bytes from the reviewed old tree."""
    listed = _required(
        git("ls-tree", "-r", "-z", baseline), "starter_evolution_baseline_unavailable"
    )
    entries: dict[str, tuple[str, str, str]] = {}
    for record in filter(None, listed.stdout.split("\0")):
        metadata, path = record.split("\t", 1)
        mode, kind, object_id = metadata.split(" ", 2)
        entries[path] = mode, kind, object_id
    if not old_files.keys() <= entries.keys():
        _fail("starter_evolution_baseline_paths_missing", verdict="block")
    if any(entries[path][0] != "100644" or entries[path][1] != "blob" for path in old_files):
        _fail("starter_evolution_baseline_paths_unsafe", verdict="block")
    ordered = sorted(old_files)
    contents = read_objects(
        root,
        tuple(entries[path][2] for path in ordered),
        gap="starter_evolution_baseline_unavailable",
    )
    for path, content in zip(ordered, contents, strict=True):
        digest = old_files[path]
        if hashlib.sha256(content).hexdigest() != digest:
            _fail("starter_evolution_baseline_content_mismatch", verdict="block")


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
    old_files: Mapping[str, str],
    new_files: Mapping[str, bytes],
) -> dict[str, object]:
    """Return one exact Git-object merge proposal, never an adopter write."""
    inputs: dict[str, object] = {}
    try:
        inputs = _source_inputs(root, baseline, current, old_files, new_files)
        with isolated_git_objects(root) as git:
            tree, template = _template_candidate(root, git, baseline, old_files, new_files)
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


def _formation_source(root: Path) -> tuple[str, dict[str, str], str, str]:
    """Resolve an exact old starter from its result, then verify its Git source."""
    _set_root, attestations = read_attestation_set(root)
    formations = [item for item in attestations if item.predicate == "effect:starter-formation"]
    if not formations:
        _fail("starter_evolution_provenance_missing", verdict="block")
    if len(formations) != 1:
        _fail("starter_evolution_provenance_ambiguous", verdict="block")
    record = formations[0]
    body = record.payload.body
    claim = body.get("claim")
    sources = body.get("input")
    output = body.get("output")
    result = body.get("result")
    if (
        record.verdict != "pass"
        or record.payload.kind != "effect:native"
        or not isinstance(claim, Mapping)
        or claim.get("operation") != "starter.form"
        or not isinstance(result, Mapping)
        or result.get("state") != "applied"
        or result.get("executed") is not True
        or not isinstance(sources, Mapping)
        or not isinstance(sources.get("sources"), Mapping)
        or not isinstance(output, Mapping)
        or body.get("repository") != repository_identity(root)
    ):
        _fail("starter_evolution_provenance_invalid", verdict="block")
    generator = sources["sources"]
    baseline = output.get("head")
    old_files = output.get("starter_outputs")
    old_version = generator.get("starter_generator_version")
    if (
        generator.get("starter") != "python-library"
        or generator.get("starter_generator") != "uv"
        or not isinstance(old_version, str)
        or not old_version
        or not isinstance(baseline, str)
        or not _oid(baseline)
        or not isinstance(old_files, Mapping)
        or "pyproject.toml" not in old_files
        or not all(
            isinstance(path, str) and isinstance(digest, str) for path, digest in old_files.items()
        )
    ):
        _fail("starter_evolution_provenance_invalid", verdict="block")
    baseline_project = run_git(
        root,
        "show",
        f"{baseline}:pyproject.toml",
        text=False,
        check=False,
        observation=True,
        timeout=10,
    )
    if baseline_project.returncode:
        _fail("starter_evolution_baseline_unavailable")
    try:
        project = tomllib.loads(baseline_project.stdout.decode())["project"]
        project_name = project["name"]
    except (KeyError, TypeError, UnicodeError, ValueError) as error:
        _fail("starter_evolution_provenance_invalid", verdict="block", detail=str(error))
    if not isinstance(project_name, str) or not _safe_path(project_name) or "/" in project_name:
        _fail("starter_evolution_provenance_invalid", verdict="block")
    return baseline, dict(old_files), old_version, project_name


def plan_starter_evolution(root: Path, *, purpose: str) -> dict[str, object]:
    """Regenerate a recorded starter as a read-only, reviewable Git proposal."""
    try:
        if not purpose.strip():
            _fail("starter_evolution_purpose_missing", verdict="block")
        baseline, old_files, old_version, project_name = _formation_source(root)
        head = run_git(root, "rev-parse", "HEAD", check=False, observation=True, timeout=10)
        state = run_git(
            root, "status", "--porcelain", "-z", check=False, observation=True, timeout=10
        )
        if head.returncode or state.returncode:
            _fail("starter_evolution_repository_unavailable")
        if state.stdout:
            _fail("starter_evolution_worktree_dirty", verdict="block")
        current = head.stdout.strip()
        with TemporaryDirectory(prefix="ethos-starter-evolution-") as temporary:
            candidate = Path(temporary) / project_name
            candidate.mkdir()
            _outputs, generated, gap, detail = compose_starter(
                candidate, "python-library", purpose.strip()
            )
            if gap:
                _fail(gap, detail=detail)
            new_files = {path: (candidate / path).read_bytes() for path in generated}
            if not new_files or any(
                hashlib.sha256(content).hexdigest() != generated[path]
                for path, content in new_files.items()
            ):
                _fail("starter_evolution_generation_changed")
            report = compose_starter_evolution(
                root,
                baseline=baseline,
                current=current,
                old_files=old_files,
                new_files=new_files,
            )
        inputs = report.get("source_inputs")
        if isinstance(inputs, dict):
            inputs.update(
                {
                    "starter": "python-library",
                    "old_generator_version": old_version,
                    "new_generator_version": metadata.version("uv"),
                    "purpose": purpose.strip(),
                }
            )
    except _CompositionError as error:
        return {
            "verdict": error.verdict,
            "required_gaps": [error.gap],
            "detail": error.detail,
            "patch": "",
            "changed_paths": [],
        }
    except (
        OSError,
        UnicodeError,
        ValueError,
        subprocess.TimeoutExpired,
        metadata.PackageNotFoundError,
    ) as error:
        return {
            "verdict": "unknown",
            "required_gaps": ["starter_evolution_observation_unknown"],
            "detail": str(error),
            "patch": "",
            "changed_paths": [],
        }
    else:
        return report
