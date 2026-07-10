from __future__ import annotations

# ruff: noqa: ARG005, FBT003
import argparse
import hashlib
import json
import runpy
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import ethos.adapters.admission.control.replacement as replacement
import ethos.adapters.admission.control.verifier as verifier
import ethos.adapters.admission.evidence.external as external
from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.coordination import CrossHostHandoff
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.coordination import LaneLease
from ethos_core.contracts.evidence.external import IdentityAssertion
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _identity_payload(now: datetime) -> dict[str, object]:
    return {
        "identity_ref": "workload:issuer:subject:build-1",
        "issuer": "https://issuer.example",
        "audience": "ethos:accepted-closeout",
        "verification_method": "oidc-signature",
        "valid_from": (now - timedelta(minutes=1)).isoformat(),
        "valid_until": (now + timedelta(minutes=5)).isoformat(),
        "attestation_digest": "a" * 64,
    }


def _enforcement_payload(now: datetime) -> dict[str, object]:
    return {
        "provider": "gitlab",
        "enforcement_boundary": "protected_ref_transition",
        "action": "accepted.advance",
        "resource": "refs/heads/dev",
        "old_value": "a" * 40,
        "new_value": "b" * 40,
        "observed_at": now.isoformat(),
        "receipt_digest": "c" * 64,
        "prevention_coverage": "provider_mediated_ref_update",
    }


def test_verifier_helpers_cover_fail_closed_edges(tmp_path: Path, monkeypatch) -> None:
    parser = verifier._parser()  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert {action.dest for action in parser._actions} >= {  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        "accepted_root",
        "candidate_root",
        "accepted_head",
        "candidate_head",
        "candidate_proof",
        "bootstrap_chronicle",
        "write_receipt",
    }
    assert verifier._is_control_path("system/gates.toml") is True  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert verifier._is_control_path("README.md") is False  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch

    payload = _write_json(tmp_path / "payload.json", {"ok": True})
    assert verifier._json(payload) == {"ok": True}  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert verifier._sha256(payload) == hashlib.sha256(payload.read_bytes()).hexdigest()  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    with pytest.raises(SystemExit, match=r"invalid_json_mapping:array\.json"):
        verifier._json(_write_json(tmp_path / "array.json", []))  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    with pytest.raises(SystemExit, match="required"):
        verifier._require(False, "required")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    verifier._require(True, "unused")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch

    monkeypatch.setattr(
        verifier.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0, stdout=" value \n"),
    )
    assert verifier._git(tmp_path, "rev-parse", "HEAD") == "value"  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert verifier._run(tmp_path, "git", "status").returncode == 0  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch


def test_verifier_control_digest_and_decision_matrix(tmp_path: Path, monkeypatch) -> None:
    responses = iter(
        (
            subprocess.CompletedProcess(["git"], 0, stdout=b"present"),
            subprocess.CompletedProcess(["git"], 128, stdout=b""),
        )
    )
    monkeypatch.setattr(verifier.subprocess, "run", lambda *args, **kwargs: next(responses))
    digest = verifier._control_digest(tmp_path, "a" * 40, ["system/gates.toml", "missing"])  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    assert len(digest) == 64

    valid = {
        "schema_version": 1,
        "kind": "control-replacement-bootstrap-decision",
        "event_type": "decision",
        "decision": "bootstrap/control-replacement",
        "accepted_head": "a",
        "candidate_head": "b",
        "verifier_sha256": "v",
        "candidate_proof_digest": "p",
        "evidence_ids": ["evidence:review"],
        "mints_authority": False,
        "reusable_authorization": False,
    }
    verifier._validate_bootstrap_decision(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        valid,
        accepted_head="a",
        candidate_head="b",
        verifier_digest="v",
        proof_digest="p",
    )
    checks = (
        ("schema_version", 2, "bootstrap_decision_schema_invalid"),
        ("kind", "bad", "bootstrap_decision_kind_invalid"),
        ("event_type", "observation", "bootstrap_chronicle_event_invalid"),
        ("decision", "bad", "bootstrap_decision_value_invalid"),
        ("accepted_head", "bad", "bootstrap_accepted_head_mismatch"),
        ("candidate_head", "bad", "bootstrap_candidate_head_mismatch"),
        ("verifier_sha256", "bad", "bootstrap_verifier_digest_mismatch"),
        ("candidate_proof_digest", "bad", "bootstrap_candidate_proof_digest_mismatch"),
        ("evidence_ids", [], "bootstrap_evidence_required"),
        ("mints_authority", True, "bootstrap_authority_invalid"),
        ("reusable_authorization", True, "bootstrap_reusable_authorization_invalid"),
    )
    for key, value, gap in checks:
        invalid = {**valid, key: value}
        with pytest.raises(SystemExit, match=gap):
            verifier._validate_bootstrap_decision(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
                invalid,
                accepted_head="a",
                candidate_head="b",
                verifier_digest="v",
                proof_digest="p",
            )


