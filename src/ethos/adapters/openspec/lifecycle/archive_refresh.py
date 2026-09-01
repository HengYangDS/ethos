"""Validate exact Work Lane refresh edges for archived OpenSpec intent."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING
from typing import Any
from typing import NamedTuple

from ethos.adapters.repo.git_effect_attestation import plan_from_attestation
from ethos.adapters.repo.git_effect_attestation import validate as validate_git_effect_attestation
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.adapters.repo.profile import repository_identity
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path


class RefreshEdge(NamedTuple):
    """One exact Work Lane head rewrite proven by refresh evidence."""

    previous: str
    current: str
    attestation_id: str


def validated_refresh_edge(
    root: Path,
    *,
    branch: str,
    attestation: Any,
) -> RefreshEdge | None:
    """Decode one refresh edge only when both Git and native evidence validate."""
    try:
        _require(valid=attestation.predicate == "effect:git-ref-update")
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
    return RefreshEdge(
        previous=str(update.expected),
        current=str(update.desired),
        attestation_id=str(attestation.id),
    )


def _require(*, valid: bool) -> None:
    if not valid:
        message = "archive_refresh_evidence_invalid"
        raise ValueError(message)
