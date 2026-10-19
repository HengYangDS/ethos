"""Publication values bind selected objects, independent targets and exact CAS."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest

from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import PublicationSource
from ethos.contracts.publication import PublicationTarget
from ethos.contracts.publication import PublicationUpdate
from ethos.contracts.publication import compile_publication_plan
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest


def _publication_source(kind: str = "commit") -> PublicationSource:
    return PublicationSource(
        kind=kind,
        object_oid="1" * 40,
        peeled_commit="2" * 40 if kind == "annotated-tag" else "1" * 40,
        tree_oid="3" * 40,
        signature={
            "verdict": "pass",
            "principal": "release@example.invalid",
            "fingerprint": "SHA256:" + "A" * 43,
            "trust_anchor_sha256": "4" * 64,
            "verifier": "git verify-tag" if kind == "annotated-tag" else "git verify-commit",
            "verifier_version": "git version 2.55.0",
        },
    )


def _update(
    target_ref: str = "refs/heads/dev", expected: str = "0" * 40, desired: str = "1" * 40
) -> PublicationUpdate:
    """Name one exact full-ref CAS; the default projects the commit source onto dev."""
    return PublicationUpdate(target_ref=target_ref, expected=expected, desired=desired)


def _retirement(width: int = 40) -> PublicationUpdate:
    """Name the exact absence of a finished proposal ref."""
    return _update("refs/heads/proposal/finished", "2" * width, "0" * width)


def _effect(
    *updates: PublicationUpdate, source: PublicationSource | None = None
) -> PublicationEffect:
    """Compile one origin peer transaction through the admitted constructor."""
    target = PublicationTarget(id="peer", remote="origin", updates=updates)
    source = source or _publication_source()
    return PublicationEffect.compile(
        repository_common_dir="/repo/.git", source=source, targets=(target,)
    )


def test_publication_effect_owns_exact_full_ref_cas() -> None:
    """A signed annotated tag projects one exact full-ref CAS onto its peer."""
    update = _update("refs/tags/v1.2.3")
    effect = _effect(update, source=_publication_source("annotated-tag"))

    assert effect.operation == "git.ref.compare-and-swap"
    assert effect.source.object_oid == "1" * 40
    assert effect.targets == (PublicationTarget(id="peer", remote="origin", updates=(update,)),)


@pytest.mark.parametrize("width", [40, 64])
def test_publication_effect_represents_retirement_without_a_second_transaction(width: int) -> None:
    """An accepted source can authorize exact absence rather than project itself."""
    source = _publication_source().model_copy(
        update={"object_oid": "1" * width, "peeled_commit": "1" * width, "tree_oid": "3" * width}
    )
    effect = _effect(_retirement(width), source=source)

    assert effect.operation == "git.ref.compare-and-swap"
    assert effect.retirement is True
    assert effect.targets[0].updates[0].deletion is True


@pytest.mark.parametrize(
    ("updates", "error"),
    [
        ((_retirement(), _update(expected="2" * 40)), "publication_mixed_retirement_projection"),
        ((_update(), _update("refs/tags/v1.0.0")), "publication_target_ref_kind_mismatch"),
    ],
)
def test_publication_effect_does_not_mix_retirement_projection_or_ref_kinds(
    updates: tuple[PublicationUpdate, ...], error: str
) -> None:
    """Different authority obligations cannot hide behind one compiled source projection."""
    with pytest.raises(ValueError, match=error):
        _effect(*updates)


@pytest.mark.parametrize(
    ("updates", "peers", "error"),
    [
        ((_update(), _update()), 1, "publication_target_ref_duplicate"),
        ((_update(desired="2" * 40),), 1, "publication_target_source_mismatch"),
        ((_update("refs/tags/v1.0.0"),), 1, "publication_target_source_kind_mismatch"),
        ((_update(),), 2, "publication_target_duplicate"),
    ],
)
def test_publication_effect_rejects_duplicate_or_source_inconsistent_updates(
    updates: tuple[PublicationUpdate, ...], peers: int, error: str
) -> None:
    """Reject duplicate refs or peers and updates that do not project the selected source."""
    target = PublicationTarget.model_construct(id="peer", remote="origin", updates=updates)
    with pytest.raises(ValueError, match=error):
        PublicationEffect(
            repository_common_dir="/repo/.git",
            source=_publication_source(),
            targets=(target,) * peers,
        )


def test_publication_plan_round_trips_and_rejects_nonadmitted_or_drifted_effect() -> None:
    """Only an admitted plan with its exact policy yields the compiled effect."""
    effect = _effect(_update())
    at = datetime(2026, 8, 29, tzinfo=UTC)
    facts = Facts(
        repository="repository:sample", head="0" * 40, tree="2" * 40, observed_at=at, values={}
    )
    plan = compile_publication_plan(
        commitment=None, facts=facts, effect=effect, prior_attestations={}
    )
    assert publication_effect_from_plan(plan) == effect

    closure = {
        "commitment": plan.commitment,
        "prior_attestations": plan.prior_attestations,
        "policy": plan.policy,
        "effect": plan.effect,
    }
    with pytest.raises(ValueError, match="publication_plan_not_admitted"):
        publication_effect_from_plan(
            type(plan).compile(inputs=plan.inputs, closure=closure, facts=plan.facts)
        )
    drifted_policy = {**plan.policy, "operation": "git.ref.unadmitted"}
    inputs = plan.inputs.model_copy(update={"policy": canonical_json_digest(drifted_policy)})
    drifted = {**closure, "policy": drifted_policy}
    with pytest.raises(ValueError, match="publication_plan_mismatch"):
        publication_effect_from_plan(
            type(plan).compile(inputs=inputs, closure=drifted, facts=plan.facts, nodes=plan.nodes)
        )
