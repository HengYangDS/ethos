from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
MODULE = ROOT / "extensions/independent-verification/adapters/generic_git/pre_receive.py"


def _adapter():
    spec = importlib.util.spec_from_file_location("generic_pre_receive", MODULE)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *args], cwd=path, check=True, text=True, capture_output=True
    ).stdout.strip()


def _repo(tmp_path: Path) -> tuple[Path, str, str]:
    bare, work = tmp_path / "bare.git", tmp_path / "work"
    _git(tmp_path, "init", "--bare", bare.as_posix())
    _git(tmp_path, "init", work.as_posix())
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    (work / "file").write_text("value\n", encoding="utf-8")
    _git(work, "add", "file")
    _git(work, "commit", "-m", "test")
    _git(work, "remote", "add", "origin", bare.as_posix())
    _git(work, "push", "origin", "HEAD:refs/heads/main")
    commit = _git(work, "rev-parse", "HEAD")
    return bare, commit, _git(work, "rev-parse", "HEAD^{tree}")


def _config(
    tmp_path: Path, bare: Path, *, mode: str = "required"
) -> tuple[Path, dict[str, object]]:
    store, signers, key, config = (
        tmp_path / "receipts",
        tmp_path / "allowed",
        tmp_path / "key",
        tmp_path / "provider.toml",
    )
    store.mkdir()
    subprocess.run(
        ["/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key.as_posix()],
        check=True,
    )
    signers.write_text(
        f"provider:test {key.with_suffix('.pub').read_text().strip()}\n",
        encoding="utf-8",
    )
    values: dict[str, object] = {
        "mode": mode,
        "bare_repository": bare,
        "remote": "ssh://example.invalid/repo.git",
        "receipt_store": store,
        "allowed_signers": signers,
        "namespace": "ethos-independent-verification",
        "implementation_digest": "a" * 64,
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "proof_floor_digest": "b" * 64,
        "policy_digest": "c" * 64,
        "action": "publish",
        "freshness_seconds": 600,
        "protected_refs": ["refs/heads/main"],
        "key": key,
    }
    lines = [
        f"{name} = {json.dumps(value.as_posix() if isinstance(value, Path) else value)}"
        for name, value in values.items()
        if name != "key"
    ]
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config, values


def _write_receipt(
    module, values: dict[str, object], commit: str, actual_tree: str, **changes: object
) -> None:
    now = datetime.now(UTC)
    receipt: dict[str, object] = {
        key: values[key]
        for key in (
            "remote",
            "action",
            "proof_floor_id",
            "proof_floor_digest",
            "policy_digest",
            "implementation_digest",
        )
    }
    receipt.update(
        commit=commit,
        tree=actual_tree,
        result="pass",
        issuer="provider:test",
        key_id="provider:test",
        signature_algorithm="ssh-ed25519",
        issued_at=now.isoformat(),
        valid_until=(now + timedelta(minutes=5)).isoformat(),
        payload_digest="",
        signature="",
    )
    receipt.update(changes)
    receipt["payload_digest"] = hashlib.sha256(module._payload(receipt)).hexdigest()
    message = Path(values["receipt_store"]) / "message"
    message.write_bytes(module._payload(receipt))
    subprocess.run(
        [
            "/usr/bin/ssh-keygen",
            "-Y",
            "sign",
            "-f",
            Path(values["key"]).as_posix(),
            "-n",
            str(values["namespace"]),
            message.as_posix(),
        ],
        check=True,
        capture_output=True,
    )
    receipt["signature"] = message.with_suffix(".sig").read_text(encoding="utf-8")
    (Path(values["receipt_store"]) / f"{commit}-{values['action']}.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )


def test_generic_git_adapter_is_extension_local_and_default_off(tmp_path: Path) -> None:
    module = _adapter()
    assert MODULE.is_file()
    assert (MODULE.parent / "README.md").is_file()
    assert (MODULE.parent / "adapter.toml").is_file()
    config, _ = _config(tmp_path, tmp_path, mode="disabled")
    module.enforce(config, ["not valid input"])


def test_receipt_timestamp_accepts_zulu_time() -> None:
    module = _adapter()
    assert module._timestamp("2026-07-13T00:00:00Z") == datetime(2026, 7, 13, tzinfo=UTC)


def test_unprotected_and_exact_signed_protected_updates(tmp_path: Path) -> None:
    module, (bare, commit, tree) = _adapter(), _repo(tmp_path)
    config, values = _config(tmp_path, bare)
    module.enforce(config, [f"{'0' * 40} {commit} refs/heads/topic"])
    _write_receipt(module, values, commit, tree)
    module.enforce(config, [f"{'0' * 40} {commit} refs/heads/main"])


def test_protected_update_rejects_a_missing_receipt(tmp_path: Path) -> None:
    module, (bare, commit, _) = _adapter(), _repo(tmp_path)
    config, _ = _config(tmp_path, bare)
    with pytest.raises(module.RefusalError, match="receipt_missing"):
        module.enforce(config, [f"{'0' * 40} {commit} refs/heads/main"])


@pytest.mark.parametrize(
    ("field", "value", "reason"),
    [
        ("signature", "", "receipt_signature_invalid"),
        ("payload_digest", "d" * 64, "receipt_digest_invalid"),
    ],
)
def test_protected_update_rejects_unsigned_or_damaged_receipts(
    tmp_path: Path, field: str, value: str, reason: str
) -> None:
    module, (bare, commit, tree) = _adapter(), _repo(tmp_path)
    config, values = _config(tmp_path, bare)
    _write_receipt(module, values, commit, tree)
    receipt_path = Path(values["receipt_store"]) / f"{commit}-{values['action']}.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt[field] = value
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(module.RefusalError, match=reason):
        module.enforce(config, [f"{'0' * 40} {commit} refs/heads/main"])


@pytest.mark.parametrize(
    "change",
    [{"tree": "d" * 40}, {"policy_digest": "d" * 64}, {"proof_floor_digest": "d" * 64}],
)
def test_protected_updates_reject_deletion_stale_and_mismatched_receipts(
    tmp_path: Path, change: dict[str, str]
) -> None:
    module, (bare, commit, tree) = _adapter(), _repo(tmp_path)
    config, values = _config(tmp_path, bare)
    _write_receipt(module, values, commit, tree, **change)
    with pytest.raises(module.RefusalError, match="receipt_binding_mismatch"):
        module.enforce(config, [f"{'0' * 40} {commit} refs/heads/main"])
    with pytest.raises(module.RefusalError, match="protected_deletion"):
        module.enforce(config, [f"{commit} {'0' * 40} refs/heads/main"])
    _write_receipt(
        module,
        values,
        commit,
        tree,
        issued_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        valid_until=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
    )
    with pytest.raises(module.RefusalError, match="receipt_stale"):
        module.enforce(config, [f"{'0' * 40} {commit} refs/heads/main"])
