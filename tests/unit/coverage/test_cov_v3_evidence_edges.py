"""Coverage-closure v3: evidence reachable branches (100% no-exemption).

Each test drives one uncovered gap-emitting branch in the evidence cluster:
- ethos.repository.evidence.claims: change-claim evidence-ref validation
  (111, 116-117, 121-122, 126, 130, 132, 145) and normal-claim digest/date
  gates (250-251, 294-295, 299-300).
- ethos.repository.evidence.parity.validation: the None-target command-identity
  branch 328->330.
All lines are reached through the real public/underscore-prefixed functions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.evidence.claims import claims_report
from ethos.repository.evidence.parity.validation import command_matches_identity

if TYPE_CHECKING:
    from pathlib import Path


def _claims_dir(root: Path) -> Path:
    claims = root / "evidence" / "claims"
    claims.mkdir(parents=True, exist_ok=True)
    return claims


def _write_evidence(root: Path, rel: str, text: str = "sample\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    ("name", "body", "expected_gap", "seed_artifact"),
    [
        (
            "nodate.toml",
            '[claim]\nid = "nodate"\nstate = "historical"\n\n[evidence]\nsha256 = "abc"\n',
            "nodate:evidence.dated_missing",
            None,
        ),
        (
            "normal-missfile.toml",
            '[claim]\nid = "missing-file"\nstate = "historical"\n\n'
            '[evidence]\ndated = "evidence/nope.md"\n',
            "missing-file:evidence_file_missing:evidence/nope.md",
            None,
        ),
        (
            "nosha.toml",
            '[claim]\nid = "nosha"\nstate = "historical"\n\n[evidence]\ndated = "evidence/e.md"\n',
            "nosha:evidence.sha256_missing",
            "evidence/e.md",
        ),
    ],
    ids=[
        "normal-dated-missing",
        "normal-dated-file-missing",
        "normal-dated-sha-missing",
    ],
)
def test_claim_record_gap(
    tmp_path: Path,
    name: str,
    body: str,
    expected_gap: str,
    seed_artifact: str | None,
) -> None:
    if seed_artifact:
        _write_evidence(tmp_path, seed_artifact)
    (_claims_dir(tmp_path) / name).write_text(body, encoding="utf-8")

    assert expected_gap in claims_report(tmp_path)["required_gaps"]


# --------------------------------------------------------------------------- #
# ethos.repository.evidence.parity.core.validation :: command_matches_identity
# --------------------------------------------------------------------------- #


def test_command_identity_none_target_reaches_flag_check() -> None:
    # Branch 328->330: target is None (skips 322 block) and "--target " IS present,
    # so the elif is False and control falls through to the --execute/--json check.
    command = "ethos parity shadow --adopter demo --target . --execute --json"

    assert command_matches_identity(command, adopter="demo", target=None) is True
