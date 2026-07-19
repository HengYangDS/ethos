from __future__ import annotations

# ruff: noqa: ARG005
import hashlib
import json
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

import ethos.adapters.admission.control.replacement as replacement
from ethos_core.contracts.admission import AdmissionDecision
from ethos_core.contracts.coordination import CrossHostHandoff
from ethos_core.contracts.coordination import HolderRef
from ethos_core.contracts.coordination import LaneLease

if TYPE_CHECKING:
    from pathlib import Path


def _write_json(path: Path, payload: object) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"command": "prove", "ok": True, "state": "proven", "data": {}},
        {
            "command": "prove",
            "ok": True,
            "state": "proven",
            "data": {"executed": True, "evidence": [], "provenance": {}},
        },
        {
            "command": "prove",
            "ok": True,
            "state": "proven",
            "data": {"executed": True, "evidence": {}, "provenance": []},
        },
        {
            "command": "prove",
            "ok": True,
            "state": "proven",
            "data": {"executed": True, "evidence": {}, "provenance": {}},
        },
        {
            "command": "prove",
            "ok": True,
            "state": "proven",
            "data": {
                "executed": True,
                "evidence": {},
                "provenance": {"predicate": {"head": "b"}},
            },
        },
        {
            "command": "prove",
            "ok": True,
            "state": "proven",
            "data": {
                "executed": True,
                "evidence": {"head": "a"},
                "provenance": {"predicate": {"head": "b"}},
            },
        },
    ],
)
def test_native_proof_parser_fails_closed_for_noncanonical_payloads(
    payload: object,
) -> None:
    assert replacement._native_executed_proof_head(payload) == ""  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch


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
    undecodable = tmp_path / "undecodable.json"
    undecodable.write_bytes(b"\xff")
    assert replacement._external_receipt(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        path=undecodable,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )[1] == ["control_replacement_receipt_invalid"]
    completed = subprocess.CompletedProcess(["git"], 1, stdout="", stderr="bad")
    original = replacement.subprocess.run
    replacement.subprocess.run = lambda *args, **kwargs: completed
    try:
        report = replacement.control_replacement_report(
            candidate_root=candidate,
            accepted_head="a",
            candidate_head="b",
        )
        assert report["required"] is True
        assert report["verdict"] == "defer"
        assert report["required_gaps"] == ["control_replacement_diff_unavailable"]
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

    receipt["candidate_proof_path"] = inside.as_posix()
    gaps = replacement._receipt_gaps(  # noqa: RUF100, SLF001 - coverage exercises an exact internal fail-closed branch
        receipt,
        accepted_head="a",
        candidate_head="b",
        candidate_root=candidate,
    )
    assert "control_replacement_candidate_proof_inside_candidate_tree" in gaps


def test_control_digest_fails_closed_when_tree_probe_errors(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        replacement.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 128, stdout=b""),
    )

    assert (
        replacement._control_digest(  # noqa: RUF100, SLF001 - coverage exercises exact Git failure handling
            tmp_path,
            "a" * 40,
            ("system/gates.toml",),
        )
        is None
    )

    monkeypatch.setattr(
        replacement.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0],
            0 if "ls-tree" in args[0] else 128,
            stdout=b"entry" if "ls-tree" in args[0] else b"",
        ),
    )
    assert (
        replacement._control_digest(  # noqa: RUF100, SLF001 - coverage exercises exact Git failure handling
            tmp_path,
            "a" * 40,
            ("system/gates.toml",),
        )
        is None
    )

    monkeypatch.setattr(replacement, "_control_digest", lambda *_args: None)
    assert replacement._control_snapshot_gaps(  # noqa: RUF100, SLF001 - coverage exercises fail-closed snapshot admission
        {},
        root=tmp_path,
        accepted_head="a",
        candidate_head="b",
        control_paths=("system/gates.toml",),
    ) == ["control_replacement_control_snapshot_unavailable"]


def test_replacement_read_failures_and_invalid_decision_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    blocked = tmp_path / "blocked.json"
    blocked.write_text("{}", encoding="utf-8")
    path_type = type(blocked)
    original_read_bytes = path_type.read_bytes

    def read_bytes(path):
        if path == blocked:
            msg = "blocked"
            raise OSError(msg)
        return original_read_bytes(path)

    monkeypatch.setattr(path_type, "read_bytes", read_bytes)
    artifacts, artifact_gaps = replacement._external_artifacts(  # noqa: RUF100, SLF001 - coverage exercises exact read failure handling
        {
            "verifier_path": blocked.as_posix(),
            "bootstrap_decision_path": blocked.as_posix(),
        },
        candidate,
    )
    assert artifacts == {}
    assert artifact_gaps == [
        "control_replacement_verifier_missing",
        "bootstrap_decision_missing",
    ]
    assert replacement._candidate_proof_gaps(  # noqa: RUF100, SLF001 - coverage exercises exact proof read failure handling
        {"candidate_proof_path": blocked.as_posix()}, candidate, "b"
    ) == ["control_replacement_candidate_proof_not_proven"]
    assert replacement._bootstrap_decision_gaps(  # noqa: RUF100, SLF001 - coverage exercises invalid decision type
        [], receipt={}, accepted_head="a", candidate_head="b"
    ) == ["control_replacement_bootstrap_decision_invalid"]


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
