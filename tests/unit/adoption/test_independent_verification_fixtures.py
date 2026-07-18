from __future__ import annotations

from pathlib import Path

import pytest

from ethos.adapters.admission.evidence.external import independent_verification_policy

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "tests/fixtures/independent-verification-adopters"


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [("disabled", "disabled"), ("optional", "optional"), ("required", "required")],
)
def test_external_adopter_fixtures_keep_provider_depth_opt_in(fixture: str, expected: str) -> None:
    policy = independent_verification_policy(FIXTURES / fixture, "publish")

    assert policy.mode == expected
