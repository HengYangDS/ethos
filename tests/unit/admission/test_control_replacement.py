from __future__ import annotations

import json
import re
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import cast

import pytest

import ethos.adapters.admission.control.replacement as control_replacement
import ethos.adapters.admission.evidence.external as external_evidence
from ethos.adapters.mutation.proof import persist_proof_attestation
from ethos.adapters.mutation.proof import proof_attestation
from ethos.adapters.mutation.proof import proof_plan
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from ethos.contracts.rules import stable_digest
from ethos.contracts.semantic import Attestation
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.contract_helpers import start_adopted_candidate

if TYPE_CHECKING:
    from pathlib import Path


def _control_change(
    tmp_path: Path, relative_path: str = "system/gates.toml"
) -> tuple[Path, Path, str, str]:
    repo, candidate = start_adopted_candidate(tmp_path)
    accepted_head = git(repo, "rev-parse", "HEAD")
    candidate_head = commit_fixture_file(candidate, relative_path, "candidate control\n", "control")
    return repo, candidate, accepted_head, candidate_head


def _trusted_receipt(
    tmp_path: Path,
    monkeypatch,
    request: dict[str, object],
    **overrides: object,
) -> Path:
    store = tmp_path / "receipts"
    store.mkdir(exist_ok=True)
    provider = external_evidence.IndependentVerificationProvider(
        receipt_store=store,
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
    )
    monkeypatch.setattr(
        control_replacement,
        "load_independent_verification_provider",
        lambda _path: (provider, []),
    )
    monkeypatch.setattr(
        control_replacement, "default_provider_config_path", lambda: tmp_path / "provider.toml"
    )
    monkeypatch.setattr(
        control_replacement,
        "verify_independent_receipt_signature",
        lambda receipt, configured: receipt.signature == "signed" and configured == provider,
    )
    now = datetime.now(UTC)
    payload = {
        **request,
        "implementation_digest": provider.implementation_digest,
        "result": "pass",
        "issuer": "provider:example",
        "key_id": "provider:example",
        "signature_algorithm": "ssh-ed25519",
        "signature": "signed",
        "issued_at": now,
        "valid_until": now + timedelta(minutes=5),
        "payload_digest": "",
        **overrides,
    }
    receipt = IndependentVerificationReceipt.model_validate(payload)
    receipt = receipt.model_copy(update={"payload_digest": receipt.canonical_payload_digest()})
    path = store / "receipt.json"
    path.write_text(json.dumps(receipt.model_dump(mode="json")), encoding="utf-8")
    return path


def test_non_control_change_needs_no_independent_verification(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    candidate_head = commit_fixture_file(candidate, "README.md", "# candidate\n", "docs")

    report = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=candidate_head,
    )

    assert report["required"] is False
    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    assert report["subject"] == {}
    assert report["independent_verification"] == {}


def test_control_change_projects_signed_verification_subject(tmp_path: Path) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)

    report = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    subject = cast("dict[str, object]", report["subject"])
    accepted = cast("dict[str, object]", subject["accepted"])
    candidate_subject = cast("dict[str, object]", subject["candidate"])
    assert report["control_paths"] == ["system/gates.toml"]
    assert subject["schema_version"] == 1
    assert subject["kind"] == "control-replacement"
    assert accepted["head"] == accepted_head
    assert candidate_subject["head"] == candidate_head
    assert accepted["tree"] == git(candidate, "rev-parse", f"{accepted_head}^{{tree}}")
    assert candidate_subject["tree"] == git(candidate, "rev-parse", f"{candidate_head}^{{tree}}")
    assert re.fullmatch(r"[0-9a-f]{64}", str(accepted["control_digest"]))
    assert re.fullmatch(r"[0-9a-f]{64}", str(candidate_subject["control_digest"]))
    assert accepted["control_digest"] != candidate_subject["control_digest"]
    assert candidate_subject["executed_proof_digest"]

    request = cast("dict[str, object]", report["verification_request"])
    assert request["proof_floor_id"] == "ethos:control-replacement:v1"
    assert request["proof_floor_digest"] == stable_digest(subject)
    assert request["commit"] == candidate_head
    assert request["tree"] == candidate_subject["tree"]
    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["independent_verification_receipt_required"]


