"""Public result recording and query preserve immutable identity and idempotence."""

from __future__ import annotations

import hashlib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo import attestation_set
from ethos.adapters.repo.attestation_set import ATTESTATION_SET_REF
from ethos.adapters.repo.attestation_set import MEMBER_BYTES_LIMIT
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.git import run_git
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture

if TYPE_CHECKING:
    import pytest

    from ethos.contracts.semantic import Attestation


def _input(path: Path, ordinal: int, *, carried_id: bool) -> Attestation:
    record = attestation_fixture(
        predicate="observation:repository",
        verifier="agent:test:attestation-command",
        subject=f"input:occurrence:{ordinal}",
        issued_at=datetime(2026, 8, 14, tzinfo=UTC),
        payload_kind="input:future-feedback",
        payload_body={"occurrence": {"ordinal": ordinal, "source": "test"}},
        evidence_refs=(f"evidence:test:{ordinal}",),
    )
    path.write_text(
        record.canonical_json() if carried_id else record.canonical_json(exclude_id=True),
        encoding="utf-8",
    )
    return record


def _command(root: Path, *arguments: str, blocked: bool = False):
    """Share public invocation construction, preserving each scenario's assertions."""
    runner = run_ethos_blocked if blocked else run_ethos
    return runner("attestation", *arguments, "--root", str(root), "--json", cwd=root)


