"""Issue and validate typed evidence for exact Git ref effects."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import git_stdout
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.plan import GitEffect

Evidence = tuple[str, str, dict[str, object], dict[str, object]]
_CONTENT_MISMATCH = "git_effect_attestation_content_mismatch"
_IDENTITY_COLLISION = "git_effect_identity_collision"
_STALE = "git_effect_attestation_stale"


def transaction_program(effect: GitEffect) -> str:
    """Render the exact deterministic update-ref transaction program."""
    return "\0".join(
        (
            "start",
            *(
                token
                for ref in sorted(effect.assertions)
                for token in (
                    f"update {ref}",
                    effect.assertions[ref],
                    effect.assertions[ref],
                )
            ),
            *(
                token
                for ref in sorted(effect.updates)
                for token in (
                    f"update {ref}",
                    effect.updates[ref].desired,
                    effect.updates[ref].expected,
                )
            ),
            "prepare",
            "commit",
            "",
        )
    )


def program_digest(effect: GitEffect) -> str:
    """Digest the exact transaction bytes bound by the Attestation."""
    return hashlib.sha256(transaction_program(effect).encode()).hexdigest()


def issue(
    effect: GitEffect,
    *,
    issuer: str,
    evidence: Evidence,
    commitment_digest: str,
    facts_digest: str,
    policy_digest: str,
) -> Attestation:
    """Issue one effect-time Attestation from pre/post observations."""
    repository, state, before, after = evidence
    issued = datetime.fromisoformat(str(after["observed_at"]))
    input_observation = {name: before[name] for name in ("head", "tree", "refs", "assertions")}
    output_observation = {name: after[name] for name in ("head", "tree", "refs")}
    result = _result(state, output_observation["refs"])
    inputs = {
        "commitment": commitment_digest,
        "facts": facts_digest,
        "plan": effect.plan_digest,
        "policy": policy_digest,
        "effect": effect.digest(),
    }
    return Attestation.issue(
        {
            "predicate": "effect:git-ref-update",
            "verifier": issuer,
            "subject": effect.id,
            "issued_at": issued,
            "valid_from": issued,
            "verdict": "pass",
            "commitment_digest": commitment_digest,
            "facts_digest": facts_digest,
            "plan_digest": effect.plan_digest,
            "policy_digest": policy_digest,
            "effect_digest": effect.digest(),
            "statement": {
                "claim": {"operation": "git.ref.compare-and-swap", "effect": effect.id},
                "repository": repository,
                "command": ("git", "update-ref", "--stdin", "-z"),
                "program_sha256": program_digest(effect),
                "input": input_observation,
                "result": result,
                "output": output_observation,
                "inputs": inputs,
                "input_digest": canonical_json_digest(
                    {"input": input_observation, "inputs": inputs}
                ),
                "output_digest": canonical_json_digest(
                    {"result": result, "output": output_observation}
                ),
                "observed_at": {
                    "before": before["observed_at"],
                    "after": after["observed_at"],
                },
                "freshness": {
                    "mode": "semantic_scope",
                    "repository": repository,
                    **output_observation,
                },
            },
        }
    )


def validate(
    root: Path,
    effect: GitEffect,
    attestation: Attestation,
    *,
    issuer: str,
    bindings: tuple[str, str, str],
) -> None:
    """Validate immutable typed evidence, validity, and current postconditions."""
    if (
        attestation.predicate != "effect:git-ref-update"
        or attestation.subject != effect.id
        or attestation.plan_digest != effect.plan_digest
        or attestation.effect_digest != effect.digest()
    ):
        raise ValueError(_IDENTITY_COLLISION)
    for name, expected in zip(
        ("commitment_digest", "facts_digest", "policy_digest"), bindings, strict=True
    ):
        if getattr(attestation, name) != expected:
            message = f"git_effect_attestation_binding_mismatch:{name}"
            raise ValueError(message)
    if attestation.verdict != "pass":
        message = f"git_effect_attestation_verdict_{attestation.verdict}"
        raise ValueError(message)
    statement = attestation.statement
    if statement.get("program_sha256") != program_digest(effect):
        raise ValueError(_CONTENT_MISMATCH)
    commitment_digest, facts_digest, policy_digest = bindings
    before, process, after = (
        statement.get("input"),
        statement.get("result"),
        statement.get("output"),
    )
    state = process.get("state") if isinstance(process, Mapping) else None
    inputs = {
        "commitment": commitment_digest,
        "facts": facts_digest,
        "plan": effect.plan_digest,
        "policy": policy_digest,
        "effect": effect.digest(),
    }
    result = _result(state, after.get("refs") if isinstance(after, Mapping) else {})
    repository = _repository_identity(root, before, after)
    expected = {
        "claim": {"operation": "git.ref.compare-and-swap", "effect": effect.id},
        "repository": repository,
        "command": ("git", "update-ref", "--stdin", "-z"),
        "program_sha256": statement.get("program_sha256"),
        "input": before,
        "result": result,
        "output": after,
        "inputs": inputs,
        "input_digest": canonical_json_digest({"input": before, "inputs": inputs}),
        "output_digest": canonical_json_digest({"result": result, "output": after}),
        "observed_at": statement.get("observed_at"),
        "freshness": statement.get("freshness"),
    }
    observed_at = statement.get("observed_at")
    try:
        observed_after = (
            datetime.fromisoformat(str(observed_at.get("after")))
            if isinstance(observed_at, Mapping)
            else None
        )
    except ValueError:
        observed_after = None
    now = datetime.now(UTC)
    if (attestation.valid_from and now < attestation.valid_from) or (
        attestation.valid_until and now > attestation.valid_until
    ):
        raise ValueError(_STALE)
    if (
        state not in {"applied", "recovered"}
        or attestation.verifier != issuer
        or attestation.issued_at != observed_after
        or attestation.valid_from != observed_after
        or any(statement.get(name) != value for name, value in expected.items())
    ):
        raise ValueError(_CONTENT_MISMATCH)
    evidence: Evidence = (
        str(repository),
        str(state),
        dict(before) if isinstance(before, Mapping) else {},
        dict(after) if isinstance(after, Mapping) else {},
    )
    if not _matches(
        root,
        effect,
        evidence,
        dict(statement["observed_at"]) if isinstance(statement["observed_at"], Mapping) else {},
        dict(statement["freshness"]) if isinstance(statement["freshness"], Mapping) else {},
    ):
        raise ValueError(_CONTENT_MISMATCH)


def _result(state: object, refs: object) -> dict[str, object]:
    return {
        "state": state,
        "executed": True if state == "applied" else False if state == "recovered" else None,
        "exit_code": 0 if state == "applied" else None,
        "refs": refs,
    }


def _repository_identity(root: Path, before: object, after: object) -> str:
    if not isinstance(before, Mapping) or not isinstance(after, Mapping):
        return ""
    try:
        identities = {
            load_repository_commitment(root, tree_ref=str(observation.get("head") or "")).id
            for observation in (before, after)
        }
    except ValueError:
        return ""
    return identities.pop() if len(identities) == 1 else ""


def _matches(
    root: Path,
    effect: GitEffect,
    evidence: Evidence,
    observed_at: dict[str, object],
    freshness: dict[str, object],
) -> bool:
    repository, state, before, after = evidence
    current_refs = {ref: _ref(root, ref) for ref in effect.updates}
    expected_before = {ref: update.expected for ref, update in effect.updates.items()}
    desired = {ref: update.desired for ref, update in effect.updates.items()}
    if state == "recovered":
        expected_before = desired
    before_time = observed_at.get("before")
    after_time = observed_at.get("after")
    try:
        if not (
            isinstance(before_time, str)
            and isinstance(after_time, str)
            and datetime.fromisoformat(before_time) <= datetime.fromisoformat(after_time)
        ):
            return False
    except ValueError:
        return False
    current_head = current_tracked_head(root)
    return bool(
        repository == _repository_identity(root, before, after)
        and current_refs == desired
        and before.get("refs") == expected_before
        and before.get("assertions") == effect.assertions
        and before.get("tree") == current_tree(root, str(before.get("head") or ""))
        and after.get("refs") == desired
        and after.get("tree") == current_tree(root, str(after.get("head") or ""))
        and (
            current_head == after.get("head")
            or (
                state == "applied"
                and before.get("head") == current_head
                and current_tree(root, current_head) == before.get("tree")
            )
        )
        and freshness
        == {
            "mode": "semantic_scope",
            "repository": repository,
            "head": after.get("head"),
            "tree": after.get("tree"),
            "refs": desired,
        }
    )


def _ref(root: Path, ref: str) -> str:
    return git_stdout(root, "rev-parse", "--verify", ref)
