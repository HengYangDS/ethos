from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.evidence.external as external
from ethos.adapters.admission.evidence.external import IndependentVerificationProvider
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.admission.evidence.external import load_independent_verification_provider
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from ethos.contracts.semantic import canonical_json_bytes
from ethos.contracts.semantic import canonical_json_digest
from ethos.repository.profile import IndependentVerificationPolicy
from tests.support.governed_repository import write_test_profile
from tests.support.literal_cases import literal_case

if TYPE_CHECKING:
    from pathlib import Path


REQUEST = literal_case("admission.test_independent_verification:assign:REQUEST:derived")


def _receipt(**updates: object) -> IndependentVerificationReceipt:
    now = datetime.now(UTC)
    receipt = IndependentVerificationReceipt(
        **REQUEST,
        result="pass",
        issuer="provider:example",
        key_id="provider:example",
        signature_algorithm="ssh-ed25519",
        signature="signed-payload",
        issued_at=now,
        valid_until=now + timedelta(minutes=5),
        payload_digest="",
    ).model_copy(update=updates)
    return receipt.model_copy(update={"payload_digest": receipt.canonical_payload_digest()})


def _write_receipt(path: Path, **updates: object) -> Path:
    path.write_text(json.dumps(_receipt(**updates).model_dump(mode="json")), encoding="utf-8")
    return path


def test_receipt_digest_and_signature_share_kernel_canonical_bytes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    receipt = _receipt(action="publish-é", issuer="provider:验证")
    payload = receipt.model_dump(mode="json", exclude={"signature", "payload_digest"})
    captured: dict[str, bytes] = {}

    def run(_command: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        signed_payload = kwargs["input"]
        assert isinstance(signed_payload, bytes)
        captured["input"] = signed_payload
        return subprocess.CompletedProcess([], 0, b"", b"")

    monkeypatch.setattr(external.shutil, "which", lambda _name: "/usr/bin/ssh-keygen")
    monkeypatch.setattr(external.subprocess, "run", run)

    assert receipt.canonical_payload_bytes() == canonical_json_bytes(payload)
    assert receipt.canonical_payload_digest() == canonical_json_digest(payload)
    assert external.verify_independent_receipt_signature(receipt, _provider(tmp_path)) is True
    assert captured["input"] == receipt.canonical_payload_bytes()


def test_proof_floor_digest_uses_kernel_semantic_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(external.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        external.git,
        "git_stdout",
        lambda _root, *args: (
            "b" * 40 if args[:2] == ("rev-parse", "a" * 40 + "^{tree}") else "origin-url"
        ),
    )

    def policy(_root: Path, *, tree_ref: str):
        assert (_root, tree_ref) == (tmp_path, "a" * 40)
        return type("Policy", (), {"gate_ids": ("tests", "verify-é"), "digest": "c" * 64})()

    monkeypatch.setattr(external, "resolve_gate_policy", policy)

    request = independent_verification_request(root=tmp_path, action="publish")

    assert request["proof_floor_digest"] == canonical_json_digest(
        {"gate_ids": ["tests", "verify-é"]}
    )


def _provider(root: Path) -> IndependentVerificationProvider:
    store = root / "store"
    store.mkdir(exist_ok=True)
    return IndependentVerificationProvider(
        receipt_store=store,
        allowed_signers=root / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
        issuer="provider:example",
        key_id="provider:example",
    )


@pytest.mark.parametrize(
    ("mode", "receipt", "verdict", "state", "gaps"),
    literal_case(
        "admission.test_independent_verification:parametrize:test_policy_modes_preserve_local_first_fail_closed_semantics:0"
    ),
)
def test_policy_modes_preserve_local_first_fail_closed_semantics(
    tmp_path: Path, mode: str, receipt: str | None, verdict: str, state: str, gaps: list[str]
) -> None:
    path = tmp_path / "receipt.json" if receipt else None
    if path:
        path.write_text("{" if receipt == "malformed" else "[]", encoding="utf-8")
    report = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode=mode),
        request={"action": "publish"},
        receipt_path=path,
    )
    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        verdict,
        state,
        gaps,
    )
    assert report["evidence_class"] == "local_readiness"
    assert report["mints_authority"] is False
    assert "ok" not in report


