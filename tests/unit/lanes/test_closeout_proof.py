from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.mutation.closeout.core import CloseoutRequest
from ethos.adapters.mutation.closeout.core import proof_carry_failure
from ethos_core.contracts.branch.roles import BranchRolePolicy


@pytest.mark.parametrize("required_gaps", [None, [], "proof_not_proven", {}])
def test_proof_carry_failure_normalizes_invalid_gap_payload(required_gaps: object) -> None:
    proof = {"ok": False}
    if required_gaps is not None:
        proof["required_gaps"] = required_gaps
    request = CloseoutRequest(Path(), BranchRolePolicy(), "old", "new", Path(), [])

    assert proof_carry_failure(request, proof)["required_gaps"] == ["proof_invalid"]