def test_verifier_main_projects_exact_receipt(tmp_path: Path, monkeypatch) -> None:
    accepted_root = tmp_path / "accepted"
    candidate_root = tmp_path / "candidate"
    accepted_root.mkdir()
    candidate_root.mkdir()
    proof = _write_json(tmp_path / "proof.json", {"head": "b", "state": "proven"})
    decision = _write_json(tmp_path / "decision.json", {"decision": "bound"})
    receipt = tmp_path / "receipt.json"
    args = argparse.Namespace(
        accepted_root=accepted_root.as_posix(),
        candidate_root=candidate_root.as_posix(),
        accepted_head="a",
        candidate_head="b",
        candidate_proof=proof.as_posix(),
        bootstrap_chronicle=decision.as_posix(),
        write_receipt=receipt.as_posix(),
    )
    monkeypatch.setattr(verifier, "_parser", lambda: SimpleNamespace(parse_args=lambda: args))
    monkeypatch.setattr(
        verifier,
        "_git",
        lambda root, *git_args: (
            "a"
            if git_args == ("rev-parse", "HEAD") and root == accepted_root.resolve()
            else "b"
            if git_args == ("rev-parse", "HEAD")
            else "system/gates.toml\n"
        ),
    )
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(
        verifier,
        "_run",
        lambda _root, *command: (
            calls.append(command) or subprocess.CompletedProcess(command, 0, stdout="")
        ),
    )
    monkeypatch.setattr(
        verifier,
        "_json",
        lambda path: {"head": "b", "state": "proven"} if path == proof else {"ok": True},
    )
    monkeypatch.setattr(verifier, "_validate_bootstrap_decision", lambda *args, **kwargs: None)
    monkeypatch.setattr(verifier, "_control_digest", lambda *args, **kwargs: "d" * 64)

    assert verifier.main() == 0
    projected = json.loads(receipt.read_text())
    assert projected["control_paths"] == ["system/gates.toml"]
    assert projected["verdict"] == "allow"
    assert calls == [("git", "merge-base", "--is-ancestor", "a", "b")]


def test_verifier_module_entrypoint_raises_main_status(monkeypatch) -> None:
    monkeypatch.setattr(runpy, "run_module", runpy.run_module)
    monkeypatch.setattr(verifier, "main", lambda: 7)
    with pytest.raises(SystemExit) as exc:
        raise SystemExit(verifier.main())
    assert exc.value.code == 7


def test_verifier_original_module_entrypoint_executes(tmp_path: Path, monkeypatch) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    control = candidate / "system" / "gates.toml"
    control.parent.mkdir(parents=True)
    control.write_text("version = 2\n", encoding="utf-8")
    git(candidate, "add", ".")
    git(
        candidate,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=t@example.com",
        "commit",
        "-m",
        "control",
    )
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    proof = _write_json(tmp_path / "proof.json", {"head": candidate_head, "state": "proven"})
    verifier_path = Path(verifier.__file__).resolve()
    decision = _write_json(
        tmp_path / "decision.json",
        {
            "schema_version": 1,
            "kind": "control-replacement-bootstrap-decision",
            "event_type": "decision",
            "decision": "bootstrap/control-replacement",
            "accepted_head": accepted_head,
            "candidate_head": candidate_head,
            "verifier_sha256": hashlib.sha256(verifier_path.read_bytes()).hexdigest(),
            "candidate_proof_digest": hashlib.sha256(proof.read_bytes()).hexdigest(),
            "evidence_ids": ["evidence:review"],
            "mints_authority": False,
            "reusable_authorization": False,
        },
    )
    receipt = tmp_path / "receipt.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            verifier_path.as_posix(),
            "--accepted-root",
            repo.as_posix(),
            "--candidate-root",
            candidate.as_posix(),
            "--accepted-head",
            accepted_head,
            "--candidate-head",
            candidate_head,
            "--candidate-proof",
            proof.as_posix(),
            "--bootstrap-chronicle",
            decision.as_posix(),
            "--write-receipt",
            receipt.as_posix(),
        ],
    )
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(verifier_path.as_posix(), run_name="__main__")
    assert exc.value.code == 0
    assert json.loads(receipt.read_text())["candidate_head"] == candidate_head


