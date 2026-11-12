"""One owner reads the key generation that a redaction or a rebuild attempt recorded last."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.attestation_set import record_attestation_once
from ethos.adapters.repo.key_generation import REBUILD_ATTEMPT
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


def _recorded(repo: Path, predicate: str, key: bytes, day: int) -> None:
    issued = datetime(2026, 11, day, tzinfo=UTC)
    body = {"generation": generation(key)}
    record_attestation_once(
        repo,
        Attestation.issue(
            {
                "schema_version": 2,
                "predicate": predicate,
                "verifier": "ethos",
                "subject": f"{predicate}:{day}",
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
        (((REDACTION, KEY, 1),), KEY),
        (((REDACTION, KEY, 1), (REBUILD_ATTEMPT, OTHER, 2)), OTHER),
        (((REBUILD_ATTEMPT, OTHER, 1), (REDACTION, KEY, 2)), KEY),
        ((("observation:unrelated", OTHER, 3),), None),
    ],
)
def test_the_last_redaction_or_rebuild_attempt_names_the_generation(
    tmp_path: Path, records: tuple[tuple[str, bytes, int], ...], last: bytes | None
) -> None:
    """Both record kinds count, by issue time; another predicate names no generation."""
    repo = init_git_repo(tmp_path / "repo")
    for predicate, key, day in records:
        _recorded(repo, predicate, key, day)

    assert recorded_generation(repo) == (generation(last) if last else None)
    if last is None:
        require_generation(repo, OTHER)
        return
    require_generation(repo, last)
    stranger = OTHER if last == KEY else KEY
    with pytest.raises(ValueError, match="redaction_key_generation_changed"):
        require_generation(repo, stranger)
    require_generation(repo, stranger, rotate=True)
