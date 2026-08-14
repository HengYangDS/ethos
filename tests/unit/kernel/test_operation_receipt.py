from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from ethos.contracts.operation import AuthorityRule
from ethos.contracts.operation import OperationAction
from ethos.contracts.operation import OperationContinuation
from ethos.contracts.operation import OperationDeclaration
from ethos.contracts.operation import OperationRequest
from ethos.contracts.operation import OperationResult
from ethos.contracts.operation import TransitionReceipt
from ethos.contracts.operation import reduce_operation
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts


def _commitment() -> Commitment:
    return Commitment(
        id="change:model-promotion",
        intent="Promote one terminal transaction model.",
        subjects=("repository:ethos",),
        scope=("src/**",),
        authority_refs=("system/operations/refresh-base.toml",),
    )


def _facts(*, head: str = "a" * 40) -> Facts:
    return Facts(
        repository="repository:ethos",
        head=head,
        tree="b" * 40,
        observed_at=datetime(2026, 8, 14, tzinfo=UTC),
        values={
            "holder": "agent:codex:task:model-promotion",
            "lease_head": head,
            "refs": {"refs/heads/work/model-promotion": head},
        },
    )


def _request() -> OperationRequest:
    return OperationRequest(
        operation="lane.refresh-base",
        repository="repository:ethos",
        subject="change:model-promotion",
        actor="agent:codex:task:model-promotion",
        coordinates={
            "branch": "work/model-promotion",
            "expected_head": "a" * 40,
            "candidate_head": "c" * 40,
        },
        effect={
            "kind": "git-ref-cas",
            "ref": "refs/heads/work/model-promotion",
            "expected": "a" * 40,
            "desired": "d" * 40,
        },
    )


def _declaration() -> OperationDeclaration:
    return OperationDeclaration(
        id="operation:lane.refresh-base",
        operation="lane.refresh-base",
        source_ref="system/operations/refresh-base.toml",
        authority_rules=(
            AuthorityRule(
                id="actor-is-holder",
                expression="facts.holder == rule.actor",
                gap="operation_actor_not_holder",
            ),
            AuthorityRule(
                id="lease-head-is-current",
                expression="facts.lease_head == rule.expected_head",
                gap="operation_lease_head_stale",
            ),
        ),
        preconditions=(
            OperationAction(
                id="observe-prestate",
                adapter="repository.observe",
                payload={"branch": "work/model-promotion"},
            ),
        ),
        effects=(
            OperationAction(
                id="advance-ref",
                adapter="git.ref.compare-and-swap",
                payload={"from_request": "effect"},
            ),
        ),
        compensations=(
            OperationAction(
                id="restore-ref",
                adapter="git.ref.compare-and-swap",
                payload={"direction": "reverse"},
            ),
        ),
        postconditions=(
            OperationAction(
                id="observe-poststate",
                adapter="repository.observe",
                payload={"required": ("ref", "lease", "attachment", "attestation")},
            ),
        ),
        blocked=OperationContinuation(
            kind="user-decision",
            command=("ethos", "lane", "recover", "derive"),
        ),
    )


def _receipt(*, facts: Facts | None = None) -> TransitionReceipt:
    return reduce_operation(
        request=_request(),
        commitment=_commitment(),
        facts=facts or _facts(),
        prior_attestations={},
        declaration=_declaration(),
    )


def test_operation_reducer_is_pure_deterministic_and_input_sensitive() -> None:
    first = _receipt()
    repeated = _receipt()
    changed = _receipt(facts=_facts(head="e" * 40))

    assert first == repeated
    assert first.canonical_json() == repeated.canonical_json()
    assert first.digest == repeated.digest
    assert changed.digest != first.digest
    assert (first.verdict, first.required_gaps, first.continuation) == ("pass", (), None)
    assert first.authority.effect_digest == first.inputs.effect
    assert first.authority.actor == _request().actor


def test_operation_reducer_blocks_with_one_declared_continuation() -> None:
    request = _request().model_copy(update={"actor": "agent:other"})
    receipt = reduce_operation(
        request=request,
        commitment=_commitment(),
        facts=_facts(),
        prior_attestations={},
        declaration=_declaration(),
    )

    assert receipt.verdict == "block"
    assert receipt.required_gaps == ("operation_actor_not_holder",)
    assert receipt.continuation == _declaration().blocked
    assert receipt.effects == _declaration().effects


def test_transition_receipt_rejects_changed_noncanonical_bytes() -> None:
    receipt = _receipt()
    payload = receipt.model_dump(mode="json")
    payload["request"]["coordinates"]["candidate_head"] = "f" * 40

    with pytest.raises(ValidationError, match="transition_receipt_digest_mismatch"):
        TransitionReceipt.model_validate_json(json.dumps(payload))

    payload = receipt.model_dump(mode="json")
    payload["required_gaps"] = ["z", "a", "z"]
    payload["verdict"] = "block"
    payload["continuation"] = _declaration().blocked.model_dump(mode="json")
    with pytest.raises(ValidationError, match="transition_receipt_gaps_not_canonical"):
        TransitionReceipt.model_validate(payload)


def test_operation_result_is_closed_and_partial_has_one_continuation() -> None:
    receipt = _receipt()
    continuation = OperationContinuation(
        kind="resume",
        command=("ethos", "operation", "resume", "--receipt", receipt.digest),
    )
    partial = OperationResult(
        verdict="block",
        state="partial",
        required_gaps=("lease_projection_incomplete",),
        receipt_digest=receipt.digest,
        continuation=continuation,
    )
    assert partial.continuation == continuation

    with pytest.raises(ValidationError, match="operation_result_partial_continuation_missing"):
        OperationResult(
            verdict="block",
            state="partial",
            required_gaps=("lease_projection_incomplete",),
            receipt_digest=receipt.digest,
        )

    with pytest.raises(ValidationError, match="operation_result_terminal_attestation_missing"):
        OperationResult(
            verdict="pass",
            state="done",
            required_gaps=(),
            receipt_digest=receipt.digest,
        )