def test_replacement_receipt_validation_reports_all_binding_failures(
    tmp_path: Path, monkeypatch
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    verifier_path = tmp_path / "verifier.py"
    decision_path = tmp_path / "decision.json"
    proof_path = tmp_path / "proof.json"
    for path in (verifier_path, decision_path, proof_path):
        path.write_text(path.name, encoding="utf-8")
    receipt = {
        "kind": "bad",
        "provenance": "self",
        "accepted_head": "bad",
        "candidate_head": "bad",
        "verdict": "block",
        "mints_authority": True,
        "verifier_path": verifier_path.as_posix(),
        "verifier_sha256": "bad",
        "bootstrap_decision_path": decision_path.as_posix(),
        "bootstrap_decision_digest": "bad",
        "candidate_proof_path": proof_path.as_posix(),
        "candidate_proof_digest": "bad",
    }
    monkeypatch.setattr(
        replacement, "validate_schema_instance", lambda *args, **kwargs: {"ok": True}
    )
    gaps = replacement._receipt_gaps(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        receipt,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )
    assert {
        "control_replacement_receipt_kind_invalid",
        "control_replacement_provenance_invalid",
        "control_replacement_accepted_head_mismatch",
        "control_replacement_candidate_head_mismatch",
        "control_replacement_verdict_not_allow",
        "control_replacement_receipt_authority_invalid",
        "control_replacement_verifier_digest_mismatch",
        "bootstrap_decision_digest_mismatch",
        "control_replacement_candidate_proof_digest_mismatch",
    }.issubset(gaps)

    monkeypatch.setattr(
        replacement, "validate_schema_instance", lambda *args, **kwargs: {"ok": False}
    )
    assert replacement._receipt_gaps(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        receipt,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    ) == ["control_replacement_receipt_invalid"]


def test_replacement_external_receipt_path_and_file_edges(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    inside = candidate / "receipt.json"
    inside.write_text("{}", encoding="utf-8")
    assert replacement._external_receipt(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        path=inside,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )[1] == ["bootstrap_verifier_inside_candidate_tree"]
    assert replacement._external_receipt(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        path=tmp_path / "missing.json",
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )[1] == ["control_replacement_receipt_invalid"]
    array = _write_json(tmp_path / "array.json", [])
    assert replacement._external_receipt(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        path=array,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )[1] == ["control_replacement_receipt_invalid"]
    completed = subprocess.CompletedProcess(["git"], 1, stdout="", stderr="bad")
    original = replacement.subprocess.run
    replacement.subprocess.run = lambda *args, **kwargs: completed
    try:
        assert replacement._changed_paths(candidate, "a", "b") == ()  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    finally:
        replacement.subprocess.run = original


def test_replacement_receipt_rejects_inside_or_missing_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    inside = candidate / "inside.py"
    inside.write_text("inside", encoding="utf-8")
    receipt = {
        "kind": "control-replacement-verifier",
        "provenance": "incumbent_runner",
        "accepted_head": "a",
        "candidate_head": "b",
        "verdict": "allow",
        "mints_authority": False,
        "verifier_path": inside.as_posix(),
        "verifier_sha256": hashlib.sha256(inside.read_bytes()).hexdigest(),
        "bootstrap_decision_path": (tmp_path / "missing-decision").as_posix(),
        "bootstrap_decision_digest": "d" * 64,
        "candidate_proof_path": (tmp_path / "missing-proof").as_posix(),
        "candidate_proof_digest": "p" * 64,
    }
    monkeypatch.setattr(
        replacement, "validate_schema_instance", lambda *args, **kwargs: {"ok": True}
    )
    gaps = replacement._receipt_gaps(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        receipt,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )
    assert gaps == [
        "bootstrap_verifier_inside_candidate_tree",
        "bootstrap_decision_missing",
        "control_replacement_candidate_proof_missing",
    ]


@pytest.mark.parametrize(
    ("payload", "expected_gap"),
    [
        ({"bad": True}, "identity_assertion_invalid"),
        ([], "identity_assertion_invalid"),
    ],
)
def test_external_identity_invalid_payloads(
    tmp_path: Path, payload: object, expected_gap: str
) -> None:
    path = _write_json(tmp_path / "identity.json", payload)
    assert external._identity_report(path, required=True) == ({}, [expected_gap])  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch


def test_external_identity_future_and_read_failures(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    future = _identity_payload(now)
    future["valid_from"] = (now + timedelta(minutes=1)).isoformat()
    future["valid_until"] = (now + timedelta(minutes=2)).isoformat()
    assert external._identity_report(_write_json(tmp_path / "future.json", future), required=True)[  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        1
    ] == ["identity_assertion_not_yet_valid"]
    assert external._read_mapping(tmp_path / "missing.json", "invalid") == ({}, "invalid")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert external._read_mapping(malformed, "invalid") == ({}, "invalid")  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch


def test_external_enforcement_invalid_and_binding_edges(tmp_path: Path) -> None:
    now = datetime.now(UTC)
    invalid = _write_json(tmp_path / "invalid.json", {"bad": True})
    assert external._enforcement_report(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        invalid,
        required=True,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
    )[1] == ["hosted_enforcement_receipt_invalid"]
    assert external._enforcement_report(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        tmp_path / "missing.json",
        required=True,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
    )[1] == ["hosted_enforcement_receipt_invalid"]
    mismatch = _enforcement_payload(now)
    mismatch["new_value"] = "c" * 40
    assert external._enforcement_report(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        _write_json(tmp_path / "mismatch.json", mismatch),
        required=True,
        expected_action="accepted.advance",
        expected_resource="refs/heads/dev",
        expected_old="a" * 40,
        expected_new="b" * 40,
    )[1] == ["hosted_enforcement_receipt_binding_mismatch"]


def test_contract_validation_failure_edges() -> None:
    with pytest.raises(ValueError, match="action preview requires"):
        AdmissionDecision.action_preview(
            action="",
            resource="resource",
            blocked_actions=(),
            why=(),
        )
    with pytest.raises(ValueError, match="surrounding whitespace"):
        HolderRef.parse(" agent:codex:thread:id ")
    now = datetime.now(UTC)
    with pytest.raises(ValidationError, match="renewed_at must not precede"):
        LaneLease(
            lane_incarnation_id="lane:1",
            lease_id="lease:1",
            lane_ref="work/example",
            holder_ref=HolderRef.parse("agent:codex:thread:id"),
            epoch=1,
            issued_at=now,
            renewed_at=now - timedelta(seconds=1),
            expires_at=now,
        )
    with pytest.raises(ValidationError, match="expires_at must not precede"):
        LaneLease(
            lane_incarnation_id="lane:1",
            lease_id="lease:1",
            lane_ref="work/example",
            holder_ref=HolderRef.parse("agent:codex:thread:id"),
            epoch=1,
            issued_at=now,
            renewed_at=now,
            expires_at=now - timedelta(seconds=1),
        )
    with pytest.raises(ValidationError, match="valid_until must be later"):
        IdentityAssertion(
            identity_ref="identity",
            issuer="issuer",
            audience="audience",
            verification_method="method",
            valid_from=now,
            valid_until=now,
            attestation_digest="a" * 64,
        )
    handoff = CrossHostHandoff(
        source_lane_ref="work/example",
        source_head="a" * 40,
        source_tree="b" * 40,
        target_holder_ref=HolderRef.parse("agent:target:run:two"),
        context_digest="c" * 64,
        dirty_disposition="clean",
        source_lease_id="lease:1",
        source_lease_epoch=1,
        source_holder_ref=HolderRef.parse("agent:source:run:one"),
        artifacts=({"path": "context.md", "sha256": "d" * 64},),
    )
    assert handoff.to_payload()["destination_creates_local_incarnation"] is True
