from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.proof_artifacts as proof_artifacts
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof_artifacts import proof_artifact_root
from ethos.adapters.repo.attestation_set import read_attestation_set
from tests.support.governed_repository import git
from tests.support.governed_repository import issue_conformant_proof
from tests.support.governed_repository import start_adopted_candidate

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.contracts.semantic import Attestation


def _reissue(record: Attestation, **updates: object) -> Attestation:
    body = updates.pop("body", None)
    payload = record.model_dump(mode="python", exclude={"id"})
    if body is not None:
        payload["payload"] = {"kind": record.payload.kind, "body": body}
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
    raw_descriptor = record.payload.body["artifact"]
    assert isinstance(raw_descriptor, Mapping)
    descriptor = dict(raw_descriptor)
    store = proof_artifact_root(candidate)
    path = store / str(descriptor["path"])

    if mutation == "missing":
        path.unlink()
    elif mutation == "size":
        forged = _reissue(
            record,
            body=record.payload.body
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
            body=record.payload.body | {"artifact": rebound},
            evidence_refs=(f"sha256:{digest}",),
        )
        assert proof_artifacts.artifact_checks(store, forged)[1] == [gap]
        return

    assert proof_artifacts.artifact_checks(store, record)[1] == [gap]


def test_poisoned_local_attestation_copy_cannot_block_selected_set(
    tmp_path: Path,
) -> None:
    _repo, candidate = start_adopted_candidate(tmp_path)
    head = git(candidate, "rev-parse", "HEAD")
    record = issue_conformant_proof(candidate, head)
    poison = proof_artifact_root(candidate) / f"{record.id}.json"
    poison.parent.mkdir(parents=True, exist_ok=True)
    poison.write_text("{}", encoding="utf-8")

    persist_proof_attestation(candidate, record)

    _root, selected = read_attestation_set(candidate)
    assert selected == (record,)
    assert poison.read_text(encoding="utf-8") == "{}"
