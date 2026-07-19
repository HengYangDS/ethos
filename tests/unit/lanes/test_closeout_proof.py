from pathlib import Path

import pytest

import ethos.adapters.mutation.closeout.core as closeout
from ethos_core.contracts.branch.roles import BranchRolePolicy

_BAD, _GAP = ["proof_invalid"], ["proof_not_proven"]


@pytest.mark.parametrize(
    ("gaps", "expected"),
    [(None, _BAD), ([], _BAD), (_GAP[0], _BAD), ({}, _BAD), (_GAP, _GAP), ([*_GAP, 1], _BAD)],
)
def test_proof_carry_failure_normalizes_gap_payload(gaps: object, expected: list[str]) -> None:
    proof = {"ok": False} if gaps is None else {"ok": False, "required_gaps": gaps}
    request = closeout.CloseoutRequest(Path(), BranchRolePolicy(), "old", "new", Path(), [])
    assert closeout.proof_carry_failure(request, proof)["required_gaps"] == expected
