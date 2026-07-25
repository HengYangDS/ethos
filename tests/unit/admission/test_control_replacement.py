from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING
from typing import cast

from ethos.adapters.admission.control import replacement
from ethos.adapters.admission.evidence import external
from ethos.adapters.mutation.proof import executed_proof_record
from ethos_core.contracts.evidence.external import IndependentVerificationReceipt
from ethos_core.contracts.rules import stable_digest
from tests.support.contract_helpers import commit_fixture_file
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import init_repo_with_candidate
from tests.support.contract_helpers import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path


def _control_change(
    tmp_path: Path, relative_path: str = "system/gates.toml"
) -> tuple[Path, Path, str, str]:
    repo, candidate = init_repo_with_candidate(tmp_path)
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
    provider = external.IndependentVerificationProvider(
        receipt_store=store,
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
    )
    monkeypatch.setattr(
        replacement,
        "load_independent_verification_provider",
        lambda _path: (provider, []),
    )
    monkeypatch.setattr(
        replacement, "default_provider_config_path", lambda: tmp_path / "provider.toml"
    )
    monkeypatch.setattr(
        replacement,
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

    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=git(repo, "rev-parse", "HEAD"),
        candidate_head=candidate_head,
    )

    assert report["required"] is False
    assert report["verdict"] == "allow"
    assert report["required_gaps"] == []
    assert report["subject"] == {}
    assert report["independent_verification"] == {}


def test_control_change_projects_exact_signed_verification_subject(tmp_path: Path) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)

    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )

    record = executed_proof_record(candidate, candidate_head)
    assert record is not None
    evidence = cast("dict[str, object]", record["evidence"])
    subject = cast("dict[str, object]", report["subject"])
    assert subject == {
        "schema_version": 1,
        "kind": "control-replacement",
        "accepted": {
            "head": accepted_head,
            "tree": git(candidate, "rev-parse", f"{accepted_head}^{{tree}}"),
            "control_digest": replacement._control_digest(
                candidate, accepted_head, ("system/gates.toml",)
            ),
        },
        "candidate": {
            "head": candidate_head,
            "tree": git(candidate, "rev-parse", f"{candidate_head}^{{tree}}"),
            "control_digest": replacement._control_digest(
                candidate, candidate_head, ("system/gates.toml",)
            ),
            "executed_proof_digest": evidence["digest"],
        },
        "control_paths": ["system/gates.toml"],
    }
    request = cast("dict[str, object]", report["verification_request"])
    assert request["proof_floor_id"] == "ethos:control-replacement:v1"
    assert request["proof_floor_digest"] == stable_digest(subject)
    assert request["commit"] == candidate_head
    assert request["tree"] == cast("dict[str, object]", subject["candidate"])["tree"]
    assert report["required_gaps"] == ["independent_verification_receipt_required"]


def test_control_replacement_accepts_only_the_existing_signed_receipt_contract(
    tmp_path: Path, monkeypatch
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)
    pending = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    request = cast("dict[str, object]", pending["verification_request"])
    receipt = _trusted_receipt(tmp_path, monkeypatch, request)

    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=receipt,
    )

    assert report["verdict"] == "allow"
    assert report["required_gaps"] == []
    verification = cast("dict[str, object]", report["independent_verification"])
    assert verification["ok"] is True
    assert verification["evidence_class"] == "independently_reexecuted"


def test_unsigned_custom_and_mismatched_signed_receipts_fail_closed(
    tmp_path: Path, monkeypatch
) -> None:
    _repo, candidate, accepted_head, candidate_head = _control_change(tmp_path)
    seed_executed_proof(candidate, candidate_head)
    pending = replacement.control_replacement_report(
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
                "verdict": "allow",
            }
        ),
        encoding="utf-8",
    )
    custom = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=receipt,
    )
    assert custom["required_gaps"] == ["independent_verification_receipt_invalid"]

    receipt = _trusted_receipt(tmp_path, monkeypatch, request, proof_floor_digest="0" * 64)
    mismatch = replacement.control_replacement_report(
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
    missing = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    assert missing["required_gaps"] == ["control_replacement_candidate_proof_not_proven"]

    seed_executed_proof(candidate, candidate_head)
    pending = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
    )
    request = cast("dict[str, object]", pending["verification_request"])
    trusted = _trusted_receipt(tmp_path, monkeypatch, request)
    outside = tmp_path / "outside.json"
    outside.write_bytes(trusted.read_bytes())
    report = replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted_head,
        candidate_head=candidate_head,
        independent_verification_receipt=outside,
    )
    assert report["required_gaps"] == ["independent_verification_receipt_outside_store"]


def test_control_surface_uses_few_broad_prefixes_and_binds_git_mode(tmp_path: Path) -> None:
    required = {
        "packages/ethos/src/ethos/repository/adoption/evolution.py",
        "packages/ethos/src/ethos/repository/context.py",
        "packages/ethos-core/src/ethos_core/contracts/workflow.py",
        "packages/ethos-core/src/ethos_core/contracts/policy/cel.py",
        "packages/ethos/src/ethos/adapters/repo/git.py",
    }
    assert all(replacement._is_control_path(path) for path in required)
    assert replacement._is_control_path("packages/ethos/README.md") is False

    repo = init_git_repo(tmp_path / "mode")
    control = repo / "system" / "gates.toml"
    control.parent.mkdir(parents=True)
    control.write_text("version = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "control")
    accepted_head = git(repo, "rev-parse", "HEAD")
    control.chmod(0o755)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "mode")
    candidate_head = git(repo, "rev-parse", "HEAD")

    assert replacement._control_digest(
        repo, accepted_head, ("system/gates.toml",)
    ) != replacement._control_digest(repo, candidate_head, ("system/gates.toml",))


def test_unresolvable_git_subject_defers_instead_of_allowing(tmp_path: Path) -> None:
    report = replacement.control_replacement_report(
        candidate_root=tmp_path,
        accepted_head="a" * 40,
        candidate_head="b" * 40,
    )

    assert report["verdict"] == "defer"
    assert report["required_gaps"] == ["control_replacement_diff_unavailable"]
