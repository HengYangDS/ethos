"""Verify native commit rewrites and their conserved contribution relationships."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Mapping
from pathlib import Path
from time import monotonic
from typing import Any
from typing import NamedTuple

from ethos.adapters.process import run_command
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import git_executable
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git import run_git
from ethos.adapters.repo.git_effect_attestation import declares_transition
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_git_effect_attestation
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json


class RewriteEdge(NamedTuple):
    """One exact historical rewrite; its existence never grants current authority."""

    previous: str
    current: str
    attestation_id: str
    kind: str
    candidate: str = ""


def refreshed_object_provenance(root: Path, *, old: str, new: str) -> dict[str, object] | None:
    """Require validated rewrite evidence and exact native contribution conservation."""
    matches = []
    for record in read_attestation_set(root)[1]:
        if not declares_transition(record, "lane.refresh"):
            continue
        policy = record.payload.body["plan"]["policy"]
        branch = str(policy.get("execution_branch") or "")
        edge = validated_refresh_edge(root, branch=branch, attestation=record)
        if edge and is_ancestor(root, old, edge.previous) and is_ancestor(root, edge.current, new):
            matches.append(edge)
    if not matches:
        return None
    if len(matches) != 1:
        return {"state": "not_absorbed", "old": old, "reason": "refresh_evidence_ambiguous"}
    edge = matches[0]
    conservation = observe_refresh_conservation(root, edge)
    return {
        "state": "refreshed" if conservation["verdict"] == "pass" else "not_absorbed",
        "old": old,
        "replacement": edge.current,
        "attestation_id": edge.attestation_id,
        "conservation": conservation,
    }


def observe_refresh_conservation(root: Path, edge: RewriteEdge) -> dict[str, object]:
    """Compose exact native inputs in an owned bare object store, never in the source."""
    environment = {
        "PATH": os.environ.get("PATH", os.defpath),
        "LC_ALL": "C",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_ATTR_NOSYSTEM": "1",
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_TERMINAL_PROMPT": "0",
    }
    deadline = monotonic() + 30
    observed: dict[str, object] = {"verdict": "unknown", "reason": "native_composition_unavailable"}

    def remaining_seconds() -> float:
        remaining = deadline - monotonic()
        if remaining <= 0:
            command = ("git", "merge-tree")
            raise subprocess.TimeoutExpired(command, 30)
        return remaining

    try:
        coordinates = run_git(
            root,
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            "objects",
            "--show-object-format",
            observation=True,
            timeout=remaining_seconds(),
            check=False,
        )
        values = coordinates.stdout.splitlines()
        if coordinates.returncode or len(values) != 2 or values[1] not in {"sha1", "sha256"}:
            return observed
        objects, object_format = Path(values[0]), values[1]
        if not objects.is_absolute() or not objects.is_dir():
            return observed
        executable = git_executable(environment)
        with tempfile.TemporaryDirectory(prefix="ethos-contribution-") as temporary:
            isolated = Path(temporary)

            def git(*args: str) -> subprocess.CompletedProcess[str]:
                return run_command(
                    isolated,
                    (executable, *args),
                    env=environment,
                    inherit_environment=False,
                    stdin="",
                    timeout=remaining_seconds(),
                )

            initialized = git("init", "--bare", "--template=", f"--object-format={object_format}")
            if initialized.returncode:
                return observed
            (isolated / "objects/info/alternates").write_text(objects.resolve().as_posix() + "\n")
            bases = git("merge-base", "--all", edge.previous, edge.candidate)
            if bases.returncode or len(bases.stdout.splitlines()) != 1:
                return {**observed, "reason": "unique_merge_base_unavailable"}
            base = bases.stdout.strip()
            result = git(
                "merge-tree", "--write-tree", f"--merge-base={base}", edge.candidate, edge.previous
            )
            output = git("rev-parse", f"{edge.current}^{{tree}}")
            return _composition_result(edge, base, result, output)
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {**observed, "reason": str(error)}


def _composition_result(
    edge: RewriteEdge,
    base: str,
    result: subprocess.CompletedProcess[str],
    output: subprocess.CompletedProcess[str],
) -> dict[str, object]:
    """Separate native conflict, missing observations and exact tree agreement."""
    observed = {
        "verdict": "unknown",
        "reason": "native_composition_unavailable",
        "base": base,
        "candidate": edge.candidate,
        "previous": edge.previous,
        "output": edge.current,
        "exit_code": result.returncode,
    }
    if result.returncode == 1:
        return {**observed, "verdict": "block", "reason": "native_composition_conflict"}
    if result.returncode or output.returncode:
        return observed
    composed = result.stdout.splitlines()[0] if result.stdout.splitlines() else ""
    expected = output.stdout.strip()
    equal = bool(composed) and composed == expected
    return {
        **observed,
        "verdict": "pass" if equal else "block",
        "reason": "conserved" if equal else "native_composition_mismatch",
        "composed_tree": composed,
        "output_tree": expected,
    }


def refresh_edges(
    root: Path, *, branch: str, attestations: tuple[Any, ...]
) -> dict[str, tuple[RewriteEdge, ...]]:
    """Derive the branch's validated adjacency relation from exact refresh evidence."""
    grouped: dict[str, list[RewriteEdge]] = {}
    for attestation in attestations:
        edge = validated_refresh_edge(root, branch=branch, attestation=attestation)
        if edge is not None:
            grouped.setdefault(edge.previous, []).append(edge)
    return {previous: tuple(values) for previous, values in grouped.items()}


