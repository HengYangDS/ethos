from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    ROOT / "extensions/independent-verification/adapters/independent_identity/reference_verifier.py"
)
LEGACY_ROOT = ROOT / "reference_adapters"


def _adapter():
    spec = importlib.util.spec_from_file_location("ethos_reference_verifier", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _config(module, tmp_path: Path):
    return module.ReferenceVerifierConfig(
        account="verifier",
        remote="file:///trusted/mirror.git",
        commit="a" * 40,
        runtime_python=tmp_path / "runtime-python",
        implementation_digest="b" * 64,
        signing_key=tmp_path / "signing-key",
        key_id="provider:reference",
        receipt_store=tmp_path / "receipts",
        checkout_root=tmp_path / "checkouts",
        sandbox_exec=tmp_path / "sandbox-exec",
    )


def _request(**overrides: object) -> dict[str, object]:
    request: dict[str, object] = {
        "remote": "file:///trusted/mirror.git",
        "commit": "a" * 40,
        "tree": "c" * 40,
        "action": "publish",
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": "d" * 64,
        "policy_digest": "e" * 64,
        "implementation_digest": "b" * 64,
    }
    request.update(overrides)
    return request


def test_reference_verifier_has_one_extension_owned_source() -> None:
    assert MODULE_PATH.is_file()
    assert not LEGACY_ROOT.exists()


def test_reference_adapter_rejects_foreign_sha_and_unallowlisted_remote(
    tmp_path: Path,
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)

    with pytest.raises(module.VerificationError, match="foreign_commit"):
        module.validate_request(config, _request(commit="f" * 40))
    with pytest.raises(module.VerificationError, match="remote_not_allowlisted"):
        module.validate_request(config, _request(remote="file:///foreign/mirror.git"))
    with pytest.raises(module.VerificationError, match="implementation_mismatch"):
        module.validate_request(config, _request(implementation_digest="c" * 64))
    module.validate_request(config, _request(implementation_digest=""))


def test_reference_adapter_preserves_the_configured_virtualenv_interpreter(
    tmp_path: Path,
) -> None:
    module = _adapter()
    runtime = tmp_path / "runtime" / "bin" / "python"
    runtime.parent.mkdir(parents=True)
    runtime.symlink_to(sys.executable)
    config_path = tmp_path / "provider.toml"
    config_path.write_text(
        "\n".join(
            [
                "[identity]",
                'account = "verifier"',
                "[source]",
                'remote = "file:///trusted/mirror.git"',
                f'commit = "{"a" * 40}"',
                "[runtime]",
                f'python = "{runtime.as_posix()}"',
                f'implementation_digest = "{"b" * 64}"',
                "[signing]",
                f'key = "{(tmp_path / "issuer").as_posix()}"',
                'key_id = "provider:reference"',
                "[storage]",
                f'receipt_store = "{(tmp_path / "receipts").as_posix()}"',
                f'checkout_root = "{(tmp_path / "checkouts").as_posix()}"',
            ]
        ),
        encoding="utf-8",
    )

    config = module.load_config(config_path)

    assert config.runtime_python == runtime
    assert config.runtime_python.is_symlink()


def test_reference_adapter_canonicalizes_the_proof_floor_and_supplies_its_own_digest() -> None:
    module = _adapter()
    expected = hashlib.sha256(
        json.dumps({"gate_ids": ["a", "z"]}, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()

    assert (
        module._proof_floor_digest(  # noqa: RUF100, SLF001 - request/receipt boundary must share a canonical floor digest
            {"data": {"action_graph": {"nodes": [{"id": "z"}, {"id": "a"}]}}}
        )
        == expected
    )


def test_reference_adapter_fails_closed_when_sandbox_is_unavailable(
    tmp_path: Path,
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)

    with pytest.raises(module.VerificationError, match="sandbox_unavailable"):
        module.sandboxed_command(config, ["/usr/bin/git", "status"], tmp_path / "checkout")


def test_reference_adapter_fails_when_receipt_cannot_be_published(
    tmp_path: Path,
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    config.receipt_store.write_text("not a directory", encoding="utf-8")

    with pytest.raises(module.VerificationError, match="receipt_publication_failed"):
        module.publish_receipt(config, "receipt.json", {"result": "pass"})


def test_reference_adapter_never_forwards_keys_to_proof_children(
    tmp_path: Path, monkeypatch
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    monkeypatch.setenv("SSH_AUTH_SOCK", "/private/key-agent.sock")
    monkeypatch.setenv("ETHOS_SIGNING_KEY", "private-key-material")
    monkeypatch.setenv("UNRELATED", "discard-me")

    child = module.proof_child_environment(config)

    assert child["HOME"] == tmp_path.as_posix()
    assert "SSH_AUTH_SOCK" not in child
    assert "ETHOS_SIGNING_KEY" not in child
    assert "UNRELATED" not in child
    assert all("KEY" not in key for key in child)
    assert os.environ["ETHOS_SIGNING_KEY"] == "private-key-material"


def test_reference_adapter_prepares_an_offline_snapshot_runtime(
    tmp_path: Path, monkeypatch
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    checkout = config.checkout_root / "snapshot" / "checkout"
    monkeypatch.setenv("SSH_AUTH_SOCK", "/private/key-agent.sock")

    environment = module.proof_child_environment(config, checkout=checkout)

    assert environment["HOME"] == (checkout.parent / "scratch").as_posix()
    assert environment["PYTHONPATH"] == ":".join(
        [
            (checkout / "packages/ethos/src").as_posix(),
            (checkout / "packages/ethos-core/src").as_posix(),
        ]
    )
    assert environment["ETHOS_RUNTIME_BOOTSTRAPPED"] == "1"
    assert environment["UV_OFFLINE"] == "1"
    assert environment["UV_NO_SYNC"] == "1"
    assert environment["OPENSPEC_TELEMETRY"] == "0"
    assert config.runtime_python.parent.as_posix() in environment["PATH"]
    assert "SSH_AUTH_SOCK" not in environment


def test_reference_adapter_uses_snapshot_parent_for_proof_execution(
    tmp_path: Path, monkeypatch
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    config.sandbox_exec.write_text("", encoding="utf-8")
    config.sandbox_exec.chmod(0o755)
    checkout = config.checkout_root / "snapshot" / "checkout"
    checkout.mkdir(parents=True)
    captured: dict[str, object] = {}

    def run(*args, **kwargs):
        captured.update(args=args, **kwargs)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(module.subprocess, "run", run)

    module._run(config, ["/usr/bin/git", "status"], checkout, prepared_checkout=True)

    assert captured["cwd"] == checkout.parent
    environment = captured["env"]
    assert environment["PYTHONPATH"].startswith(checkout.as_posix())
    assert environment["UV_OFFLINE"] == "1"


def test_reference_adapter_keeps_clone_environment_free_of_snapshot_paths(
    tmp_path: Path, monkeypatch
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    config.sandbox_exec.write_text("", encoding="utf-8")
    config.sandbox_exec.chmod(0o755)
    checkout = config.checkout_root / "snapshot" / "checkout"
    captured: dict[str, object] = {}

    def run(*args, **kwargs):
        captured.update(args=args, **kwargs)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(module.subprocess, "run", run)

    module._run(config, ["/usr/bin/git", "clone"], checkout)

    environment = captured["env"]
    assert "PYTHONPATH" not in environment
    assert environment["HOME"] == config.checkout_root.parent.as_posix()


def test_reference_adapter_creates_the_clone_workspace_before_dispatch(
    tmp_path: Path, monkeypatch
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    config.sandbox_exec.write_text("", encoding="utf-8")
    config.sandbox_exec.chmod(0o755)
    checkout = config.checkout_root / "snapshot" / "checkout"
    captured: dict[str, object] = {}

    def run(*args, **kwargs):
        captured.update(args=args, **kwargs)
        return SimpleNamespace(returncode=0, stdout=b"", stderr=b"")

    monkeypatch.setattr(module.subprocess, "run", run)

    module._run(config, ["/usr/bin/git", "clone"], checkout)

    assert checkout.parent.is_dir()
    assert captured["cwd"] == checkout.parent


def test_reference_adapter_profile_supports_the_offline_runtime_without_broker_state(
    tmp_path: Path,
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    checkout = config.checkout_root / "snapshot" / "checkout"

    profile = module._sandbox_profile(config, checkout)

    assert "(deny default)" in profile
    assert "(deny network*)" not in profile
    assert "(allow file-read*)" in profile
    assert "com.apple.SystemConfiguration.configd" in profile
    assert '(literal "/bin/ps")' in profile
    assert '(literal "/dev/null")' in profile
    assert '(literal "/dev")' in profile
    assert checkout.parent.as_posix() in profile
    assert '(deny file-read* (subpath "/var/db/ethos"))' in profile
    assert '(deny file-read* (subpath "/etc/ethos"))' in profile
    assert f'(deny file-read* (literal "{config.signing_key.as_posix()}"))' in profile
    assert f'(deny file-read* (subpath "{config.receipt_store.as_posix()}"))' in profile


def test_reference_adapter_does_not_treat_remote_location_as_policy(
    tmp_path: Path,
) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    mirror = tmp_path / "mirror.git"
    config = module.ReferenceVerifierConfig(
        **{**config.__dict__, "remote": f"file://{mirror.as_posix()}"}
    )
    checkout = config.checkout_root / "snapshot" / "checkout"

    profile = module._sandbox_profile(config, checkout)

    assert mirror.as_posix() not in profile
    assert "file://" not in profile
