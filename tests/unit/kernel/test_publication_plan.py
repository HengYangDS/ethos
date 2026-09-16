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


def test_publication_effect_owns_exact_full_ref_cas() -> None:
    target = PublicationTarget(
        id="gitlab",
        remote="origin",
        updates=(
            PublicationUpdate(
                target_ref="refs/tags/v1.2.3",
                expected="0" * 40,
                desired="1" * 40,
            ),
        ),
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
    update = PublicationUpdate(
        target_ref="refs/heads/proposal/finished",
        expected="2" * width,
        desired="0" * width,
    )
    effect = PublicationEffect.compile(
        repository_common_dir="/repo/.git",
        source=source,
        targets=(PublicationTarget(id="peer", remote="origin", updates=(update,)),),
    )

    assert effect.operation == "git.ref.compare-and-swap"
    assert effect.retirement is True
    assert effect.targets[0].updates[0].deletion is True


def test_publication_effect_does_not_mix_retirement_and_projection() -> None:
    """Different authority obligations cannot hide behind one source projection."""
    with pytest.raises(ValueError, match="publication_mixed_retirement_projection"):
        PublicationEffect.compile(
            repository_common_dir="/repo/.git",
            source=_publication_source(),
            targets=(
                PublicationTarget(
                    id="peer",
                    remote="origin",
                    updates=(
                        PublicationUpdate(
                            target_ref="refs/heads/proposal/finished",
                            expected="2" * 40,
                            desired="0" * 40,
                        ),
                        PublicationUpdate(
                            target_ref="refs/heads/dev", expected="2" * 40, desired="1" * 40
                        ),
                    ),
                ),
            ),
        )


@pytest.mark.parametrize(
    ("kind", "updates", "error"),
    [
        (
            "commit",
            (
                PublicationUpdate(
                    target_ref="refs/heads/dev",
                    expected="0" * 40,
                    desired="1" * 40,
                ),
                PublicationUpdate(
                    target_ref="refs/heads/dev",
                    expected="0" * 40,
                    desired="1" * 40,
                ),
            ),
            "publication_target_ref_duplicate",
        ),
        (
            "commit",
            (
                PublicationUpdate(
                    target_ref="refs/heads/dev",
                    expected="0" * 40,
                    desired="2" * 40,
                ),
            ),
            "publication_target_source_mismatch",
        ),
        (
            "commit",
            (
                PublicationUpdate(
                    target_ref="refs/tags/v1.0.0",
                    expected="0" * 40,
                    desired="1" * 40,
                ),
            ),
            "publication_target_source_kind_mismatch",
        ),
    ],
)
def test_publication_effect_rejects_duplicate_or_source_inconsistent_updates(
    kind: str,
    updates: tuple[PublicationUpdate, ...],
    error: str,
) -> None:
    target = PublicationTarget.model_construct(id="peer", remote="origin", updates=updates)
    with pytest.raises(ValueError, match=error):
        PublicationEffect(
            repository_common_dir="/repo/.git",
            source=_publication_source(kind),
            targets=(target,),
        )


def test_publication_effect_rejects_duplicate_peer_and_mixed_ref_kinds() -> None:
    update = PublicationUpdate(
        target_ref="refs/heads/dev",
        expected="0" * 40,
        desired="1" * 40,
    )
    target = PublicationTarget(id="peer", remote="origin", updates=(update,))
    with pytest.raises(ValueError, match="publication_target_duplicate"):
        PublicationEffect(
            repository_common_dir="/repo/.git",
            source=_publication_source(),
            targets=(target, target),
        )
    with pytest.raises(ValueError, match="publication_target_ref_kind_mismatch"):
        PublicationEffect.compile(
            repository_common_dir="/repo/.git",
            source=_publication_source(),
            targets=(
                PublicationTarget(
                    id="mixed",
                    remote="origin",
                    updates=(
                        update,
                        PublicationUpdate(
                            target_ref="refs/tags/v1.0.0",
                            expected="0" * 40,
                            desired="1" * 40,
                        ),
                    ),
                ),
            ),
        )


def test_publication_plan_round_trips_and_rejects_nonadmitted_or_drifted_effect() -> None:
    effect = PublicationEffect.compile(
        repository_common_dir="/repo/.git",
        source=_publication_source(),
        targets=(
            PublicationTarget(
                id="peer",
                remote="origin",
                updates=(
                    PublicationUpdate(
                        target_ref="refs/heads/dev",
                        expected="0" * 40,
                        desired="1" * 40,
                    ),
                ),
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
