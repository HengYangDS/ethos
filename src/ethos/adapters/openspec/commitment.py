"""Compile acceptance Commitment values from official OpenSpec projections."""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING

import ethos.adapters.openspec.cli as openspec_cli
from ethos.adapters.openspec.lifecycle.archive_transition import attested_archive_transition
from ethos.adapters.openspec.projection import openspec_tree_projection
from ethos.adapters.openspec.selection import requested_change
from ethos.adapters.openspec.selection import resolve_change_selection
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.profile import load_committed_repository_profile
from ethos.contracts.semantic import Commitment
from ethos.repository.openspec.identifiers import active_change_root
from ethos.repository.openspec.identifiers import logical_change_identifier_issue
from ethos.repository.profile import INVALID_PROFILE_ERROR
from ethos.repository.profile import load_repository_profile

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


_TASK_CHECKBOX = re.compile(rb"(?m)^([ \t]*[-*+]\s+)\[[ xX]\]")


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
    artifact_digests: dict[str, str] | None = None,
    named: bool = False,
) -> Commitment:
    """Compile acceptance propositions from official OpenSpec JSON projections."""
    if not isinstance(projection, dict) or projection.get("id") != change:
        msg = f"openspec_show_invalid:{change}"
        raise ValueError(msg)
    deltas = projection.get("deltas")
    if not isinstance(deltas, list):
        msg = f"openspec_acceptance_missing:{change}"
        raise TypeError(msg)
    if _spec_free_deltas(deltas):
        acceptance = _spec_free_acceptance(
            change,
            status=status,
            artifact_digests=artifact_digests,
        )
    else:
        acceptance = tuple(
            item for delta in deltas for item in _acceptance_items(change, delta, named=named)
        )
    if not acceptance:
        msg = f"openspec_acceptance_missing:{change}"
        raise ValueError(msg)
    return Commitment(
        schema_version=3,
        id=f"change:{change}",
        acceptance=acceptance,
    )


def _spec_free_deltas(deltas: object) -> bool:
    """Distinguish native rename operations from spec-free proposal projections."""
    return isinstance(deltas, list) and all(
        isinstance(delta, dict)
        and "requirements" not in delta
        and str(delta.get("operation") or "").strip().upper() != "RENAMED"
        for delta in deltas
    )


def _spec_free_acceptance(
    change: str,
    *,
    status: object,
    artifact_digests: dict[str, str] | None,
) -> tuple[str, ...]:
    if not isinstance(status, dict):
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
        return {name: _spec_free_artifact_digest(name, path) for name, path in paths}
    except OSError:
        return {}


def _spec_free_artifact_digest(name: str, path: Path) -> str:
    content = path.read_bytes()
    identity = _TASK_CHECKBOX.sub(rb"\1[ ]", content) if name == "tasks" else content
    return hashlib.sha256(identity).hexdigest()


def _acceptance_items(change: str, delta: object, *, named: bool) -> tuple[str, ...]:
    if not isinstance(delta, dict):
        msg = f"openspec_show_invalid:{change}"
        raise TypeError(msg)
    spec = str(delta.get("spec") or "").strip()
    if str(delta.get("operation") or "").strip().upper() == "REMOVED":
        requirements = delta.get("requirements")
        if (
            not spec
            or not isinstance(requirements, list)
            or not requirements
            or any(
                not isinstance(requirement, dict)
                or not isinstance(requirement.get("name"), str)
                or not requirement["name"].strip()
                for requirement in requirements
            )
        ):
            msg = f"openspec_show_invalid:{change}"
            raise ValueError(msg)
        return tuple(
            f"{spec}:remove:{json.dumps(requirement, sort_keys=True, ensure_ascii=False)}"
            for requirement in requirements
        )
    if str(delta.get("operation") or "").strip().upper() == "RENAMED":
        rename = delta.get("rename")
        if (
            not spec
            or not isinstance(rename, dict)
            or set(rename) != {"from", "to"}
            or any(not isinstance(value, str) or not value.strip() for value in rename.values())
            or rename["from"].strip() == rename["to"].strip()
        ):
            msg = f"openspec_show_invalid:{change}"
            raise ValueError(msg)
        return (f"{spec}:rename:{json.dumps(rename, sort_keys=True, ensure_ascii=False)}",)
    requirements = delta.get("requirements")
    if not spec or not isinstance(requirements, list):
        msg = f"openspec_show_invalid:{change}"
        raise ValueError(msg)
    return tuple(
        item
        for requirement in requirements
        for item in _requirement_acceptance(change, spec, requirement, named=named)
    )


