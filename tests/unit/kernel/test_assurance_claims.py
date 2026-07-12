from __future__ import annotations

import pytest

from ethos_core.models import EvidenceClaim


def test_semantic_attestation_cannot_unlock_verified_language() -> None:
    with pytest.raises(ValueError, match="semantic_attested does not permit verified"):
        EvidenceClaim(
            id="claim:attestation",
            change_id="change:example",
            evidence_ids=("evidence:example",),
            binding="The semantic behavior is verified.",
            verifier="semantic_attested",
        )


def test_independent_reexecution_is_bounded_to_its_proof_floor() -> None:
    claim = EvidenceClaim(
        id="claim:reexecution",
        change_id="change:example",
        evidence_ids=("evidence:example",),
        binding="An independent provider re-executed the declared proof floor.",
        verifier="independently_reexecuted",
    )

    assert claim.to_dict()["verifier"] == "independently_reexecuted"


def test_independent_reexecution_cannot_claim_semantic_correctness() -> None:
    with pytest.raises(
        ValueError,
        match="independently_reexecuted does not permit semantic correctness",
    ):
        EvidenceClaim(
            id="claim:reexecution-overclaim",
            change_id="change:example",
            evidence_ids=("evidence:example",),
            binding="The independent run proves semantic correctness.",
            verifier="independently_reexecuted",
        )
