from __future__ import annotations

import json
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

import ethos.adapters.admission.evidence.external as external
from ethos.adapters.admission.evidence.external import IndependentVerificationPolicy
from ethos.adapters.admission.evidence.external import IndependentVerificationProvider
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.admission.evidence.external import load_independent_verification_provider
from ethos_core.contracts.evidence.external import IndependentVerificationReceipt


def _receipt_payload() -> dict[str, object]:
    now = datetime.now(UTC)
    receipt = IndependentVerificationReceipt(
        remote="https://example.invalid/org/repo.git",
        commit="a" * 40,
        tree="b" * 40,
        action="publish",
        proof_floor_id="proof-floor:default",
        proof_floor_digest="c" * 64,
        policy_digest="d" * 64,
        implementation_digest="e" * 64,
        result="pass",
        issuer="provider:example",
        key_id="key:example",
        signature_algorithm="ssh-ed25519",
        signature="signed-payload",
        issued_at=now,
        valid_until=now + timedelta(minutes=5),
        payload_digest="",
    )
    return receipt.model_copy(
        update={"payload_digest": receipt.canonical_payload_digest()}
    ).model_dump(mode="json")


def test_disabled_policy_is_local_first_without_a_provider(tmp_path) -> None:
    report = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="disabled"),
        request={"action": "publish"},
        receipt_path=None,
    )

    assert report["ok"] is True
    assert report["state"] == "disabled"
    assert report["evidence_class"] == "local_readiness"


@pytest.mark.parametrize("carrier", ["missing", "malformed", "array", "mapping"])
def test_optional_policy_accepts_absence_but_marks_supplied_invalid_receipt(
    tmp_path, carrier: str
) -> None:
    absent = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="optional"),
        request={"action": "publish"},
        receipt_path=None,
    )
    invalid = tmp_path / "receipt.json"
    if carrier != "missing":
        invalid.write_text(
            {"malformed": "{", "array": "[]", "mapping": "{}"}[carrier],
            encoding="utf-8",
        )
    supplied = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="optional"),
        request={"action": "publish"},
        receipt_path=invalid,
    )

    assert absent["ok"] is True
    assert supplied["ok"] is False
    assert "independent_verification_receipt_invalid" in supplied["required_gaps"]


def test_required_policy_fails_closed_and_accepts_only_exact_valid_receipt(
    tmp_path,
) -> None:
    required = IndependentVerificationPolicy(mode="required")
    missing = independent_verification_report(
        root=tmp_path,
        policy=required,
        request={"action": "publish"},
        receipt_path=None,
    )
    path = tmp_path / "receipt.json"
    path.write_text(json.dumps(_receipt_payload()), encoding="utf-8")
    accepted = independent_verification_report(
        root=tmp_path,
        policy=required,
        request={
            "remote": "https://example.invalid/org/repo.git",
            "commit": "a" * 40,
            "tree": "b" * 40,
            "action": "publish",
            "proof_floor_id": "proof-floor:default",
            "proof_floor_digest": "c" * 64,
            "policy_digest": "d" * 64,
            "implementation_digest": "e" * 64,
        },
        receipt_path=path,
        signature_verifier=lambda receipt: receipt.issuer == "provider:example",
    )

    assert missing["ok"] is False
    assert "independent_verification_receipt_required" in missing["required_gaps"]
    assert accepted["ok"] is True
    assert accepted["evidence_class"] == "independently_reexecuted"


def test_receipt_binding_survives_bundled_executable_retirement(tmp_path: Path) -> None:
    """Keep exact provider-neutral admission after deleting shipped executables."""
    base_payload = _receipt_payload()
    assert str(base_payload["issued_at"]).endswith("Z")
    request = {
        key: base_payload[key]
        for key in (
            "remote",
            "commit",
            "tree",
            "action",
            "proof_floor_id",
            "proof_floor_digest",
            "policy_digest",
            "implementation_digest",
        )
    }
    replacements = {
        "remote": "https://wrong.example/repo.git",
        "commit": "f" * 40,
        "tree": "f" * 40,
        "action": "land",
        "proof_floor_id": "proof-floor:wrong",
        "proof_floor_digest": "f" * 64,
        "policy_digest": "f" * 64,
        "implementation_digest": "f" * 64,
    }
    receipt_path = tmp_path / "receipt.json"
    for field, replacement in replacements.items():
        payload = {**base_payload, field: replacement, "payload_digest": ""}
        receipt = IndependentVerificationReceipt.model_validate(payload)
        payload["payload_digest"] = receipt.canonical_payload_digest()
        receipt_path.write_text(json.dumps(payload), encoding="utf-8")
        report = independent_verification_report(
            root=tmp_path,
            policy=IndependentVerificationPolicy(mode="required"),
            request=request,
            receipt_path=receipt_path,
            signature_verifier=lambda _receipt: True,
        )
        assert report["required_gaps"] == ["independent_verification_receipt_binding_mismatch"]

    root = Path(__file__).resolve().parents[3]
    assert not (root / "extensions/independent-verification").exists()
    assert not (root / "packages/ethos/src/ethos/adapters/admission/control/verifier.py").exists()