def _requirement_acceptance(
    change: str, spec: str, requirement: object, *, named: bool
) -> tuple[str, ...]:
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
    if not named:
        return (
            f"{spec}:requirement:{text}",
            *(f"{spec}:scenario:{raw}" for raw in raw_scenarios),
        )
    # Names carry identity, so requirements or scenarios with equal bodies stay distinct.
    names = (requirement.get("name"), *(scenario.get("name") for scenario in scenarios))
    if not all(isinstance(name, str) and name.strip() for name in names):
        msg = f"openspec_acceptance_missing:{change}"
        raise ValueError(msg)
    title, *titles = (str(name).strip() for name in names)
    return (
        f"{spec}:requirement:{_identity(title, text)}",
        *(
            f"{spec}:scenario:{_identity(title, scenario, raw)}"
            for scenario, raw in zip(titles, raw_scenarios, strict=True)
        ),
    )


def _identity(*parts: str) -> str:
    return json.dumps(list(parts), ensure_ascii=False, separators=(",", ":"))


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
    require_absent: bool = False,
    attestations: tuple[Attestation, ...] | None = None,
) -> Commitment | None:
    if tree_ref is None:
        return None
    if require_absent:
        if change_id is None or logical_change_identifier_issue(change_id):
            return None
        active = run_git(
            repo, "ls-tree", "-z", tree_ref, "--", active_change_root(change_id), check=False
        )
        if active.returncode or active.stdout:
            return None
    archived = attested_archive_transition(
        repo, head=tree_ref, change=change_id, attestations=attestations
    )
    if archived is None:
        return None
    return _accepted_commitment(archived[0], expected_digest=expected_digest)


def load_openspec_commitment(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
    expected_digest: str | None = None,
    attestations: tuple[Attestation, ...] | None = None,
    official_command: tuple[str, ...] | None = None,
    official_status: object = None,
    official_projection: dict[str, object] | None = None,
    named: bool = False,
) -> Commitment:
    """Compile exact official intent, sharing only a caller's current evidence observation."""
    (commitment,) = _load_commitments(
        repo,
        change_id=change_id,
        tree_ref=tree_ref,
        expected_digest=expected_digest,
        attestations=attestations,
        official_command=official_command,
        official_status=official_status,
        official_projection=official_projection,
        encodings=(named,),
    )
    return commitment


def admissible_openspec_commitments(
    repo: Path,
    *,
    change_id: str | None,
    tree_ref: str | None,
    attestations: tuple[Attestation, ...] | None = None,
) -> tuple[Commitment, ...]:
    """Return each encoding of the exact source that a proof may carry, legacy first.

    While landing hooks move to named acceptance identity, a proof may carry either encoding of
    the same source; a source whose requirements or scenarios lack names admits only the legacy one.
    """
    return _load_commitments(
        repo,
        change_id=change_id,
        tree_ref=tree_ref,
        attestations=attestations,
        encodings=(False, True),
    )


