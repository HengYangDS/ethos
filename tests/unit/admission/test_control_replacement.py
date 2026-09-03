from __future__ import annotations

import json
import re
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import ethos.adapters.admission.control.replacement as replacement
import ethos.adapters.admission.evidence.external as evidence
from ethos.adapters.mutation.proof import proof_attestation
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from ethos.contracts.semantic import canonical_json_digest
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import seed_executed_proof
from tests.support.governed_repository import start_adopted_candidate
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


def _control_change(
    tmp_path: Path, path: str = "system/gates.toml", mode: str = "required"
) -> tuple[Path, str, str]:
    repo, candidate = start_adopted_candidate(tmp_path)
    accepted = git(repo, "rev-parse", "HEAD")
    profile = candidate / ".ethos/profile.toml"
    profile.write_text(profile.read_text() + f'\n[independent_verification]\nmode = "{mode}"\n')
    return (
        candidate,
        accepted,
        commit_fixture_file(candidate, path, "candidate control\n", "control"),
    )


def _report(candidate: Path, accepted: str, head: str, receipt: Path | None = None):
    return replacement.control_replacement_report(
        candidate_root=candidate,
        accepted_head=accepted,
        candidate_head=head,
        independent_verification_receipt=receipt,
    )


def _trusted_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, request: dict[str, object], **updates: object
) -> Path:
    store = tmp_path / "receipts"
    store.mkdir(exist_ok=True)
    provider = evidence.IndependentVerificationProvider(
        receipt_store=store,
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
        issuer="provider:example",
        key_id="provider:example",
    )
    monkeypatch.setattr(
        replacement, "load_independent_verification_provider", lambda _path: (provider, [])
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
    receipt = IndependentVerificationReceipt.model_validate(
        {
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
            **updates,
        }
    )
    receipt = receipt.model_copy(update={"payload_digest": receipt.canonical_payload_digest()})
    path = store / "receipt.json"
    path.write_text(json.dumps(receipt.model_dump(mode="json")))
    return path


def test_non_control_change_bypasses_independent_verification(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    candidate = tmp_path / "candidate"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate, "dev")
    report = _report(
        candidate,
        git(repo, "rev-parse", "HEAD"),
        commit_fixture_file(candidate, "README.md", "# candidate\n", "docs"),
    )
    assert {
        key: report[key]
        for key in ("required", "verdict", "required_gaps", "subject", "independent_verification")
    } == {
        "required": False,
        "verdict": "pass",
        "required_gaps": [],
        "subject": {},
        "independent_verification": {},
    }


def test_control_subject_and_request_bind_exact_signed_git_state(tmp_path: Path) -> None:
    candidate, accepted, head = _control_change(tmp_path)
    seed_executed_proof(candidate, head)
    report = _report(candidate, accepted, head)
    subject = cast("dict[str, object]", report["subject"])
    before, after = (cast("dict[str, object]", subject[key]) for key in ("accepted", "candidate"))
    proof = proof_attestation(candidate, head)
    assert proof
    assert (report["control_paths"], subject["schema_version"], subject["kind"]) == (
        ["system/gates.toml"],
        1,
        "control-replacement",
    )
    assert (before["head"], after["head"], before["tree"], after["tree"]) == (
        accepted,
        head,
        git(candidate, "rev-parse", f"{accepted}^{{tree}}"),
        git(candidate, "rev-parse", f"{head}^{{tree}}"),
    )
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", str(item["control_digest"])) for item in (before, after)
    )
    assert before["control_digest"] != after["control_digest"]
    assert after["proof"] == {
        "attestation": proof.id,
        "statement": canonical_json_digest(proof.payload.body),
        "plan": proof.plan_digest,
    }
    request = cast("dict[str, object]", report["verification_request"])
    assert request == {
        "remote": "local",
        "commit": head,
        "tree": after["tree"],
        "action": "control-replacement",
        "proof_floor_id": "ethos:control-replacement:v1",
        "proof_floor_digest": canonical_json_digest(subject),
        "policy_digest": proof.policy_digest,
        "implementation_digest": "",
    }
    assert (report["verdict"], report["required_gaps"]) == (
        "unknown",
        ["independent_verification_receipt_required"],
    )


@pytest.mark.parametrize(
    ("mode", "verdict", "state", "gaps"),
    literal_case(
        "admission.test_control_replacement:parametrize:test_control_policy_modes_fail_closed:0"
    ),
)
def test_control_policy_modes_fail_closed(
    tmp_path: Path, mode: str, verdict: str, state: str, gaps: list[str]
) -> None:
    candidate, accepted, head = _control_change(tmp_path, mode=mode)
    seed_executed_proof(candidate, head)
    report = _report(candidate, accepted, head)
    assert report["required"] is True
    assert (
        report["verdict"],
        report["required_gaps"],
        report["independent_verification"]["state"],
    ) == (verdict, gaps, state)


def test_only_existing_exact_signed_receipt_contract_is_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate, accepted, head = _control_change(tmp_path)
    seed_executed_proof(candidate, head)
    request = cast("dict[str, object]", _report(candidate, accepted, head)["verification_request"])
    report = _report(candidate, accepted, head, _trusted_receipt(tmp_path, monkeypatch, request))
    verification = cast("dict[str, object]", report["independent_verification"])
    assert (
        report["verdict"],
        report["required_gaps"],
        verification["verdict"],
        verification["evidence_class"],
    ) == ("pass", [], "pass", "independently_reexecuted")
    assert "ok" not in verification