def test_required_policy_accepts_only_exact_valid_receipt(tmp_path: Path) -> None:
    path = _write_receipt(tmp_path / "receipt.json")
    report = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="required"),
        request=REQUEST,
        receipt_path=path,
        signature_verifier=lambda receipt: receipt.issuer == "provider:example",
    )
    assert report["verdict"] == "pass"
    assert report["evidence_class"] == "independently_reexecuted"
    assert report["required_gaps"] == []


def test_profile_policy_is_valid_action_scoped_and_default_disabled(tmp_path: Path) -> None:
    assert (
        independent_verification_admission_report(
            root=tmp_path, action="publish", request={"action": "publish"}
        )["verdict"]
        == "pass"
    )
    write_test_profile(
        tmp_path,
        independent_verification={"actions": {"publish": {"mode": "required"}}},
    )
    assert independent_verification_admission_report(
        root=tmp_path, action="publish", request={"action": "publish"}
    )["required_gaps"] == ["independent_verification_receipt_required"]
    assert (
        independent_verification_admission_report(
            root=tmp_path, action="land", request={"action": "land"}
        )["verdict"]
        == "pass"
    )
    profile = tmp_path / ".ethos/profile.toml"
    profile.write_text("[", encoding="utf-8")
    with pytest.raises(ValueError, match="repository_profile_invalid"):
        external.independent_verification_policy(tmp_path, "publish")
    with pytest.raises(ValueError, match=r"disabled.*optional.*required"):
        IndependentVerificationPolicy(mode="always")


def test_request_binds_exact_revision_and_policy_without_provider_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(external.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        external.git,
        "git_stdout",
        lambda _root, *args: (
            "b" * 40 if args[:2] == ("rev-parse", "a" * 40 + "^{tree}") else "origin-url"
        ),
    )

    def policy(_root: Path, *, tree_ref: str):
        assert (_root, tree_ref) == (tmp_path, "a" * 40)
        return type("Policy", (), {"gate_ids": ("tests", "lint"), "digest": "c" * 64})()

    monkeypatch.setattr(external, "resolve_gate_policy", policy)
    assert independent_verification_request(root=tmp_path, action="publish") == {
        "remote": "origin-url",
        "commit": "a" * 40,
        "tree": "b" * 40,
        "action": "publish",
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": "bdd89b540b1199629ad5bcfc89e847d489408875c99944bd17b6aefcd80a5297",
        "policy_digest": "c" * 64,
        "implementation_digest": "",
    }
    monkeypatch.setattr(external.git, "current_head", lambda _root: "")
    empty = independent_verification_request(root=tmp_path, action="publish")
    assert (empty["tree"], empty["policy_digest"], empty["implementation_digest"]) == ("", "", "")


def _write_provider_config(root: Path, provider: IndependentVerificationProvider) -> Path:
    if not provider.allowed_signers.exists():
        provider.allowed_signers.write_text("provider:test ssh-ed25519 test\n", encoding="utf-8")
    config = root / "provider.toml"
    config.write_text(
        f'[receipt_store]\nroot = "{provider.receipt_store}"\n[signature]\n'
        f'allowed_signers = "{provider.allowed_signers}"\nnamespace = "{provider.namespace}"\n'
        f'implementation_digest = "{provider.implementation_digest}"\n'
        f'issuer = "{provider.issuer}"\nkey_id = "{provider.key_id}"\n',
        encoding="utf-8",
    )
    return config


def test_provider_configuration_is_protected_outside_agent_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _provider(tmp_path)
    config = _write_provider_config(tmp_path, provider)
    owner = config.stat().st_uid
    monkeypatch.setattr(external.os, "geteuid", lambda: owner)
    assert load_independent_verification_provider(config) == (
        None,
        ["independent_verification_provider_config_untrusted"],
    )
    monkeypatch.setattr(external.os, "geteuid", lambda: owner + 1)
    loaded, gaps = load_independent_verification_provider(config)
    assert gaps == []
    assert loaded == provider


@pytest.mark.parametrize(
    ("content", "gap"),
    literal_case(
        "admission.test_independent_verification:parametrize:test_provider_configuration_invalid_inputs_fail_closed:1"
    ),
)
def test_provider_configuration_invalid_inputs_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, content: str | None, gap: str
) -> None:
    path = tmp_path / "provider.toml"
    if content is not None:
        path.write_text(content, encoding="utf-8")
        monkeypatch.setattr(external.os, "geteuid", lambda: path.stat().st_uid + 1)
    assert load_independent_verification_provider(path) == (None, [gap])


