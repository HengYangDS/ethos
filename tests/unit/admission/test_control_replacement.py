"""Require trusted predecessor policy for exact control-plane replacement."""

from __future__ import annotations

import json
import re
import tomllib
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest
import tomli_w

import ethos.adapters.admission.control.replacement as replacement
import ethos.adapters.admission.evidence.external as evidence
from ethos.adapters.mutation.proof import proof_attestation
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from ethos.contracts.semantic import canonical_json_digest
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.literal_cases import literal_case
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path


def _control_change(
    tmp_path: Path, path: str = "system/gates.toml", mode: str = "required"
) -> tuple[Path, str, str]:
    repo, candidate = start_adopted_candidate(tmp_path, docs_only=True)
    (repo / "system/gates.toml").rename(repo / ".ethos/fixture-proof.toml")
    profile = repo / ".ethos/profile.toml"
    profile.write_text(
        profile.read_text().replace(
            'gate_registry = "system/gates.toml"',
            'gate_registry = ".ethos/fixture-proof.toml"',
        )
        + f'\n[independent_verification]\nmode = "{mode}"\n',
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    accepted = commit_fixture(repo, "configure independent verification")
    git(candidate, "reset", "--hard", accepted)
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


@pytest.fixture(autouse=True)
def configured_provider(tmp_path, monkeypatch):
    provider = evidence.IndependentVerificationProvider(
        receipt_store=tmp_path / "receipts",
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
        issuer="provider:example",
        key_id="provider:example",
    )
    provider.receipt_store.mkdir()
    monkeypatch.setattr(
        evidence, "load_independent_verification_provider", lambda _path: (provider, [])
    )
    monkeypatch.setattr(
        evidence, "default_provider_config_path", lambda: tmp_path / "provider.toml"
    )
    monkeypatch.setattr(
        evidence,
        "verify_independent_receipt_signature",
        lambda receipt, configured: receipt.signature == "signed" and configured == provider,
    )


def _trusted_receipt(request: dict[str, object], **updates: object) -> Path:
    provider, gaps = evidence.load_independent_verification_provider(
        evidence.default_provider_config_path()
    )
    assert provider is not None
    assert not gaps
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
    path = provider.receipt_store / "receipt.json"
    path.write_text(json.dumps(receipt.model_dump(mode="json")))
    return path


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


def test_receipt_and_proof_negative_matrix_fails_closed(tmp_path: Path) -> None:
    candidate, accepted, head = _control_change(tmp_path)
    assert _report(candidate, accepted, head)["required_gaps"] == ["proof_not_proven"]
    seed_executed_proof(candidate, head)
    request = cast("dict[str, object]", _report(candidate, accepted, head)["verification_request"])
    custom = _trusted_receipt(request)
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
            _trusted_receipt(request, **{field: wrong}),
        )
        assert report["required_gaps"] == ["independent_verification_receipt_binding_mismatch"], (
            field
        )
    trusted = _trusted_receipt(request)
    accepted_receipt = _report(candidate, accepted, head, trusted)
    assert (accepted_receipt["verdict"], accepted_receipt["required_gaps"]) == ("pass", [])
    verification = accepted_receipt["independent_verification"]
    assert (verification["verdict"], verification["evidence_class"]) == (
        "pass",
        "independently_reexecuted",
    )
    assert "ok" not in verification
    outside = tmp_path / "outside.json"
    outside.write_bytes(trusted.read_bytes())
    assert _report(candidate, accepted, head, outside)["required_gaps"] == [
        "independent_verification_receipt_outside_store"
    ]


@pytest.mark.parametrize(
    "path",
    [
        "README.md",
        *literal_case(
            "admission.test_control_replacement:parametrize:test_control_path_matrix_requires_independent_verification:1"
        ),
        "src/ethos/adapters/repo/runtime/selection.py",
        "src/ethos/adapters/repo/hook/protocol.py",
        "src/ethos/adapters/repo/hook/admission.py",
        "src/ethos/adapters/repo/git_effects.py",
        "src/ethos/domain/status.py",
        "src/ethos/repository/audit.py",
        "src/ethos/repository/release/configuration.py",
    ],
)
def test_control_path_matrix_requires_independent_verification(
    tmp_path: Path, path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inspect the control-path policy with an admitted proof as an explicit prerequisite."""
    candidate, accepted, head = _control_change(tmp_path, path)
    proof = SimpleNamespace(
        id="a" * 64,
        plan_digest="b" * 64,
        policy_digest="c" * 64,
        payload=SimpleNamespace(body={"fixture": "admitted proof"}),
    )
    monkeypatch.setattr(replacement, "proof_for_repository_transition", lambda *_args: (proof, []))
    report = _report(candidate, accepted, head)
    if path == "README.md":
        assert (report["required"], report["verdict"], report["required_gaps"]) == (
            False,
            "pass",
            [],
        )
        assert report["subject"] == report["independent_verification"] == {}
        return
    assert (
        report["required"],
        report["control_paths"],
        report["verdict"],
        report["required_gaps"],
    ) == (True, [path], "unknown", ["independent_verification_receipt_required"])


def test_control_digest_binds_git_mode(tmp_path: Path) -> None:
    candidate, _accepted, accepted = _control_change(tmp_path)
    (candidate / "system/gates.toml").chmod(0o755)
    head = commit_fixture_file(candidate, "system/gates.toml", "candidate control\n", "mode")
    seed_executed_proof(candidate, head)
    report = _report(candidate, accepted, head)
    subject = cast("dict[str, dict[str, object]]", report["subject"])
    assert report["control_paths"] == ["system/gates.toml"]
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


@pytest.mark.parametrize("prior", ["required", "disabled"])
def test_candidate_cannot_disable_trusted_predecessor_verification(
    tmp_path: Path, prior: str
) -> None:
    """Either committed object can require verification; dirty policy cannot disable it."""
    candidate, accepted, _head = _control_change(tmp_path, mode=prior)
    profile = candidate / ".ethos/profile.toml"
    proposed = "disabled" if prior == "required" else "required"
    head = commit_fixture_file(
        candidate,
        ".ethos/profile.toml",
        profile.read_text().replace(f'mode = "{prior}"', f'mode = "{proposed}"'),
        "change verifier policy",
    )
    seed_executed_proof(candidate, head)
    profile.write_text(profile.read_text().replace('mode = "required"', 'mode = "disabled"'))
    report = _report(candidate, accepted, head)
    assert report["verdict"] != "pass", report
    assert report["required_gaps"] == ["independent_verification_receipt_required"]


def test_changed_gate_does_not_enable_an_unselected_external_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A changed floor is review input, not an implicit external-provider policy."""
    candidate, accepted, _head = _control_change(tmp_path, mode="disabled")
    registry = candidate / ".ethos/fixture-proof.toml"
    payload = tomllib.loads(registry.read_text())
    old = payload["proof_sets"]["default"][0]
    selected = next(gate for gate in payload["gates"] if gate["id"] == old)
    selected["command"] = ["git", "--version"]
    head = commit_fixture_file(
        candidate, ".ethos/fixture-proof.toml", tomli_w.dumps(payload), "change proof floor"
    )
    seed_executed_proof(candidate, head)
    monkeypatch.setattr(
        evidence,
        "load_independent_verification_provider",
        lambda _path: pytest.fail("disabled policy must not inspect host configuration"),
    )
    report = _report(candidate, accepted, head)
    assert report["verdict"] == "pass", report
    assert report["independent_verification"]["state"] == "disabled"
    assert report["mints_authority"] is False
    assert old in report["subject"]["verification_floor"]["changed_obligations"]
