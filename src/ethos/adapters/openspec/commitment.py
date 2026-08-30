"""Compile acceptance Commitment values from official OpenSpec projections."""

from __future__ import annotations

import hashlib
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.contracts.semantic import Commitment
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from collections.abc import Iterator


@contextmanager
def _openspec_projection(repo: Path, tree_ref: str | None) -> Iterator[Path]:
    """Expose official OpenSpec artifacts from one exact Git tree."""
    if tree_ref is None:
        yield repo
        return
    paths = run_git(
        repo,
        "ls-tree",
        "-r",
        "-z",
        "--name-only",
        tree_ref,
        "--",
        "openspec",
    ).stdout
    if not paths:
        msg = "openspec_tree_projection_missing"
        raise ValueError(msg)
    with tempfile.TemporaryDirectory(prefix="ethos-openspec-tree-") as directory:
        projection = Path(directory)
        environment = {"GIT_INDEX_FILE": (projection / "index").as_posix()}
        run_git(repo, "read-tree", tree_ref, env=environment)
        run_git(
            repo,
            "checkout-index",
            f"--prefix={projection.as_posix()}/",
            "--stdin",
            "-z",
            env=environment,
            stdin=paths,
        )
        yield projection


def openspec_profile_enabled(repo: Path, *, tree_ref: str | None = None) -> bool:
    """Return whether the explicit repository profile selects OpenSpec."""
    profile = (
        load_committed_repository_profile(repo, tree_ref)
        if tree_ref
        else load_repository_profile(repo)
    )
    if profile.state == "invalid":
        raise ValueError(INVALID_PROFILE_ERROR)
    return profile.declaration is not None and profile.declaration.openspec is not None


def commitment_from_projection(
    change: str,
    projection: object,
    *,
    status: object = None,
    apply: object = None,
    artifact_digests: dict[str, str] | None = None,
) -> Commitment:
    """Compile acceptance propositions from official OpenSpec JSON projections."""
    if not isinstance(projection, dict) or projection.get("id") != change:
        msg = f"openspec_show_invalid:{change}"
        raise ValueError(msg)
    deltas = projection.get("deltas")
    if not isinstance(deltas, list):
        msg = f"openspec_acceptance_missing:{change}"
        raise TypeError(msg)
    spec_free_projection = not deltas or all(
        isinstance(delta, dict) and "requirements" not in delta for delta in deltas
    )
    if spec_free_projection:
        acceptance = _spec_free_acceptance(
            change,
            status=status,
            apply=apply,
            artifact_digests=artifact_digests,
        )
    else:
        acceptance = tuple(item for delta in deltas for item in _acceptance_items(change, delta))
    if not acceptance:
        msg = f"openspec_acceptance_missing:{change}"
        raise ValueError(msg)
    return Commitment(
        schema_version=3,
        id=f"change:{change}",
        acceptance=acceptance,
    )


def _spec_free_acceptance(
    change: str,
    *,
    status: object,
    apply: object,
    artifact_digests: dict[str, str] | None,
) -> tuple[str, ...]:
    if not isinstance(status, dict) or not isinstance(apply, dict):
        return ()
    artifacts = status.get("artifacts")
    if not isinstance(artifacts, list):
        return ()
    states = {
        str(artifact.get("id") or ""): str(artifact.get("status") or "")
        for artifact in artifacts
        if isinstance(artifact, dict)
    }
    digests = artifact_digests or {}
    names = ("metadata", "proposal", "design", "tasks")
    if (
        status.get("changeName") != change
        or status.get("isComplete") is not True
        or states.get("proposal") != "done"
        or states.get("specs") != "skipped"
        or states.get("design") != "done"
        or states.get("tasks") != "done"
        or apply.get("changeName") != change
        or apply.get("state") != "all_done"
        or set(digests) != set(names)
        or any(
            len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest)
            for digest in digests.values()
        )
    ):
        return ()
    return (
        f"openspec:change:{change}",
        "openspec:specs:skipped",
        *(f"openspec:artifact:{name}:sha256:{digests[name]}" for name in names),
    )


def _spec_free_artifact_digests(root: Path, change: str) -> dict[str, str]:
    change_root = root / "openspec" / "changes" / change
    paths = (
        ("metadata", change_root / ".openspec.yaml"),
        ("proposal", change_root / "proposal.md"),
        ("design", change_root / "design.md"),
        ("tasks", change_root / "tasks.md"),
    )
    try:
        return {name: hashlib.sha256(path.read_bytes()).hexdigest() for name, path in paths}
    except OSError:
        return {}


