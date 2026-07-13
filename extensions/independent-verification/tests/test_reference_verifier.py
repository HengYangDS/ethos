from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = (
    ROOT / "extensions/independent-verification/adapters/independent_identity/reference_verifier.py"
)


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


def test_reference_adapter_refuses_invalid_requests(tmp_path: Path) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    for request, error in (
        (_request(commit="f" * 40), "foreign_commit"),
        (_request(remote="file:///foreign/mirror.git"), "remote_not_allowlisted"),
        (_request(implementation_digest="c" * 64), "implementation_mismatch"),
        (_request(tree="bad"), "request_invalid:tree"),
    ):
        with pytest.raises(module.VerificationError, match=error):
            module.validate_request(config, request)


def test_reference_adapter_refuses_unavailable_sandbox_and_receipt_store(tmp_path: Path) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    with pytest.raises(module.VerificationError, match="sandbox_unavailable"):
        module.sandboxed_command(config, ["/usr/bin/git", "status"], tmp_path / "checkout")
    config.sandbox_exec.touch()
    config.sandbox_exec.chmod(0o755)
    profile = module.sandboxed_command(config, ["/usr/bin/git", "status"], tmp_path / "checkout")[2]
    for token in (
        '(import "system.sb")',
        "(deny network*)",
        '(deny file-read* file-write* (subpath "/var/db/ethos"))',
        f'(deny file-read* file-write* (literal "{config.signing_key.as_posix()}"))',
        f'(deny file-read* file-write* (subpath "{config.receipt_store.as_posix()}"))',
    ):
        assert token in profile
    config.receipt_store.write_text("not a directory", encoding="utf-8")
    with pytest.raises(module.VerificationError, match="receipt_publication_failed"):
        module.publish_receipt(config, "receipt.json", {"result": "pass"})


def test_reference_adapter_prepares_key_free_snapshot_environment(tmp_path: Path) -> None:
    module = _adapter()
    config = _config(module, tmp_path)
    checkout = config.checkout_root / "snapshot" / "checkout"
    environment = module.proof_child_environment(config, checkout=checkout)
    assert environment["HOME"] == (checkout.parent / "scratch").as_posix()
    assert environment["UV_OFFLINE"] == "1"
    assert environment["PYTHONPATH"].startswith(checkout.as_posix())
    assert "SSH_AUTH_SOCK" not in environment
    assert "ETHOS_SIGNING_KEY" not in environment