def test_receipt_and_proof_negative_matrix_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate, accepted, head = _control_change(tmp_path)
    assert _report(candidate, accepted, head)["required_gaps"] == ["proof_not_proven"]
    seed_executed_proof(candidate, head)
    request = cast("dict[str, object]", _report(candidate, accepted, head)["verification_request"])
    custom = _trusted_receipt(tmp_path, monkeypatch, request)
    custom.write_text(json.dumps({"kind": "control-replacement-verifier", "verdict": "pass"}))
    assert _report(candidate, accepted, head, custom)["required_gaps"] == [
        "independent_verification_receipt_invalid"
    ]
    for field, wrong in (
        ("commit", "0" * 40),
        ("tree", "0" * 40),
        ("action", "release"),
        ("proof_floor_id", "ethos:wrong:v1"),
        ("proof_floor_digest", "0" * 64),
        ("policy_digest", "0" * 64),
        ("implementation_digest", "0" * 64),
        ("issuer", "provider:wrong"),
        ("key_id", "provider:wrong"),
    ):
        report = _report(
            candidate,
            accepted,
            head,
            _trusted_receipt(tmp_path, monkeypatch, request, **{field: wrong}),
        )
        assert report["required_gaps"] == ["independent_verification_receipt_binding_mismatch"], (
            field
        )
    trusted = _trusted_receipt(tmp_path, monkeypatch, request)
    outside = tmp_path / "outside.json"
    outside.write_bytes(trusted.read_bytes())
    assert _report(candidate, accepted, head, outside)["required_gaps"] == [
        "independent_verification_receipt_outside_store"
    ]


@pytest.mark.parametrize(
    "path",
    literal_case(
        "admission.test_control_replacement:parametrize:test_control_path_matrix_requires_independent_verification:1"
    ),
)
def test_control_path_matrix_requires_independent_verification(tmp_path: Path, path: str) -> None:
    candidate, accepted, head = _control_change(tmp_path, path)
    seed_executed_proof(candidate, head)
    report = _report(candidate, accepted, head)
    assert (
        report["required"],
        report["control_paths"],
        report["verdict"],
        report["required_gaps"],
    ) == (True, [path], "unknown", ["independent_verification_receipt_required"])


def test_control_digest_binds_git_mode(tmp_path: Path) -> None:
    repo, candidate = start_adopted_candidate(tmp_path)
    commit_fixture_file(repo, "system/gates.toml", "version = 1\n", "control")
    accepted = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", accepted)
    profile = candidate / ".ethos/profile.toml"
    profile.write_text(profile.read_text() + '\n[independent_verification]\nmode = "required"\n')
    (candidate / "system/gates.toml").chmod(0o755)
    git(candidate, "add", ".")
    git(candidate, "commit", "-m", "mode")
    head = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, head)
    report = _report(candidate, accepted, head)
    subject = cast("dict[str, dict[str, object]]", report["subject"])
    assert set(report["control_paths"]) == {".ethos/profile.toml", "system/gates.toml"}
    assert subject["accepted"]["control_digest"] != subject["candidate"]["control_digest"]
    assert report["required_gaps"] == ["independent_verification_receipt_required"]


def test_control_replacement_uses_semantic_identity_for_the_outer_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = ".ethos/规则.toml"
    candidate, accepted, head = _control_change(tmp_path, path)
    git(candidate, "config", "core.quotePath", "false")
    monkeypatch.setattr(
        replacement,
        "proof_for_repository_transition",
        lambda _root, _head: (
            SimpleNamespace(
                id="a" * 64,
                payload=SimpleNamespace(body={"statement": "验证"}),
                plan_digest="b" * 64,
                policy_digest="c" * 64,
            ),
            [],
        ),
    )

    report = _report(candidate, accepted, head)
    subject = cast("dict[str, object]", report["subject"])
    request = cast("dict[str, object]", report["verification_request"])
    entry = replacement.git.run_git(
        candidate, "ls-tree", "-z", head, "--", path, check=False, text=False
    ).stdout
    content = replacement.git.run_git(
        candidate, "show", f"{head}:{path}", check=False, text=False
    ).stdout
    expected_snapshot_bytes = (
        b'[{"path":".ethos/\xe8\xa7\x84\xe5\x88\x99.toml","present":true,"sha256":"'
        + replacement.hashlib.sha256(content).hexdigest().encode("ascii")
        + b'","tree_entry_sha256":"'
        + replacement.hashlib.sha256(entry).hexdigest().encode("ascii")
        + b'"}]'
    )

    candidate_subject = cast("dict[str, object]", subject["candidate"])
    assert (
        candidate_subject["control_digest"]
        == replacement.hashlib.sha256(expected_snapshot_bytes).hexdigest()
    )
    assert request["proof_floor_digest"] == canonical_json_digest(subject)


def test_unresolvable_git_subject_defers_instead_of_allowing(tmp_path: Path) -> None:
    report = _report(tmp_path, "a" * 40, "b" * 40)
    assert (report["verdict"], report["required_gaps"]) == (
        "unknown",
        ["control_replacement_diff_unavailable"],
    )