def test_equivalent_proof_does_not_change_control_replacement_subject(tmp_path: Path) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)
    before = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    plan = proof_plan(candidate, head=candidate_head)
    first = proof_attestation(candidate, candidate_head, expected_plan=plan)
    assert first is not None
    equivalent = Attestation.issue(
        first.model_dump(exclude={"id", "schema_version", "statement_digest"})
        | {"issued_at": first.issued_at + timedelta(seconds=1)}
    )
    persist_proof_attestation(candidate, equivalent)

    after = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    assert after["subject"] == before["subject"]
    assert after["verification_request"] == before["verification_request"]


def test_control_replacement_accepts_only_the_existing_signed_receipt_contract(
    tmp_path: Path, monkeypatch
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)
    pending = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    request = cast("dict[str, object]", pending["verification_request"])
    receipt = _trusted_receipt(tmp_path, monkeypatch, request)

    report = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=receipt,
    )

    assert report["verdict"] == "pass"
    assert report["required_gaps"] == []
    verification = cast("dict[str, object]", report["independent_verification"])
    assert verification["verdict"] == "pass"
    assert "ok" not in verification
    assert verification["evidence_class"] == "independently_reexecuted"


def test_unsigned_custom_and_mismatched_signed_receipts_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)
    pending = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    request = cast("dict[str, object]", pending["verification_request"])
    receipt = _trusted_receipt(tmp_path, monkeypatch, request)
    receipt.write_text(
        json.dumps(
            {
                "kind": "control-replacement-verifier",
                "accepted_head": accepted_head,
                "candidate_head": candidate_head,
                "verdict": "pass",
            }
        ),
        encoding="utf-8",
    )
    custom = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=receipt,
    )
    assert custom["required_gaps"] == ["independent_verification_receipt_invalid"]

    receipt = _trusted_receipt(tmp_path, monkeypatch, request, proof_floor_digest="0" * 64)
    mismatch = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=receipt,
    )
    assert mismatch["required_gaps"] == ["independent_verification_receipt_binding_mismatch"]


def test_missing_executed_proof_and_untrusted_receipt_location_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    missing = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    assert missing["required_gaps"] == ["proof_not_proven"]

    seed_executed_proof(candidate, candidate_head)
    pending = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    request = cast("dict[str, object]", pending["verification_request"])
    trusted = _trusted_receipt(tmp_path, monkeypatch, request)
    outside = tmp_path / "outside.json"
    outside.write_bytes(trusted.read_bytes())
    report = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=outside,
    )
    assert report["required_gaps"] == ["independent_verification_receipt_outside_store"]


@pytest.mark.parametrize(
    "relative_path",
    [
        "src/ethos/repository/adoption/evolution.py",
        "src/ethos/repository/context.py",
        "src/ethos/contracts/workflow.py",
        "src/ethos/contracts/policy/cel.py",
        "src/ethos/adapters/repo/git.py",
    ],
)
def test_control_paths_require_independent_verification(
    tmp_path: Path,
    relative_path: str,
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path, relative_path)
    seed_executed_proof(candidate, candidate_head)

    report = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    assert report["required"] is True
    assert report["control_paths"] == [relative_path]
    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["independent_verification_receipt_required"]


def test_control_change_digest_binds_git_mode(tmp_path: Path) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    commit_fixture_file(repo, "system/gates.toml", "version = 1\n", "control")
    accepted_head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted_head)
    control = candidate / "system" / "gates.toml"
    control.chmod(0o755)
    git(candidate, "add", ".")
    git(candidate, "commit", "-m", "mode")
    candidate_head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, candidate_head)

    report = control_replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    subject = cast("dict[str, object]", report["subject"])
    accepted = cast("dict[str, object]", subject["accepted"])
    candidate_subject = cast("dict[str, object]", subject["candidate"])
    assert report["control_paths"] == ["system/gates.toml"]
    assert accepted["control_digest"] != candidate_subject["control_digest"]
    assert report["required_gaps"] == ["independent_verification_receipt_required"]


def test_unresolvable_git_subject_defers_instead_of_allowing(tmp_path: Path) -> None:
    report = control_replacement.control_replacement_report(
        candidate_root=tmp_path,
        accepted_head="a" * 40,
        candidate_head="b" * 40,
    )

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["control_replacement_diff_unavailable"]
