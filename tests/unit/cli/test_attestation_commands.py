from __future__ import annotations

from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

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
                "kind": "input:future-feedback",
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

    results = [
        run_ethos(
            "attestation",
            "record",
            "--input",
            input_path.as_posix(),
            "--root",
            repo.as_posix(),
            *arguments,
            "--json",
            cwd=repo,
        )
        for arguments in ((), ("--apply",), ("--apply",))
    ]

    dry, applied, repeated = results
    assert (dry["state"], dry["data"]["attestation"]["id"]) == ("ready", record.id)
    assert applied["state"] == "recorded"
    assert applied["data"]["set_root"]
    assert (repeated["state"], repeated["data"]["set_root"]) == (
        "unchanged",
        applied["data"]["set_root"],
    )


def test_attestation_query_returns_exact_unknown_values_without_authority_claim(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    paths = (tmp_path / "first.json", tmp_path / "second.json")
    records = tuple(
        _input(path, ordinal, carried_id=True) for path, ordinal in zip(paths, (2, 3), strict=True)
    )
    for path in paths:
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

    first = records[0]
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
    assert result["data"]["attestations"] == [first.model_dump(mode="json")]


def test_attestation_commands_fail_closed_for_invalid_roots_and_selectors(
    tmp_path: Path,
) -> None:
    input_path = tmp_path / "attestation.json"
    _input(input_path, 4, carried_id=True)
    for arguments in ((), ("--apply",)):
        result = run_ethos_blocked(
            "attestation",
            "record",
            "--input",
            input_path.as_posix(),
            "--root",
            tmp_path.as_posix(),
            *arguments,
            "--json",
            cwd=tmp_path,
        )
        assert result["required_gaps"] == ["attestation_set_repository_invalid"]

    result = run_ethos_blocked(
        "attestation", "query", "--root", tmp_path.as_posix(), "--json", cwd=tmp_path
    )
    assert result["required_gaps"] == ["attestation_set_repository_invalid"]

    repo = init_git_repo(tmp_path / "repo")
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin="not-a-root").stdout.strip()
    run_git(repo, "update-ref", ATTESTATION_SET_REF, blob)
    result = run_ethos_blocked(
        "attestation", "query", "--root", repo.as_posix(), "--json", cwd=repo
    )
    assert result["required_gaps"] == ["attestation_set_root_invalid"]

    selectors = (
        ("--id", "not-a-digest", "id"),
        ("--predicate", "BAD SPACE", "predicate"),
        ("--verifier", "   ", "verifier"),
        ("--subject", "   ", "subject"),
        ("--payload-kind", "bad/space", "payload_kind"),
    )
    for option, value, field in selectors:
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
