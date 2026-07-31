from __future__ import annotations

import json
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta

import pytest

import ethos.adapters.admission.evidence.external as external
from ethos.adapters.admission.evidence.external import IndependentVerificationProvider
from ethos.adapters.admission.evidence.external import independent_verification_admission_report
from ethos.adapters.admission.evidence.external import independent_verification_report
from ethos.adapters.admission.evidence.external import independent_verification_request
from ethos.adapters.admission.evidence.external import load_independent_verification_provider
from ethos.contracts.evidence.external import IndependentVerificationReceipt
from ethos.repository.profile import IndependentVerificationPolicy
from tests.support.contract_helpers import write_test_profile


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

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["state"] == "disabled"
    assert report["evidence_class"] == "local_readiness"


def test_independent_verification_policy_rejects_invalid_profile(tmp_path) -> None:
    profile = tmp_path / ".ethos" / "profile.toml"
    profile.parent.mkdir()
    profile.write_text("[", encoding="utf-8")

    with pytest.raises(ValueError, match="repository_profile_invalid"):
        external.independent_verification_policy(tmp_path, "publish")


def test_optional_policy_accepts_absence_but_marks_supplied_invalid_receipt(
    tmp_path,
) -> None:
    absent = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="optional"),
        request={"action": "publish"},
        receipt_path=None,
    )
    invalid = tmp_path / "receipt.json"
    invalid.write_text("[]", encoding="utf-8")
    supplied = independent_verification_report(
        root=tmp_path,
        policy=IndependentVerificationPolicy(mode="optional"),
        request={"action": "publish"},
        receipt_path=invalid,
    )

    assert absent["verdict"] == "pass"
    assert supplied["verdict"] == "block"
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

    assert missing["verdict"] == "unknown"
    assert "independent_verification_receipt_required" in missing["required_gaps"]
    assert accepted["verdict"] == "pass"
    assert accepted["evidence_class"] == "independently_reexecuted"


def test_profile_defaults_disabled_but_required_publish_is_action_scoped(
    tmp_path,
) -> None:
    default = independent_verification_admission_report(
        root=tmp_path,
        action="publish",
        request={"action": "publish"},
    )
    write_test_profile(
        tmp_path,
        independent_verification={"actions": {"publish": {"mode": "required"}}},
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

    assert default["verdict"] == "pass"
    assert required["required_gaps"] == ["independent_verification_receipt_required"]
    assert unrelated["verdict"] == "pass"


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

    def policy(_root, *, tree_ref: str):
        assert _root == tmp_path
        assert tree_ref == "a" * 40
        return type(
            "Policy",
            (),
            {"gate_ids": ("tests", "lint"), "digest": "c" * 64},
        )()

    monkeypatch.setattr(external, "resolve_gate_policy", policy)

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
    write_test_profile(
        tmp_path,
        independent_verification={"actions": {"publish": {"mode": "required"}}},
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

    assert report["verdict"] == "pass"
    assert report["evidence_class"] == "independently_reexecuted"


def test_provider_configuration_reports_invalid_inputs_fail_closed(tmp_path, monkeypatch) -> None:
    missing = tmp_path / "missing.toml"
    assert load_independent_verification_provider(missing) == (
        None,
        ["independent_verification_provider_config_missing"],
    )
    with pytest.raises(ValueError, match=r"disabled.*optional.*required"):
        IndependentVerificationPolicy(mode="always")

    malformed = tmp_path / "provider.toml"
    malformed.write_text("[receipt_store\n", encoding="utf-8")
    monkeypatch.setattr(
        "ethos.adapters.admission.evidence.external.os.geteuid",
        lambda: malformed.stat().st_uid + 1,
    )
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
    assert external.verify_independent_receipt_signature(receipt, provider) is False
    monkeypatch.setattr(external, "_SSH_KEYGEN", external.Path("/usr/bin/true"))

    def raise_os_error(*_args, **_kwargs):
        raise OSError

    monkeypatch.setattr(external.subprocess, "run", raise_os_error)
    assert external.verify_independent_receipt_signature(receipt, provider) is False


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
    monkeypatch.setenv("ETHOS_INDEPENDENT_VERIFICATION_RECEIPT", receipt.as_posix())
    for mode, state in (("required", "blocked"), ("optional", "invalid")):
        write_test_profile(
            tmp_path,
            independent_verification={"actions": {"publish": {"mode": mode}}},
        )
        report = independent_verification_admission_report(
            root=tmp_path,
            action="publish",
            request={"action": "publish"},
            provider_config_path=tmp_path / "missing-provider.toml",
        )
        assert report["state"] == state
        assert report["required_gaps"] == ["independent_verification_provider_config_missing"]
