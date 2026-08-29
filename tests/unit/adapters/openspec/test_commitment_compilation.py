"""Official OpenSpec projection is the sole input to Commitment compilation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ethos.adapters.openspec.commitment import commitment_from_projection
from ethos.contracts.semantic import Commitment


def test_official_projection_compiles_minimal_commitment() -> None:
    projection = {
        "id": "minimal-authority",
        "deltas": [
            {
                "spec": "authority",
                "requirements": [
                    {
                        "text": "Official OpenSpec is the sole tracked intent carrier.",
                        "scenarios": [{"rawText": "- **WHEN** selected\n- **THEN** compile"}],
                    }
                ],
            }
        ],
    }

    commitment = commitment_from_projection("minimal-authority", projection)

    assert commitment.id == "change:minimal-authority"
    assert commitment.acceptance == (
        "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
        "authority:scenario:- **WHEN** selected\n- **THEN** compile",
    )
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Commitment.model_validate(commitment.model_dump() | {"predecessors": ()})


def test_removed_requirements_do_not_become_acceptance_obligations() -> None:
    projection = {
        "id": "minimal-authority",
        "deltas": [
            {
                "spec": "authority",
                "operation": "REMOVED",
                "requirements": [
                    {
                        "text": "Retired parallel authority remains supported.",
                        "scenarios": [],
                    }
                ],
            },
            {
                "spec": "authority",
                "operation": "ADDED",
                "requirements": [
                    {
                        "text": "Official OpenSpec is the sole tracked intent carrier.",
                        "scenarios": [{"rawText": "- **WHEN** selected\n- **THEN** compile"}],
                    }
                ],
            },
        ],
    }

    commitment = commitment_from_projection("minimal-authority", projection)

    assert commitment.acceptance == (
        "authority:requirement:Official OpenSpec is the sole tracked intent carrier.",
        "authority:scenario:- **WHEN** selected\n- **THEN** compile",
    )