def _load_commitments(
    repo: Path,
    *,
    change_id: str | None = None,
    tree_ref: str | None = None,
    expected_digest: str | None = None,
    attestations: tuple[Attestation, ...] | None = None,
    official_command: tuple[str, ...] | None = None,
    official_status: object = None,
    official_projection: dict[str, object] | None = None,
    encodings: tuple[bool, ...],
) -> tuple[Commitment, ...]:
    """Compile one official projection in each requested encoding; the first must compile."""
    if not openspec_profile_enabled(repo, tree_ref=tree_ref):
        msg = "openspec_profile_not_enabled"
        raise ValueError(msg)
    change_id = requested_change(change_id)
    command = official_command
    archived = _archived_commitment(
        repo,
        tree_ref=tree_ref,
        change_id=change_id,
        expected_digest=expected_digest,
        require_absent=True,
        attestations=attestations,
    )
    if archived is not None:
        return (archived,)
    if (
        official_projection is not None
        and (command := command or openspec_cli.openspec_base_command()) is None
    ):
        msg = "openspec_official_cli_missing"
        raise ValueError(msg)
    with openspec_tree_projection(repo, tree_ref) as projection:
        if change_id is None:
            (listed,) = openspec_cli.run_json_batch(projection, command, (("list", "--json"),))
            rows = listed.get("json", {}).get("changes", [])
            selected, gap = resolve_change_selection(rows, None, root=repo, tree_ref=tree_ref)
            gaps = [gap] if gap else []
            if (
                gaps == ["openspec_active_change_missing"]
                and (
                    archived := _archived_commitment(
                        repo,
                        tree_ref=tree_ref,
                        change_id=None,
                        expected_digest=expected_digest,
                        attestations=attestations,
                    )
                )
                is not None
            ):
                return (archived,)
            if selected is None:
                raise ValueError(gaps[0])
            change_id = selected
        if logical_change_identifier_issue(change_id):
            msg = "openspec_change_required"
            raise ValueError(msg)
        result = (
            official_projection
            if tree_ref is None and official_projection is not None
            else openspec_cli.run_json_batch(
                projection, command, (("show", change_id, "--type", "change", "--json"),)
            )[0]
        )
        if result.get("exit_code") != 0 or result.get("parse_error"):
            archived = _archived_commitment(
                repo,
                tree_ref=tree_ref,
                change_id=change_id,
                expected_digest=expected_digest,
                attestations=attestations,
            )
            if archived is not None:
                return (archived,)
            msg = f"openspec_show_failed:{change_id}"
            raise ValueError(msg)
        commitments = _projected_commitments(
            projection,
            command,
            change_id,
            result.get("json"),
            status=official_status if tree_ref is None else None,
            encodings=encodings,
        )
    return tuple(
        _accepted_commitment(commitment, expected_digest=expected_digest)
        for commitment in commitments
    )


def _projected_commitments(
    projection: Path,
    command: tuple[str, ...] | None,
    change: str,
    payload: object,
    *,
    status: object,
    encodings: tuple[bool, ...],
) -> tuple[Commitment, ...]:
    """Compile each requested encoding; only the first one is required to compile."""
    commitments: list[Commitment] = []
    for index, named in enumerate(encodings):
        try:
            commitments.append(
                _projected_commitment(
                    projection, command, change, payload, status=status, named=named
                )
            )
        except ValueError:
            if not index:
                raise
    return tuple(commitments)


def _projected_commitment(
    projection: Path,
    command: tuple[str, ...] | None,
    change: str,
    payload: object,
    *,
    status: object = None,
    named: bool = False,
) -> Commitment:
    """Read additional official artifact inputs only for a spec-free Change."""
    deltas = payload.get("deltas") if isinstance(payload, dict) else None
    if not _spec_free_deltas(deltas):
        return commitment_from_projection(change, payload, named=named)
    if status is None:
        status = openspec_cli.run_json_batch(
            projection, command, (("status", "--change", change, "--json"),)
        )[0].get("json")
    return commitment_from_projection(
        change,
        payload,
        status=status,
        artifact_digests=_spec_free_artifact_digests(projection, change),
    )
