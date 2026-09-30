"""Publication values bind selected objects, independent targets and exact CAS."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from functools import partial

import pytest

from ethos.contracts.publication import PublicationEffect
from ethos.contracts.publication import PublicationSource
from ethos.contracts.publication import PublicationTarget
from ethos.contracts.publication import PublicationUpdate
from ethos.contracts.publication import compile_publication_plan
from ethos.contracts.publication import publication_effect_from_plan
from ethos.contracts.semantic import Facts
from ethos.contracts.semantic import canonical_json_digest

_update = partial(
    PublicationUpdate,
    target_ref="refs/heads/dev",
    expected="0" * 40,
    desired="1" * 40,
)


def test_publication_effect_owns_exact_full_ref_cas() -> None:
    target = PublicationTarget(
        id="gitlab",
        remote="origin",
        updates=(_update(target_ref="refs/tags/v1.2.3"),),
    )

    effect = PublicationEffect.compile(
        repository_common_dir="/repo/.git",
        source=PublicationSource(
            kind="annotated-tag",
            object_oid="1" * 40,
            peeled_commit="2" * 40,
            tree_oid="3" * 40,
            signature={
                "verdict": "pass",
                "principal": "release@example.invalid",
                "fingerprint": "SHA256:" + "A" * 43,
                "trust_anchor_sha256": "4" * 64,
                "verifier": "git verify-tag",
                "verifier_version": "git version 2.55.0",
            },
        ),
        targets=(target,),
    )

    assert effect.operation == "git.ref.compare-and-swap"
    assert effect.source.object_oid == "1" * 40
    assert effect.targets == (target,)


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


@pytest.mark.parametrize("width", [40, 64])
def test_publication_effect_represents_retirement_without_a_second_transaction(width: int) -> None:
    """An accepted source can authorize exact absence rather than project itself."""
    source = _publication_source().model_copy(
        update={"object_oid": "1" * width, "peeled_commit": "1" * width, "tree_oid": "3" * width}
    )
    update = _update(
        target_ref="refs/heads/proposal/finished", expected="2" * width, desired="0" * width
    )
    effect = PublicationEffect.compile(
        repository_common_dir="/repo/.git",
        source=source,
        targets=(PublicationTarget(id="peer", remote="origin", updates=(update,)),),
    )

    assert effect.operation == "git.ref.compare-and-swap"
    assert effect.retirement is True
    assert effect.targets[0].updates[0].deletion is True


@pytest.mark.parametrize(
    ("method", "target_id", "updates", "raw_target", "target_count", "error"),
    [
        pytest.param(
            "compile",
            "peer",
            (
                _update(
                    target_ref="refs/heads/proposal/finished", expected="2" * 40, desired="0" * 40
                ),
                _update(expected="2" * 40),
            ),
            False,
            1,
            "publication_mixed_retirement_projection",
            id="mixed-retirement-projection",
        ),
        pytest.param(
            "construct",
            "peer",
            (_update(), _update()),
            True,
            1,
            "publication_target_ref_duplicate",
            id="duplicate-target-ref",
        ),
        pytest.param(
            "construct",
            "peer",
            (_update(desired="2" * 40),),
            True,
            1,
            "publication_target_source_mismatch",
            id="source-object-mismatch",
        ),
        pytest.param(
            "construct",
            "peer",
            (_update(target_ref="refs/tags/v1.0.0"),),
            True,
            1,
            "publication_target_source_kind_mismatch",
            id="source-kind-mismatch",
        ),
        pytest.param(
            "construct",
            "peer",
            (_update(),),
            False,
            2,
            "publication_target_duplicate",
            id="duplicate-peer",
        ),
        pytest.param(
            "compile",
            "mixed",
            (_update(), _update(target_ref="refs/tags/v1.0.0")),
            False,
            1,
            "publication_target_ref_kind_mismatch",
            id="mixed-ref-kinds",
        ),
    ],
)
def test_publication_effect_rejects_inconsistent_target_relations(
    method: str,
    target_id: str,
    updates: tuple[PublicationUpdate, ...],
    *,
    raw_target: bool,
    target_count: int,
    error: str,
) -> None:
    """Source, target, peer and retirement relations share one refusal law."""
    target_factory = PublicationTarget.model_construct if raw_target else PublicationTarget
    target = target_factory(id=target_id, remote="origin", updates=updates)
    effect_factory = PublicationEffect.compile if method == "compile" else PublicationEffect
    with pytest.raises(ValueError, match=error):
        effect_factory(
            repository_common_dir="/repo/.git",
            source=_publication_source(),
            targets=(target,) * target_count,
        )


def test_publication_plan_round_trips_and_rejects_nonadmitted_or_drifted_effect() -> None:
    effect = PublicationEffect.compile(
        repository_common_dir="/repo/.git",
        source=_publication_source(),
        targets=(
            PublicationTarget(
                id="peer",
                remote="origin",
                updates=(_update(),),
            ),
        ),
    )
    facts = Facts(
        repository="repository:sample",
        head="0" * 40,
        tree="2" * 40,
        observed_at=datetime(2026, 8, 29, tzinfo=UTC),
        values={},
    )
    plan = compile_publication_plan(
        commitment=None,
        facts=facts,
        effect=effect,
        prior_attestations={},
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
    with pytest.raises(ValueError, match="publication_plan_mismatch"):
        publication_effect_from_plan(
            type(plan).compile(
                inputs=plan.inputs.model_copy(
                    update={"policy": canonical_json_digest(drifted_policy)}
                ),
                closure={**closure, "policy": drifted_policy},
                facts=plan.facts,
                nodes=plan.nodes,
            )
        )