def test_attestation_record_dry_run_then_apply_is_idempotent(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    input_path = tmp_path / "attestation.json"
    record = _input(input_path, 1, carried_id=False)

    results = [
        _command(repo, "record", "--input", input_path.as_posix(), *arguments)
        for arguments in ((), ("--apply",), ("--apply",))
    ]

    dry, applied, repeated = results
    assert (dry["state"], dry["data"]["attestation"]["id"]) == ("ready", record.id)
    assert applied["state"] == "recorded"
    assert applied["data"]["set_root"]
    # No reflog covers the set ref, so the replaced root is recoverable only from this output.
    assert applied["data"]["previous_set_root"] == dry["data"]["set_root"]
    assert (repeated["state"], repeated["data"]["set_root"]) == (
        "unchanged",
        applied["data"]["set_root"],
    )


def test_attestation_record_refuses_oversized_input_before_any_effect(tmp_path: Path) -> None:
    """File bytes above the member bound are refused and routed to custody evidence."""
    repo = init_git_repo(tmp_path / "repo")
    input_path = tmp_path / "attestation.json"
    record = attestation_fixture(
        predicate="observation:repository",
        verifier="agent:test:attestation-command",
        subject="input:occurrence:oversized",
        issued_at=datetime(2026, 8, 14, tzinfo=UTC),
        payload_kind="input:future-feedback",
        payload_body={"text": "x" * MEMBER_BYTES_LIMIT},
        evidence_refs=("evidence:test:oversized",),
    )
    input_path.write_text(record.canonical_json(exclude_id=True), encoding="utf-8")

    for arguments in ((), ("--apply",)):
        result = _command(
            repo, "record", "--input", input_path.as_posix(), *arguments, blocked=True
        )
        assert result["required_gaps"] == [f"attestation_member_too_large:{record.id}"]
        assert "--evidence" in result["next_action"]
    assert not run_git(repo, "for-each-ref", ATTESTATION_SET_REF).stdout


def test_attestation_record_reports_an_existing_oversized_member_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The bound applies to members being added, so replaying a held legacy member is a no-op."""
    repo = init_git_repo(tmp_path / "repo")
    input_path = tmp_path / "attestation.json"
    legacy = attestation_fixture(
        predicate="observation:repository",
        verifier="agent:test:attestation-command",
        subject="input:occurrence:legacy",
        issued_at=datetime(2026, 10, 1, tzinfo=UTC),
        payload_kind="input:future-feedback",
        payload_body={"text": "x" * MEMBER_BYTES_LIMIT},
        evidence_refs=("evidence:test:legacy",),
    )
    input_path.write_text(legacy.canonical_json(), encoding="utf-8")
    # Members recorded before the bound existed are held legally; seed one the same way.
    monkeypatch.setattr(attestation_set, "MEMBER_BYTES_LIMIT", 2 * MEMBER_BYTES_LIMIT)
    root = attestation_set.record_attestations(repo, (legacy,))["root"]
    monkeypatch.undo()

    for arguments in ((), ("--apply",)):
        result = _command(repo, "record", "--input", input_path.as_posix(), *arguments)
        assert (result["state"], result["data"]["added"]) == ("unchanged", [])
    assert run_git(repo, "rev-parse", ATTESTATION_SET_REF).stdout.strip() == root


def _custody_input(path: Path, digest: str) -> Attestation:
    record = attestation_fixture(
        predicate="observation:repository",
        verifier="agent:test:attestation-command",
        subject="input:occurrence:custody",
        issued_at=datetime(2026, 10, 16, tzinfo=UTC),
        payload_kind="input:future-feedback",
        payload_body={"claim": "preserved failed receipt"},
        evidence_refs=(f"custody:sha256:{digest}",),
    )
    path.write_text(record.canonical_json(exclude_id=True), encoding="utf-8")
    return record


def test_attestation_record_stores_declared_custody_evidence(tmp_path: Path) -> None:
    """Declared evidence is stored byte-exact without touching the index or tracked tree."""
    repo = init_git_repo(tmp_path / "repo")
    evidence = tmp_path / "receipt.bin"
    evidence.write_bytes(b"failed receipt\n\x00")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    record = _custody_input(tmp_path / "attestation.json", digest)
    arguments = ("--input", (tmp_path / "attestation.json").as_posix(), "--evidence")

    preview = _command(repo, "record", *arguments, evidence.as_posix())
    applied = _command(repo, "record", *arguments, evidence.as_posix(), "--apply")

    assert (preview["state"], applied["state"]) == ("ready", "recorded")
    assert applied["data"]["custody"] == [digest]
    stored = Path(git_common_dir(repo)) / "ethos/custody/sha256" / digest
    assert stored.read_bytes() == evidence.read_bytes()
    assert applied["data"]["attestation"]["id"] == record.id
    assert run_git(repo, "status", "--porcelain").stdout == ""


def test_attestation_record_refuses_missing_or_undeclared_custody(tmp_path: Path) -> None:
    """A declared digest needs its exact bytes and every supplied file must be declared."""
    repo = init_git_repo(tmp_path / "repo")
    other = tmp_path / "other.bin"
    other.write_bytes(b"other")
    digest = hashlib.sha256(b"declared").hexdigest()
    _custody_input(tmp_path / "attestation.json", digest)
    arguments = ("record", "--input", (tmp_path / "attestation.json").as_posix())

    missing = _command(repo, *arguments, "--apply", blocked=True)
    undeclared = _command(repo, *arguments, "--evidence", other.as_posix(), "--apply", blocked=True)

    assert missing["required_gaps"] == [f"attestation_custody_missing:{digest}"]
    other_digest = hashlib.sha256(b"other").hexdigest()
    assert undeclared["required_gaps"] == [f"attestation_custody_undeclared:{other_digest}"]
    assert not run_git(repo, "for-each-ref", ATTESTATION_SET_REF).stdout


def test_attestation_release_previews_then_removes_an_owned_member(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The verifier releases its open-predicate member by exact CAS after a preview."""
    repo = init_git_repo(tmp_path / "repo")
    input_path = tmp_path / "attestation.json"
    record = _input(input_path, 7, carried_id=False)
    recorded = _command(repo, "record", "--input", input_path.as_posix(), "--apply")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:attestation-command")

    preview = _command(repo, "release", "--id", record.id)
    applied = _command(repo, "release", "--id", record.id, "--apply")

    assert (preview["state"], applied["state"]) == ("ready", "released")
    assert applied["data"]["previous_root"] == recorded["data"]["set_root"]
    assert applied["data"]["root"] != applied["data"]["previous_root"]
    assert _command(repo, "query", "--id", record.id)["data"]["attestations"] == []


def test_attestation_release_needs_review_from_another_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another actor is refused until it names reviewed content and a reason."""
    repo = init_git_repo(tmp_path / "repo")
    input_path = tmp_path / "attestation.json"
    record = _input(input_path, 8, carried_id=False)
    _command(repo, "record", "--input", input_path.as_posix(), "--apply")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:other")
    release = ("release", "--id", record.id, "--apply")

    for extra in ((), ("--review-content",), ("--reason", "consumer closed")):
        blocked = _command(repo, *release, *extra, blocked=True)
        assert blocked["required_gaps"] == ["attestation_release_actor_unadmitted"]
    reviewed = _command(repo, *release, "--review-content", "--reason", "consumer closed")
    assert reviewed["state"] == "released"


def test_attestation_query_returns_exact_unknown_values_without_authority_claim(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    paths = (tmp_path / "first.json", tmp_path / "second.json")
    records = tuple(
        _input(path, ordinal, carried_id=True) for path, ordinal in zip(paths, (2, 3), strict=True)
    )
    for path in paths:
        _command(repo, "record", "--input", path.as_posix(), "--apply")

    first = records[0]
    result = _command(
        repo, "query", "--subject", first.subject, "--payload-kind", first.payload.kind
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
        result = _command(
            tmp_path, "record", "--input", input_path.as_posix(), *arguments, blocked=True
        )
        assert result["required_gaps"] == ["attestation_set_repository_invalid"]

    result = _command(tmp_path, "query", blocked=True)
    assert result["required_gaps"] == ["attestation_set_repository_invalid"]

    repo = init_git_repo(tmp_path / "repo")
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin="not-a-root").stdout.strip()
    run_git(repo, "update-ref", ATTESTATION_SET_REF, blob)
    result = _command(repo, "query", blocked=True)
    assert result["required_gaps"] == ["attestation_set_root_invalid"]

    selectors = (
        ("--id", "not-a-digest", "id"),
        ("--predicate", "BAD SPACE", "predicate"),
        ("--verifier", "   ", "verifier"),
        ("--subject", "   ", "subject"),
        ("--payload-kind", "bad/space", "payload_kind"),
    )
    for option, value, field in selectors:
        result = _command(repo, "query", option, value, blocked=True)
        assert result["required_gaps"] == [f"attestation_selector_invalid:{field}"]
