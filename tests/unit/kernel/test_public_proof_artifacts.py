from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.proof_artifacts as proof_artifacts
from ethos.adapters.mutation.proof import attestation_store_dir
from ethos.adapters.mutation.proof import persist_proof_attestation
from tests.support.governed_repository import git
from tests.support.governed_repository import issue_conformant_proof
from tests.support.governed_repository import start_adopted_candidate

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def _reissue(record: Attestation, **updates: object) -> Attestation:
    payload = record.model_dump(mode="python", exclude={"id", "schema_version", "statement_digest"})
    return type(record).issue(payload | updates)


@pytest.mark.parametrize(
    ("checks", "empty_allowed", "error"),
    [
        (None, False, "proof_attestation_checks_required"),
        ([], False, "proof_attestation_checks_required"),
        (["invalid"], False, "proof_attestation_check_invalid"),
        (
            [
                {
                    "action_id": "gate",
                    "command": ["python", "-m", "pytest"],
                    "verdict": "pass",
                    "exit_code": 0,
                    "diagnostics": [{1: "invalid"}],
                }
            ],
            False,
            "proof_attestation_check_invalid:gate",
        ),
        (
            [
                {"action_id": "gate", "command": ["true"], "verdict": "pass"},
                {"action_id": "gate", "command": ["true"], "verdict": "pass"},
            ],
            False,
            "proof_attestation_check_duplicate",
        ),
    ],
)
def test_proof_check_envelope_fails_closed(
    checks: object, empty_allowed: object, error: str
) -> None:
    with pytest.raises((TypeError, ValueError), match=error):
        proof_artifacts.normalize_checks(checks, allow_empty=empty_allowed)


@pytest.mark.parametrize(
    ("mutation", "gap"),
    [
        ("missing", "proof_attestation_artifact_missing"),
        ("size", "proof_attestation_artifact_size_mismatch"),
        ("head", "proof_attestation_artifact_content_mismatch"),
        ("json", "proof_attestation_artifact_invalid"),
    ],
)
def test_public_proof_artifact_binding_fails_closed(
    tmp_path: Path, mutation: str, gap: str
) -> None:
    _repo, candidate = start_adopted_candidate(tmp_path)
    head = git(candidate, "rev-parse", "HEAD")
    record = issue_conformant_proof(candidate, head)
    persist_proof_attestation(candidate, record)
    raw_descriptor = record.statement["artifact"]
    assert isinstance(raw_descriptor, Mapping)
    descriptor = dict(raw_descriptor)
    store = attestation_store_dir(candidate)
    path = store / str(descriptor["path"])

    if mutation == "missing":
        path.unlink()
    elif mutation == "size":
        forged = _reissue(
            record,
            statement=record.statement
            | {"artifact": descriptor | {"size_bytes": path.stat().st_size + 1}},
        )
        assert proof_artifacts.artifact_checks(store, forged)[1] == [gap]
        return
    else:
        document = json.loads(path.read_text())
        path.write_text(
            "{" if mutation == "json" else json.dumps(document | {"head": "0" * 40}),
            encoding="utf-8",
        )
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        relative = f"artifacts/{digest}.json"
        rebound = descriptor | {
            "path": relative,
            "sha256": f"sha256:{digest}",
            "size_bytes": len(payload),
        }
        target = store / relative
        target.write_bytes(payload)
        forged = _reissue(
            record,
            statement=record.statement | {"artifact": rebound},
            evidence_refs=(f"sha256:{digest}",),
        )
        assert proof_artifacts.artifact_checks(store, forged)[1] == [gap]
        return

    assert proof_artifacts.artifact_checks(store, record)[1] == [gap]


def test_public_attestation_scan_rejects_filename_payload_and_identity_drift(
    tmp_path: Path,
) -> None:
    _repo, candidate = start_adopted_candidate(tmp_path)
    head = git(candidate, "rev-parse", "HEAD")
    record = issue_conformant_proof(candidate, head)
    store = attestation_store_dir(candidate)
    store.mkdir(parents=True, exist_ok=True)
    (store / "not-an-identity.json").write_text("{}")
    (store / f"{'0' * 64}.json").write_text("not-json")
    (store / f"{'1' * 64}.json").write_text(record.canonical_json())

    records, gaps = proof_artifacts.scan_attestations(store)

    assert records == ()
    assert gaps == [
        f"attestation_store_invalid:{'0' * 64}.json",
        f"attestation_store_identity_mismatch:{'1' * 64}.json",
        "attestation_store_filename_invalid:not-an-identity.json",
    ]