def test_profile_defaults_disabled_but_required_publish_is_action_scoped(
    tmp_path,
) -> None:
    default = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={"action": "publish"},
    )
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        '[independent_verification.actions.publish]\nmode = "required"\n',
        encoding="utf-8",
    )
    required = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={"action": "publish"},
    )
    unrelated = independent_verification_admission_report(
        root=tmp_path,
        action="land",
        request={"action": "land"},
    )

    assert default["ok"] is True
    assert required["required_gaps"] == ["independent_verification_receipt_required"]
    assert unrelated["ok"] is True


def test_request_builder_binds_publish_to_exact_git_revision_and_gate_policy(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setattr(external.git, "git_stdout", lambda *_args: "origin-url")
    monkeypatch.setattr(external.git, "current_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        external.git,
        "git_stdout",
        lambda _root, *args: (
            "b" * 40 if args[:2] == ("rev-parse", "a" * 40 + "^{tree}") else "origin-url"
        ),
    )
    monkeypatch.setattr(external, "promotion_required_gate_ids", lambda _root: ("tests", "lint"))

    def policy_digest(_root, *, tree_ref: str) -> str:
        assert _root == tmp_path
        assert tree_ref == "a" * 40
        return "c" * 64

    monkeypatch.setattr(external, "gate_policy_digest", policy_digest)

    request = independent_verification_request(root=tmp_path, action="publish")

    assert request == {
        "remote": "origin-url",
        "commit": "a" * 40,
        "tree": "b" * 40,
        "action": "publish",
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": "bdd89b540b1199629ad5bcfc89e847d489408875c99944bd17b6aefcd80a5297",
        "policy_digest": "c" * 64,
        "implementation_digest": "",
    }


def test_provider_configuration_must_be_outside_the_agent_identity(tmp_path, monkeypatch) -> None:
    receipts = tmp_path / "receipts"
    receipts.mkdir()
    signers = tmp_path / "allowed-signers"
    signers.write_text("provider:test ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItest\n")
    config = tmp_path / "provider.toml"
    config.write_text(
        "\n".join(
            [
                "[receipt_store]",
                f'root = "{receipts}"',
                "[signature]",
                f'allowed_signers = "{signers}"',
                'namespace = "ethos-independent-verification"',
                'implementation_digest = "' + "a" * 64 + '"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    owner = config.stat().st_uid
    monkeypatch.setattr("ethos.adapters.admission.evidence.external.os.geteuid", lambda: owner)

    rejected, rejected_gaps = load_independent_verification_provider(config)

    assert rejected is None
    assert rejected_gaps == ["independent_verification_provider_config_untrusted"]

    monkeypatch.setattr("ethos.adapters.admission.evidence.external.os.geteuid", lambda: owner + 1)
    provider, gaps = load_independent_verification_provider(config)

    assert gaps == []
    assert isinstance(provider, IndependentVerificationProvider)
    assert provider.implementation_digest == "a" * 64


def test_required_provider_rejects_receipt_outside_the_read_only_store(
    tmp_path, monkeypatch
) -> None:
    store = tmp_path / "store"
    store.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps(_receipt_payload()), encoding="utf-8")
    provider = IndependentVerificationProvider(
        receipt_store=store,
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
    )
    monkeypatch.setattr(
        "ethos.adapters.admission.evidence.external.load_independent_verification_provider",
        lambda _path: (provider, []),
    )
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", outside.as_posix())
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        '[independent_verification.actions.publish]\nmode = "required"\n',
        encoding="utf-8",
    )

    report = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={"action": "publish"},
        provider_config_path=tmp_path / "provider.toml",
    )

    assert report["ok"] is False
    assert "independent_verification_receipt_outside_store" in report["required_gaps"]


def test_provider_verifies_a_signature_from_its_protected_anchor(tmp_path, monkeypatch) -> None:
    store = tmp_path / "store"
    store.mkdir()
    private_key = tmp_path / "signing-key"
    subprocess.run(
        [
            "/usr/bin/ssh-keygen",
            "-q",
            "-t",
            "ed25519",
            "-N",
            "",
            "-f",
            private_key.as_posix(),
        ],
        check=True,
    )
    public_key = private_key.with_suffix(".pub").read_text(encoding="utf-8").strip()
    allowed_signers = tmp_path / "allowed-signers"
    allowed_signers.write_text(f"provider:example {public_key}\n", encoding="utf-8")
    config = tmp_path / "provider.toml"
    config.write_text(
        "\n".join(
            [
                "[receipt_store]",
                f'root = "{store}"',
                "[signature]",
                f'allowed_signers = "{allowed_signers}"',
                'namespace = "ethos-independent-verification"',
                'implementation_digest = "' + "e" * 64 + '"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    unsigned = IndependentVerificationReceipt(
        remote="https://example.invalid/org/repo.git",
        commit="a" * 40,
        tree="b" * 40,
        action="publish",
        proof_floor_id="proof-floor:default",
        proof_floor_digest="c" * 64,
        policy_digest="d" * 64,
        implementation_digest="e" * 64,
        result="pass",
        issuer="provider:example",
        key_id="provider:example",
        signature_algorithm="ssh-ed25519",
        signature="placeholder",
        issued_at=now,
        valid_until=now + timedelta(minutes=5),
        payload_digest="",
    )
    unsigned = unsigned.model_copy(update={"payload_digest": unsigned.canonical_payload_digest()})
    payload_path = tmp_path / "payload"
    payload_path.write_text(
        json.dumps(
            unsigned.model_dump(mode="json", exclude={"signature", "payload_digest"}),
            sort_keys=True,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            private_key.as_posix(),
            "-n",
            "ethos-independent-verification",
            payload_path.as_posix(),
        ],
        check=True,
        capture_output=True,
    )
    receipt_path = store / "receipt.json"
    receipt_path.write_text(
        json.dumps(
            unsigned.model_copy(
                update={"signature": payload_path.with_suffix(".sig").read_text(encoding="utf-8")}
            ).model_dump(mode="json")
        ),
        encoding="utf-8",
    )
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        '[independent_verification.actions.publish]\nmode = "required"\n',
        encoding="utf-8",
    )
    owner = config.stat().st_uid
    monkeypatch.setattr("ethos.adapters.admission.evidence.external.os.geteuid", lambda: owner + 1)
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", receipt_path.as_posix())

    report = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={
            "remote": "https://example.invalid/org/repo.git",
            "commit": "a" * 40,
            "tree": "b" * 40,
            "action": "publish",
            "proof_floor_id": "proof-floor:default",
            "proof_floor_digest": "c" * 64,
            "policy_digest": "d" * 64,
        },
        provider_config_path=config,
    )

    assert report["ok"] is True
    assert report["evidence_class"] == "independently_reexecuted"


def test_provider_configuration_helpers_fail_closed_on_invalid_inputs(
    tmp_path, monkeypatch
) -> None:
    missing = tmp_path / "missing.toml"
    assert load_independent_verification_provider(missing) == (
        None,
        ["independent_verification_provider_config_missing"],
    )
    assert external._is_protected_from_current_identity(missing) is False  # noqa: RUF100, SLF001 - coverage exercises provider-boundary refusal
    assert external._absolute_path("relative/provider.toml") is None  # noqa: RUF100, SLF001 - coverage exercises provider-boundary refusal
    assert external._absolute_path(None) is None  # noqa: RUF100, SLF001 - coverage exercises provider-boundary refusal
    assert external._sha256("not-a-digest") == ""  # noqa: RUF100, SLF001 - coverage exercises provider-boundary refusal
    with pytest.raises(ValueError, match="mode is invalid"):
        IndependentVerificationPolicy(mode="always")

    malformed = tmp_path / "provider.toml"
    malformed.write_text("[receipt_store\n", encoding="utf-8")
    monkeypatch.setattr(external, "_is_protected_from_current_identity", lambda _path: True)
    assert load_independent_verification_provider(malformed) == (
        None,
        ["independent_verification_provider_config_invalid"],
    )

    malformed.write_text("", encoding="utf-8")
    assert load_independent_verification_provider(malformed) == (
        None,
        ["independent_verification_provider_config_invalid"],
    )

    malformed.write_text(
        "[receipt_store]\nroot = 'relative'\n[signature]\nallowed_signers = '/tmp/key'\n"
        "namespace = ''\nimplementation_digest = 'invalid'\n",
        encoding="utf-8",
    )
    assert load_independent_verification_provider(malformed) == (
        None,
        ["independent_verification_provider_config_invalid"],
    )

    fallback = tmp_path / "fallback.toml"
    fallback.write_text("", encoding="utf-8")
    monkeypatch.setattr(external, "_SYSTEM_PROVIDER_CONFIGS", (missing, fallback))
    assert external._default_provider_config_path() == fallback  # noqa: RUF100, SLF001 - provider defaults are an explicit host boundary
    fallback.unlink()
    assert external._default_provider_config_path() == missing  # noqa: RUF100, SLF001 - provider defaults are an explicit host boundary


def test_receipt_negative_paths_remain_local_readiness(tmp_path, monkeypatch) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{", encoding="utf-8")
    report = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="optional"),
        request={"action": "publish"},
        receipt_path=invalid,
    )
    assert report["required_gaps"] == ["independent_verification_receipt_invalid"]

    now = datetime.now(UTC)
    failed = _receipt_payload()
    failed.update(
        {
            "result": "fail",
            "issued_at": (now - timedelta(minutes=10)).isoformat(),
            "valid_until": (now - timedelta(minutes=5)).isoformat(),
            "remote": "https://wrong.example/repo.git",
            "payload_digest": "",
        }
    )
    receipt_path = tmp_path / "failed.json"
    receipt_path.write_text(json.dumps(failed), encoding="utf-8")
    report = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="required"),
        request={"remote": "https://example.invalid/org/repo.git"},
        receipt_path=receipt_path,
        signature_verifier=lambda _receipt: False,
    )
    assert set(report["required_gaps"]) == {
        "independent_verification_receipt_failed",
        "independent_verification_receipt_stale",
        "independent_verification_receipt_binding_mismatch",
        "independent_verification_signature_invalid",
    }

    receipt = IndependentVerificationReceipt.model_validate(_receipt_payload())
    provider = IndependentVerificationProvider(
        receipt_store=tmp_path,
        allowed_signers=tmp_path / "allowed-signers",
        namespace="ethos-independent-verification",
        implementation_digest="e" * 64,
    )
    monkeypatch.setattr(external, "_SSH_KEYGEN", tmp_path / "missing-keygen")
    assert external._verify_independent_receipt_signature(receipt, provider) is False  # noqa: RUF100, SLF001 - coverage exercises fail-closed verifier availability
    monkeypatch.setattr(external, "_SSH_KEYGEN", external.Path("/usr/bin/true"))

    def raise_os_error(*_args, **_kwargs):
        raise OSError

    monkeypatch.setattr(external.subprocess, "run", raise_os_error)
    assert external._verify_independent_receipt_signature(receipt, provider) is False  # noqa: RUF100, SLF001 - coverage exercises fail-closed verifier errors


def test_request_without_head_and_missing_provider_config_are_fail_closed(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(external.git, "current_head", lambda _root: "")
    monkeypatch.setattr(external.git, "git_stdout", lambda *_args: "origin-url")
    request = independent_verification_request(root=tmp_path, action="publish")
    assert request["tree"] == ""
    assert request["policy_digest"] == ""

    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps(_receipt_payload()), encoding="utf-8")
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", receipt.as_posix())
    for mode, state in (("required", "blocked"), ("optional", "invalid")):
        profile.write_text(
            f'[independent_verification.actions.publish]\nmode = "{mode}"\n',
            encoding="utf-8",
        )
        report = independent_verification_admission_report(
            root=tmp_path,
            action="publish",
            request={"action": "publish"},
            provider_config_path=tmp_path / "missing-provider.toml",
        )
        assert report["state"] == state
        assert report["required_gaps"] == ["independent_verification_provider_config_missing"]
