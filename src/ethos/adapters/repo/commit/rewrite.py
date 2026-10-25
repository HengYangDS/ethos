"""Verify native commit rewrites and their conserved contribution relationships."""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from pydantic import TypeAdapter

from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.git import is_ancestor
from ethos.adapters.repo.git_effect_attestation import declares_transition
from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_git_effect_attestation
from ethos.adapters.repo.git_object_sandbox import isolated_git_objects
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path

_NATIVE_EFFECT = TypeAdapter(NativeEffect)


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
    observed: dict[str, object] = {"verdict": "unknown", "reason": "native_composition_unavailable"}
    try:
        with isolated_git_objects(root) as git:
            bases = git("merge-base", "--all", edge.previous, edge.candidate)
            if bases.returncode or len(bases.stdout.splitlines()) != 1:
                return {**observed, "reason": "unique_merge_base_unavailable"}
            base = bases.stdout.strip()
            result = git(
                "merge-tree", "--write-tree", f"--merge-base={base}", edge.candidate, edge.previous
            )
            output = git("rev-parse", f"{edge.current}^{{tree}}")
            composition = {
                **observed,
                "base": base,
                "candidate": edge.candidate,
                "previous": edge.previous,
                "output": edge.current,
                "exit_code": result.returncode,
            }
            if result.returncode == 1:
                return {**composition, "verdict": "block", "reason": "native_composition_conflict"}
            if result.returncode or output.returncode:
                return composition
            composed = result.stdout.splitlines()[0] if result.stdout.splitlines() else ""
            expected = output.stdout.strip()
            equal = bool(composed) and composed == expected
            return {
                **composition,
                "verdict": "pass" if equal else "block",
                "reason": "conserved" if equal else "native_composition_mismatch",
                "composed_tree": composed,
                "output_tree": expected,
            }
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        return {**observed, "reason": str(error)}


def validated_refresh_edge(
    root: Path,
    *,
    branch: str,
    attestation: Any,
    previous: str | None = None,
) -> RewriteEdge | None:
    """Decode one refresh edge only when both Git and native evidence validate."""
    try:
        _require(
            valid=attestation.predicate == "effect:git-ref-update"
            and declares_transition(attestation, "lane.refresh")
            and attestation.payload.body["plan"]["policy"].get("execution_branch") == branch
            and (
                previous is None
                or attestation.payload.body["plan"]["effect"]["updates"][f"refs/heads/{branch}"][
                    "expected"
                ]
                == previous
            )
        )
        plan = plan_from_attestation(attestation)
        _require(valid=plan.policy.get("transition") == "lane.refresh")
        effect = git_effect_from_plan(plan)
        ref = f"refs/heads/{branch}"
        update = effect.updates.get(ref)
        _require(valid=update is not None and len(effect.updates) == 1)
        assert update is not None
        _require(valid=previous is None or update.expected == previous)
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
        body = rebase.payload.body
        freshness = body.get("freshness")
        repository = str(body.get("repository") or "")
        _require(valid=isinstance(freshness, Mapping) and bool(repository))
        assert isinstance(freshness, Mapping)
        native = _NATIVE_EFFECT.validate_python(
            {
                "predicate": "effect:git-rebase",
                "operation": "git.rebase",
                "command": body.get("command"),
                "subject": freshness.get("subject"),
                "before": body.get("input"),
                "after": body.get("output"),
            }
        )
        expected_rebase = issue_native_effect(
            root,
            effect=native,
            state="applied",
            commitment_digest=None,
            repository_id=repository,
            issued_at=rebase.issued_at,
        )
        candidate_heads = tuple(str(value) for value in effect.assertions.values())
        candidate_head = str(native.before.get("candidate_head") or "")
        _require(valid=rebase.canonical_json() == expected_rebase.canonical_json())
        _require(valid=repository == repository_identity(root, tree_ref=update.desired))
        _require(valid=native.subject == {"branch": branch, "candidate_head": candidate_head})
        _require(valid=native.before.get("branch") == branch)
        _require(valid=native.before.get("head") == update.expected)
        _require(valid=native.after.get("branch") == "detached")
        _require(valid=native.after.get("head") == update.desired)
        _require(valid=candidate_head == native.after.get("candidate_head"))
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