def validated_refresh_edge(
    root: Path,
    *,
    branch: str,
    attestation: Any,
) -> RewriteEdge | None:
    """Decode one refresh edge only when both Git and native evidence validate."""
    try:
        _require(
            valid=attestation.predicate == "effect:git-ref-update"
            and declares_transition(attestation, "lane.refresh")
        )
        plan = plan_from_attestation(attestation)
        _require(valid=plan.policy.get("transition") == "lane.refresh")
        _require(valid=plan.policy.get("execution_branch") == branch)
        effect = git_effect_from_plan(plan)
        ref = f"refs/heads/{branch}"
        update = effect.updates.get(ref)
        _require(valid=update is not None and len(effect.updates) == 1)
        assert update is not None
        validate_git_effect_attestation(
            root,
            effect,
            attestation,
            issuer=attestation.verifier,
            plan=plan,
            current_postconditions=False,
        )
        carried = plan.prior_attestations.get("rebase")
        _require(valid=isinstance(carried, Mapping))
        rebase = Attestation.model_validate(mutable_json(carried))
        projected_body = mutable_json(rebase.payload.body)
        _require(valid=isinstance(projected_body, dict))
        assert isinstance(projected_body, dict)
        body = {str(key): value for key, value in projected_body.items()}
        before = body.get("input")
        after = body.get("output")
        freshness = body.get("freshness")
        command = body.get("command")
        repository = str(body.get("repository") or "")
        _require(valid=all(isinstance(value, dict) for value in (before, after, freshness)))
        assert isinstance(before, dict)
        assert isinstance(after, dict)
        assert isinstance(freshness, dict)
        _require(valid=isinstance(command, list | tuple) and bool(repository))
        assert isinstance(command, list | tuple)
        before_map = {str(key): value for key, value in before.items()}
        after_map = {str(key): value for key, value in after.items()}
        freshness_map = {str(key): value for key, value in freshness.items()}
        subject = freshness_map.get("subject")
        _require(valid=isinstance(subject, dict))
        assert isinstance(subject, dict)
        subject_map = {str(key): value for key, value in subject.items()}
        expected_rebase = issue_native_effect(
            root,
            effect=NativeEffect(
                predicate="effect:git-rebase",
                operation="git.rebase",
                command=tuple(str(value) for value in command),
                subject=subject_map,
                before=before_map,
                after=after_map,
            ),
            state="applied",
            commitment_digest=None,
            repository_id=repository,
            issued_at=rebase.issued_at,
        )
        candidate_heads = tuple(str(value) for value in effect.assertions.values())
        candidate_head = str(before_map.get("candidate_head") or "")
        _require(valid=rebase.canonical_json() == expected_rebase.canonical_json())
        _require(valid=repository == repository_identity(root, tree_ref=update.desired))
        _require(valid=subject_map == {"branch": branch, "candidate_head": candidate_head})
        _require(valid=before_map.get("branch") == branch)
        _require(valid=before_map.get("head") == update.expected)
        _require(valid=after_map.get("branch") == "detached")
        _require(valid=after_map.get("head") == update.desired)
        _require(valid=candidate_head == after_map.get("candidate_head"))
        _require(valid=candidate_heads == (candidate_head,))
    except (AttributeError, KeyError, TypeError, ValueError):
        return None
    return RewriteEdge(
        previous=str(update.expected),
        current=str(update.desired),
        attestation_id=str(attestation.id),
        kind="refresh",
        candidate=candidate_head,
    )


def _require(*, valid: bool) -> None:
    if not valid:
        message = "git_refresh_evidence_invalid"
        raise ValueError(message)
