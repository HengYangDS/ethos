"""Issue and validate typed evidence for exact Git ref effects."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from typing import NamedTuple

from ethos.adapters.admission.ref_intent import committed_ref_intent
from ethos.adapters.repo.attestation_set import read_attestation_set
from ethos.adapters.repo.attestation_set import record_attestations
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.git import current_tree
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import TransitionPlan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.contracts.semantic import canonical_utc_time
from ethos.contracts.value import mutable_json

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.value import JsonObject


class NativeEffect(NamedTuple):
    """Exact subject and observations for one non-CAS effect."""

    predicate: str
    operation: str
    command: tuple[str, ...]
    subject: JsonObject
    before: JsonObject
    after: JsonObject


def issue_native_effect(
    _root: Path,
    *,
    effect: NativeEffect,
    state: str,
    commitment_digest: str,
    repository_id: str,
    issued_at: datetime | None = None,
) -> Attestation:
    """Issue one digest-bound effect Attestation from exact pre/post facts."""
    payload = effect._asdict()
    effect_digest = canonical_json_digest(payload)
    result = native_effect_result(state)
    issued = issued_at or datetime.now(UTC)
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": effect.predicate,
            "verifier": "git",
            "subject": f"{effect.predicate}:{effect_digest}",
            "issued_at": issued,
            "valid_from": issued,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": "effect:native",
                "body": {
                    "claim": {"operation": effect.operation, "effect": effect_digest},
                    "repository": repository_id,
                    "command": effect.command,
                    "input": effect.before,
                    "result": result,
                    "output": effect.after,
                    "input_digest": canonical_json_digest(effect.before),
                    "output_digest": canonical_json_digest(
                        {"result": result, "output": effect.after}
                    ),
                    "freshness": {
                        "mode": "semantic_scope",
                        "repository": repository_id,
                        "subject": effect.subject,
                        **effect.subject,
                        "output_digest": canonical_json_digest(effect.after),
                    },
                },
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": commitment_digest,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": effect_digest,
            "mints_authority": False,
        }
    )


def native_effect_result(state: str) -> dict[str, object]:
    """Return the canonical result envelope for one native effect state."""
    executed = state in {"applied", "recognized"}
    return {"state": state, "executed": executed, "exit_code": 0 if executed else None}


Evidence = tuple[str, str, dict[str, object], dict[str, object]]
_CONTENT_MISMATCH = "git_effect_attestation_content_mismatch"
_IDENTITY_COLLISION = "git_effect_identity_collision"
_STALE = "git_effect_attestation_stale"


def _statement(attestation: Attestation) -> dict[str, object]:
    projected = mutable_json(attestation.payload.body)
    if not isinstance(projected, dict):
        message = "git_effect_attestation_statement_invalid"
        raise TypeError(message)
    return {str(name): value for name, value in projected.items()}


def _object_mapping(value: object) -> dict[str, object]:
    return {str(name): item for name, item in value.items()} if isinstance(value, Mapping) else {}


def issue(
    effect: GitEffect,
    *,
    plan: TransitionPlan,
    issuer: str,
    evidence: Evidence,
) -> Attestation:
    """Issue one effect-time Attestation from pre/post observations."""
    repository, state, before, after = evidence
    try:
        issued = datetime.fromisoformat(str(after["observed_at"]))
        observed_at = {
            "before": canonical_utc_time(datetime.fromisoformat(str(before["observed_at"]))),
            "after": canonical_utc_time(issued),
        }
    except ValueError:
        raise ValueError(_CONTENT_MISMATCH) from None
    input_observation = {name: before[name] for name in ("head", "tree", "refs", "assertions")}
    output_observation = {name: after[name] for name in ("head", "tree", "refs")}
    result = {
        "state": state,
        "executed": state == "applied",
        "exit_code": 0 if state == "applied" else None,
        "refs": output_observation["refs"],
    }
    effect_digest = effect.digest()
    subject = f"git-effect:{effect_digest}"
    inputs = {
        "commitment": plan.inputs.commitment,
        "facts": plan.inputs.facts,
        "prior_attestations": plan.inputs.prior_attestations,
        "plan": plan.digest,
        "policy": plan.inputs.policy,
        "effect": effect_digest,
    }
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "effect:git-ref-update",
            "verifier": issuer,
            "subject": subject,
            "issued_at": issued,
            "valid_from": issued,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": "effect:git-ref-update",
                "body": {
                    "claim": {"operation": "git.ref.compare-and-swap", "effect": subject},
                    "repository": repository,
                    "command": ("git", "update-ref", "--stdin", "-z"),
                    "program_sha256": effect_digest,
                    "plan": plan.model_dump(mode="json"),
                    "effect": effect.model_dump(mode="json"),
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
                        "before": observed_at["before"],
                        "after": observed_at["after"],
                    },
                    "freshness": {
                        "mode": "semantic_scope",
                        "repository": repository,
                        **output_observation,
                    },
                },
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (),
            "commitment_digest": plan.inputs.commitment,
            "facts_digest": plan.inputs.facts,
            "plan_digest": plan.digest,
            "policy_digest": plan.inputs.policy,
            "effect_digest": effect_digest,
            "mints_authority": False,
        }
    )


def validate(
    root: Path,
    effect: GitEffect,
    attestation: Attestation,
    *,
    issuer: str,
    plan: TransitionPlan,
    environment: Mapping[str, str] | None = None,
    current_postconditions: bool = True,
) -> None:
    """Validate immutable typed evidence, validity, and current postconditions."""
    if git_effect_from_plan(plan) != effect:
        raise ValueError(_CONTENT_MISMATCH)
    statement = _statement(attestation)
    subject = f"git-effect:{effect.digest()}"
    if (
        attestation.predicate != "effect:git-ref-update"
        or attestation.subject != subject
        or attestation.plan_digest != plan.digest
        or attestation.effect_digest != effect.digest()
    ):
        raise ValueError(_IDENTITY_COLLISION)
    binding_mismatch = next(
        (
            name
            for name, expected in (
                ("commitment_digest", plan.inputs.commitment),
                ("facts_digest", plan.inputs.facts),
                ("policy_digest", plan.inputs.policy),
            )
            if getattr(attestation, name) != expected
        ),
        "",
    )
    if binding_mismatch:
        message = f"git_effect_attestation_binding_mismatch:{binding_mismatch}"
        raise ValueError(message)
    if attestation.verdict != "pass":
        message = f"git_effect_attestation_verdict_{attestation.verdict}"
        raise ValueError(message)
    before = _object_mapping(statement.get("input"))
    process = _object_mapping(statement.get("result"))
    after = _object_mapping(statement.get("output"))
    observed_at = _object_mapping(statement.get("observed_at"))
    state = str(process.get("state") or "")
    try:
        datetime.fromisoformat(str(observed_at["after"]))
    except (KeyError, ValueError):
        raise ValueError(_CONTENT_MISMATCH) from None
    now = datetime.now(UTC)
    if (attestation.valid_from and now < attestation.valid_from) or (
        attestation.valid_until and now > attestation.valid_until
    ):
        raise ValueError(_STALE)
    allow_missing_prestate = plan.policy.get("repository_commitment_bootstrap") is True
    repository = resolve_git_effect_repository(
        root,
        effect,
        before,
        environment=environment,
        allow_missing_prestate=allow_missing_prestate,
        prestate_repository_id=str(plan.policy.get("prestate_repository_id") or ""),
        prestate_repository_bytes_sha256=str(
            plan.policy.get("prestate_repository_bytes_sha256") or ""
        ),
    )
    evidence = (
        repository,
        state,
        before | {"observed_at": observed_at.get("before")},
        after | {"observed_at": observed_at.get("after")},
    )
    expected = issue(effect, plan=plan, issuer=issuer, evidence=evidence)
    if (
        state not in {"applied", "recovered"}
        or attestation.canonical_json() != expected.canonical_json()
    ):
        raise ValueError(_CONTENT_MISMATCH)
    if current_postconditions and not _matches(
        root,
        effect,
        evidence,
        observed_at,
        _object_mapping(statement.get("freshness")),
        plan=plan,
        environment=environment,
        allow_missing_prestate=allow_missing_prestate,
    ):
        raise ValueError(_CONTENT_MISMATCH)


def plan_from_attestation(attestation: Attestation) -> TransitionPlan:
    """Return the exact TransitionPlan carried by one Git effect Attestation."""
    statement = _statement(attestation)
    try:
        plan = TransitionPlan.model_validate(statement["plan"])
        git_effect_from_plan(plan)
    except (KeyError, TypeError, ValueError) as error:
        message = "git_effect_attestation_plan_invalid"
        raise ValueError(message) from error
    return plan


def _matching_plan_attestations(root: Path, plan_digest: str) -> tuple[Attestation, ...]:
    try:
        _root_identity, members = read_attestation_set(root)
    except ValueError as error:
        message = "git_effect_attestation_invalid"
        raise ValueError(message) from error
    matches = tuple(
        attestation
        for attestation in members
        if attestation.predicate == "effect:git-ref-update"
        and attestation.plan_digest == plan_digest
    )
    if len(matches) > 1:
        message = "git_effect_attestation_collision"
        raise ValueError(message)
    return matches


def validated_plan_attestation(
    root: Path,
    plan_digest: str,
    *,
    issuer: str,
    environment: Mapping[str, str] | None = None,
) -> tuple[TransitionPlan, Attestation] | None:
    """Return the sole validated plan and its exact Git-effect Attestation."""
    matches = _matching_plan_attestations(root, plan_digest)
    if not matches:
        return None
    attestation = matches[0]
    if attestation.verifier != issuer:
        raise ValueError(_CONTENT_MISMATCH)
    plan = plan_from_attestation(attestation)
    validate(
        root,
        git_effect_from_plan(plan),
        attestation,
        issuer=issuer,
        plan=plan,
        environment=environment,
        current_postconditions=False,
    )
    return plan, attestation


def recover_plan(
    root: Path,
    *,
    operation: str,
    desired: str,
    ref_name: str = "",
    assertions: Mapping[str, str] | None = None,
) -> TransitionPlan | None:
    """Return the sole attested plan bound to one committed ref intent."""
    intent = committed_ref_intent(
        root=root,
        operation=operation,
        desired=desired,
        ref_name=ref_name,
    )
    gap = str(intent["gap"] or "")
    if gap == "ref_intent_missing":
        return None
    if gap:
        raise ValueError(
            "git_effect_recovery_ambiguous"
            if gap == "ref_intent_ambiguous"
            else "git_effect_recovery_unproven"
        )
    digest = str(intent["plan_digest"])
    try:
        attestation = next(iter(_matching_plan_attestations(root, digest)))
        plan = plan_from_attestation(attestation)
        validate(
            root,
            git_effect_from_plan(plan),
            attestation,
            issuer=attestation.verifier,
            plan=plan,
        )
        effect = git_effect_from_plan(plan)
        update = effect.updates.get(str(intent["ref_name"]))
    except (StopIteration, ValueError) as error:
        msg = "git_effect_recovery_unproven"
        raise ValueError(msg) from error
    if (
        plan.digest != digest
        or attestation.plan_digest != digest
        or (plan.policy.get("transition") or plan.policy.get("operation")) != operation
        or update is None
        or update.expected != intent["old_value"]
        or update.desired != desired
        or (assertions is not None and effect.assertions != assertions)
    ):
        msg = "git_effect_recovery_unproven"
        raise ValueError(msg)
    return plan


def records(
    root: Path,
    plan: TransitionPlan,
    record: Attestation | None = None,
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[Attestation, ...]:
    """Read or atomically persist the sole Attestation for one exact plan."""
    effect = git_effect_from_plan(plan)
    if record is None:
        existing = _matching_plan_attestations(root, plan.digest)
        if not existing:
            return ()
        plan_from_attestation(existing[0])
        if git_effect_from_plan(plan_from_attestation(existing[0])) != effect:
            message = "git_effect_attestation_collision"
            raise ValueError(message)
        return existing
    plan_from_attestation(record)
    validate(root, effect, record, issuer=record.verifier, plan=plan, environment=environment)
    existing = _matching_plan_attestations(root, plan.digest)
    if existing:
        if existing[0].canonical_json() != record.canonical_json():
            message = "git_effect_attestation_collision"
            raise ValueError(message)
        return existing
    try:
        record_attestations(root, (record,))
    except ValueError as error:
        if str(error).startswith("attestation_set_identity_collision:"):
            message = "git_effect_attestation_collision"
            raise ValueError(message) from error
        raise
    return _matching_plan_attestations(root, plan.digest)


def _matches(
    root: Path,
    effect: GitEffect,
    evidence: Evidence,
    observed_at: dict[str, object],
    freshness: dict[str, object],
    *,
    plan: TransitionPlan,
    environment: Mapping[str, str] | None = None,
    allow_missing_prestate: bool = False,
) -> bool:
    repository, state, before, after = evidence
    current_refs = {
        name: ref_head(root, name, update.desired, environment=environment)
        for name, update in effect.updates.items()
    }
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
    try:
        repository_matches = repository == resolve_git_effect_repository(
            root,
            effect,
            before,
            environment=environment,
            allow_missing_prestate=allow_missing_prestate,
            prestate_repository_id=str(plan.policy.get("prestate_repository_id") or ""),
            prestate_repository_bytes_sha256=str(
                plan.policy.get("prestate_repository_bytes_sha256") or ""
            ),
        )
    except ValueError:
        return False
    return bool(
        repository_matches
        and current_refs == desired
        and before.get("refs") == expected_before
        and before.get("assertions") == effect.assertions
        and before.get("tree")
        == current_tree(root, str(before.get("head") or ""), environment=environment)
        and after.get("refs") == desired
        and after.get("tree")
        == current_tree(root, str(after.get("head") or ""), environment=environment)
        and (
            current_head == after.get("head")
            or (
                state == "applied"
                and before.get("head") == current_head
                and current_tree(root, current_head, environment=environment) == before.get("tree")
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