def test_required_provider_rejects_receipt_outside_read_only_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = _provider(tmp_path)
    outside = _write_receipt(tmp_path / "outside.json")
    monkeypatch.setattr(
        external, "load_independent_verification_provider", lambda _path: (provider, [])
    )
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", outside.as_posix())
    write_test_profile(
        tmp_path,
        independent_verification={"actions": {"publish": {"mode": "required"}}},
    )
    report = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={"action": "publish"},
        provider_config_path=tmp_path / "provider.toml",
    )
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["independent_verification_receipt_outside_store"]


def test_provider_verifies_signature_from_protected_anchor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ssh_keygen = shutil.which("ssh-keygen")
    assert ssh_keygen
    provider = _provider(tmp_path)
    private_key = tmp_path / "signing-key"
    subprocess.run([ssh_keygen, "-q", "-t", "ed25519", "-N", "", "-f", private_key], check=True)
    provider.allowed_signers.write_text(
        f"provider:example {private_key.with_suffix('.pub').read_text().strip()}\n",
        encoding="utf-8",
    )
    config = _write_provider_config(tmp_path, provider)
    unsigned = _receipt(signature="placeholder")
    payload = tmp_path / "payload"
    payload.write_text(
        json.dumps(
            unsigned.model_dump(mode="json", exclude={"signature", "payload_digest"}),
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [ssh_keygen, "-Y", "sign", "-f", private_key, "-n", provider.namespace, payload],
        check=True,
        capture_output=True,
    )
    receipt = unsigned.model_copy(update={"signature": payload.with_suffix(".sig").read_text()})
    receipt_path = provider.receipt_store / "receipt.json"
    receipt_path.write_text(json.dumps(receipt.model_dump(mode="json")), encoding="utf-8")
    write_test_profile(
        tmp_path,
        independent_verification={"actions": {"publish": {"mode": "required"}}},
    )
    monkeypatch.setattr(external.os, "geteuid", lambda: config.stat().st_uid + 1)
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", receipt_path.as_posix())
    report = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={k: v for k, v in REQUEST.items() if k != "implementation_digest"},
        provider_config_path=config,
    )
    assert (report["verdict"], report["evidence_class"]) == ("pass", "independently_reexecuted")


def test_receipt_negative_matrix_remains_local_readiness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    path = _write_receipt(
        tmp_path / "failed.json",
        result="fail",
        issued_at=now - timedelta(minutes=10),
        valid_until=now - timedelta(minutes=5),
        remote="https://wrong.example/repo.git",
    )
    report = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="required"),
        request={"remote": REQUEST["remote"]},
        receipt_path=path,
        signature_verifier=lambda _receipt: False,
    )
    assert set(report["required_gaps"]) == {
        "independent_verification_receipt_failed",
        "independent_verification_receipt_stale",
        "independent_verification_receipt_binding_mismatch",
        "independent_verification_signature_invalid",
    }
    assert report["evidence_class"] == "local_readiness"
    provider = _provider(tmp_path)
    receipt = _receipt()
    monkeypatch.setattr(external.shutil, "which", lambda _name: None)
    assert external.verify_independent_receipt_signature(receipt, provider) is False
    monkeypatch.setattr(external.shutil, "which", lambda _name: "true")
    monkeypatch.setattr(
        external.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError)
    )
    assert external.verify_independent_receipt_signature(receipt, provider) is False


@pytest.mark.parametrize(("mode", "state"), [("required", "blocked"), ("optional", "invalid")])
def test_missing_provider_config_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, state: str
) -> None:
    receipt = _write_receipt(tmp_path / "receipt.json")
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", receipt.as_posix())
    write_test_profile(
        tmp_path,
        independent_verification={"actions": {"publish": {"mode": mode}}},
    )
    report = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={"action": "publish"},
        provider_config_path=tmp_path / "missing.toml",
    )
    assert (report["state"], report["required_gaps"]) == (
        state,
        ["independent_verification_provider_config_missing"],
    )