def _acceptance_items(change: str, delta: object) -> tuple[str, ...]:
    if not isinstance(delta, dict):
        msg = f"openspec_show_invalid:{change}"
        raise TypeError(msg)
    if str(delta.get("operation") or "").strip().upper() == "REMOVED":
        return ()
    spec = str(delta.get("spec") or "").strip()
    requirements = delta.get("requirements")
    if not spec or not isinstance(requirements, list):
        msg = f"openspec_show_invalid:{change}"
        raise ValueError(msg)
    return tuple(
        item
        for requirement in requirements
        for item in _requirement_acceptance(change, spec, requirement)
    )


def _requirement_acceptance(change: str, spec: str, requirement: object) -> tuple[str, ...]:
    if not isinstance(requirement, dict):
        msg = f"openspec_show_invalid:{change}"
        raise TypeError(msg)
    text = str(requirement.get("text") or "").strip()
    scenarios = requirement.get("scenarios")
    if not text or not isinstance(scenarios, list) or not scenarios:
        msg = f"openspec_acceptance_missing:{change}"
        raise ValueError(msg)
    raw_scenarios = tuple(
        str(scenario.get("rawText") or "").strip() if isinstance(scenario, dict) else ""
        for scenario in scenarios
    )
    if not all(raw_scenarios):
        msg = f"openspec_acceptance_missing:{change}"
        raise ValueError(msg)
    return (
        f"{spec}:requirement:{text}",
        *(f"{spec}:scenario:{raw}" for raw in raw_scenarios),
    )


def _listed_change_names(payload: object) -> tuple[str, ...]:
    rows = payload.get("changes") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return ()
    return tuple(
        name for row in rows if isinstance(row, dict) and (name := str(row.get("name") or ""))
    )


def _accepted_commitment(
    commitment: Commitment,
    *,
    expected_digest: str | None,
) -> Commitment:
    if expected_digest is not None and commitment.digest() != expected_digest:
        msg = "commitment_digest_mismatch"
        raise ValueError(msg)
    return commitment


def _archived_commitment(
    repo: Path,
    *,
    tree_ref: str | None,
    change_id: str | None,
    expected_digest: str | None,
) -> Commitment | None:
    if tree_ref is None:
        return None
    archived = attested_archive_transition(repo, head=tree_ref, change=change_id)
    if archived is None:
        return None
    return _accepted_commitment(archived[0], expected_digest=expected_digest)


def load_openspec_commitment(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
    expected_digest: str | None = None,
) -> Commitment:
    """Compile one active Change from the official OpenSpec JSON projection."""
    if not openspec_profile_enabled(repo, tree_ref=tree_ref):
        msg = "openspec_profile_not_enabled"
        raise ValueError(msg)
    command = openspec_cli.openspec_base_command()
    if command is None:
        msg = "openspec_official_cli_missing"
        raise ValueError(msg)
    with _openspec_projection(repo, tree_ref) as projection:
        if change_id is None:
            listed = openspec_cli.run_json(projection, command, ("list", "--json"))
            names = _listed_change_names(listed.get("json"))
            if (
                not names
                and (
                    archived := _archived_commitment(
                        repo,
                        tree_ref=tree_ref,
                        change_id=None,
                        expected_digest=expected_digest,
                    )
                )
                is not None
            ):
                return archived
            if len(names) != 1:
                raise ValueError(
                    "openspec_active_change_missing"
                    if not names
                    else f"openspec_active_change_ambiguous:{','.join(names)}"
                )
            change_id = names[0]
        if logical_change_identifier_issue(change_id):
            msg = "openspec_change_required"
            raise ValueError(msg)
        result = openspec_cli.run_json(projection, command, ("show", change_id, "--json"))
        if result.get("exit_code") != 0 or result.get("parse_error"):
            archived = _archived_commitment(
                repo,
                tree_ref=tree_ref,
                change_id=change_id,
                expected_digest=expected_digest,
            )
            if archived is not None:
                return archived
            msg = f"openspec_show_failed:{change_id}"
            raise ValueError(msg)
        payload = result.get("json")
        deltas = payload.get("deltas") if isinstance(payload, dict) else None
        spec_free = isinstance(deltas, list) and (
            not deltas
            or all(isinstance(delta, dict) and "requirements" not in delta for delta in deltas)
        )
        if spec_free:
            status = openspec_cli.run_json(
                projection,
                command,
                ("status", "--change", change_id, "--json"),
            )
            apply = openspec_cli.run_json(
                projection,
                command,
                ("instructions", "apply", "--change", change_id, "--json"),
            )
            commitment = commitment_from_projection(
                change_id,
                payload,
                status=status.get("json"),
                apply=apply.get("json"),
                artifact_digests=_spec_free_artifact_digests(projection, change_id),
            )
        else:
            commitment = commitment_from_projection(change_id, payload)
    return _accepted_commitment(commitment, expected_digest=expected_digest)
