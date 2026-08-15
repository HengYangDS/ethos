from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.git import run_git
from ethos.contracts.semantic import Attestation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _input(path: Path, ordinal: int, *, carried_id: bool) -> Attestation:
    record = Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "observation:repository",
            "verifier": "agent:test:attestation-command",
            "subject": f"input:occurrence:{ordinal}",
            "issued_at": datetime(2026, 8, 14, tzinfo=UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": "input:feedback",
                "body": {"occurrence": {"ordinal": ordinal, "source": "test"}},
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (f"evidence:test:{ordinal}",),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
    )
    path.write_text(
        record.canonical_json() if carried_id else record.canonical_json(exclude_id=True),
        encoding="utf-8",
    )
    return record


def test_attestation_record_dry_run_then_apply_is_idempotent(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    input_path = tmp_path / "attestation.json"
    record = _input(input_path, 1, carried_id=False)

    dry = run_ethos(
        "attestation",
        "record",
        "--input",
        input_path.as_posix(),
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )
    applied = run_ethos(
        "attestation",
        "record",
        "--input",
        input_path.as_posix(),
        "--root",
        repo.as_posix(),
        "--apply",
        "--json",
        cwd=repo,
    )
    repeated = run_ethos(
        "attestation",
        "record",
        "--input",
        input_path.as_posix(),
        "--root",
        repo.as_posix(),
        "--apply",
        "--json",
        cwd=repo,
    )

    assert dry["state"] == "ready"
    assert dry["data"]["attestation"]["id"] == record.id
    assert applied["state"] == "recorded"
    assert applied["data"]["set_root"]
    assert repeated["state"] == "unchanged"
    assert repeated["data"]["set_root"] == applied["data"]["set_root"]


def test_attestation_query_returns_exact_unknown_values_without_authority_claim(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    first_path, second_path = tmp_path / "first.json", tmp_path / "second.json"
    first = _input(first_path, 2, carried_id=True)
    _input(second_path, 3, carried_id=True)
    for path in (first_path, second_path):
        run_ethos(
            "attestation",
            "record",
            "--input",
            path.as_posix(),
            "--root",
            repo.as_posix(),
            "--apply",
            "--json",
            cwd=repo,
        )

    result = run_ethos(
        "attestation",
        "query",
        "--subject",
        first.subject,
        "--payload-kind",
        first.payload.kind,
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert result["verdict"] == "pass"
    assert result["data"]["set_root"]
    assert result["data"]["authorizes_effects"] is False
    assert [item["id"] for item in result["data"]["attestations"]] == [first.id]


@pytest.mark.parametrize("arguments", [(), ("--apply",)])
def test_attestation_record_rejects_non_repository_root(
    tmp_path: Path, arguments: tuple[str, ...]
) -> None:
    input_path = tmp_path / "attestation.json"
    _input(input_path, 4, carried_id=True)
    command = [
        "attestation",
        "record",
        "--input",
        input_path.as_posix(),
        "--root",
        tmp_path.as_posix(),
    ]

    result = run_ethos_blocked(*command, *arguments, "--json", cwd=tmp_path)

    assert result["required_gaps"] == ["attestation_set_repository_invalid"]


def test_attestation_query_rejects_non_repository_root(tmp_path: Path) -> None:
    result = run_ethos_blocked(
        "attestation",
        "query",
        "--root",
        tmp_path.as_posix(),
        "--json",
        cwd=tmp_path,
    )

    assert result["required_gaps"] == ["attestation_set_repository_invalid"]


def test_attestation_query_reports_invalid_selected_root_without_traceback(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin="not-a-root").stdout.strip()
    run_git(repo, "update-ref", ATTESTATION_SET_REF, blob)

    result = run_ethos_blocked(
        "attestation",
        "query",
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert result["required_gaps"] == ["attestation_set_root_invalid"]


@pytest.mark.parametrize(
    ("option", "value", "field"),
    [
        ("--id", "not-a-digest", "id"),
        ("--predicate", "BAD SPACE", "predicate"),
        ("--verifier", "   ", "verifier"),
        ("--subject", "   ", "subject"),
        ("--payload-kind", "bad/space", "payload_kind"),
    ],
)
def test_attestation_query_rejects_invalid_selectors(
    tmp_path: Path, option: str, value: str, field: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")

    result = run_ethos_blocked(
        "attestation",
        "query",
        option,
        value,
        "--root",
        repo.as_posix(),
        "--json",
        cwd=repo,
    )

    assert result["required_gaps"] == [f"attestation_selector_invalid:{field}"]
