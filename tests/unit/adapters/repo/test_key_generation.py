"""One owner reads the key generation that a redaction or a rebuild attempt recorded last."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.commit.signature import ATTEMPT
from ethos.adapters.repo.key_generation import REDACTION
from ethos.adapters.repo.key_generation import recorded_generation
from ethos.adapters.repo.key_generation import require_generation
from ethos.contracts.semantic import Attestation
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.paradigm.peer_identity import generation
from ethos.repository.paradigm.peer_identity import read_key
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path

KEY, OTHER = read_key("ab" * 32), read_key("cd" * 32)
# A rebuild's attempt is the signature repair's attempt under its own key; a repair's is not.
REBUILT, REPAIRED = (ATTEMPT, "rebuild:fixture-rebuild"), (ATTEMPT, f"signature-repair:{'0' * 64}")
REDACTED, LATER = ((REDACTION, f"{REDACTION}:{head}") for head in ("1" * 40, "2" * 40))


def _recorded(repo: Path, kind: tuple[str, str], key: bytes | None, day: int) -> None:
    """Record one member of a predicate under its key; without a key its body names none."""
    predicate, subject = kind
    issued = datetime(2026, 11, day, tzinfo=UTC)
    body = {"generation": generation(key)} if key else {"coordinates": {}}
    record_attestation_once(
        repo,
        Attestation.issue(
            {
                "schema_version": 2,
                "predicate": predicate,
                "verifier": "ethos",
                "subject": subject,
                "issued_at": issued,
                "valid_from": issued,
                "valid_until": None,
                "verdict": "pass",
                "payload": {"kind": predicate, "body": body},
                "relations": (),
                "advisories": (),
                "evidence_refs": (),
                "commitment_digest": None,
                "facts_digest": canonical_json_digest(body),
                "plan_digest": None,
                "policy_digest": None,
                "effect_digest": None,
                "mints_authority": False,
            }
        ),
    )


@pytest.mark.parametrize(
    ("records", "last"),
    [
        ((), None),
        (((REDACTED, KEY, 1),), KEY),
        (((REDACTED, KEY, 1), (REBUILT, OTHER, 2)), OTHER),
        (((REBUILT, OTHER, 1), (REDACTED, KEY, 2)), KEY),
        ((((REBUILT[0], "rebuild-attempt"), OTHER, 3),), None),
        (((("observation:unrelated", REBUILT[1]), OTHER, 3),), None),
        (((("observation:rebuild-attempt", REBUILT[1]), OTHER, 3),), None),
        (((REDACTED, KEY, 1), (REPAIRED, None, 2)), KEY),
        (((REPAIRED, OTHER, 1),), None),
    ],
)
def test_the_last_redaction_or_rebuild_attempt_names_the_generation(
    tmp_path: Path,
    records: tuple[tuple[tuple[str, str], bytes | None, int], ...],
    last: bytes | None,
) -> None:
    """Both kinds count, by issue time: a rebuild's is the repair attempt under `rebuild:<id>`.

    Another predicate, or the repair attempt under any other key, names no generation.
    """
    repo = init_git_repo(tmp_path / "repo")
    for kind, key, day in records:
        _recorded(repo, kind, key, day)

    assert recorded_generation(repo) == (generation(last) if last else None)
    if last is None:
        require_generation(repo, OTHER)
        return
    require_generation(repo, last)
    stranger = OTHER if last == KEY else KEY
    with pytest.raises(ValueError, match="redaction_key_generation_changed"):
        require_generation(repo, stranger)
    require_generation(repo, stranger, rotate=True)


@pytest.mark.parametrize("kind", [LATER, REBUILT])
def test_a_last_record_that_names_no_generation_refuses(
    tmp_path: Path, kind: tuple[str, str]
) -> None:
    """Only no record means no generation yet; every writer names one, so a bare record refuses."""
    repo = init_git_repo(tmp_path / "repo")
    _recorded(repo, REDACTED, KEY, 1)
    _recorded(repo, kind, None, 2)

    with pytest.raises(ValueError, match="redaction_key_generation_unrecorded"):
        require_generation(repo, KEY, rotate=True)
