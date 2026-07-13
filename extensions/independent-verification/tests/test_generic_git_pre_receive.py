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


ADAPTER = _adapter()


def _git(path: Path, *args: str) -> str:
    return subprocess.run(
        ["/usr/bin/git", *args], cwd=path, check=True, text=True, capture_output=True
    ).stdout.strip()


def _setup(tmp_path: Path) -> tuple[Path, dict[str, object], str, str]:
    bare, work, store = tmp_path / "bare.git", tmp_path / "work", tmp_path / "receipts"
    _git(tmp_path, "init", "--bare", bare.as_posix())
    _git(tmp_path, "init", work.as_posix())
    _git(work, "config", "user.email", "test@example.invalid")
    _git(work, "config", "user.name", "test")
    (work / "file").write_text("value\n", encoding="utf-8")
    _git(work, "add", "file")
    _git(work, "commit", "-m", "test")
    _git(work, "remote", "add", "origin", bare.as_posix())
    _git(work, "push", "origin", "HEAD:refs/heads/main")
    key, signers, config = tmp_path / "key", tmp_path / "allowed", tmp_path / "provider.toml"
    store.mkdir()
    subprocess.run(
        ["/usr/bin/ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", key.as_posix()], check=True
    )
    signers.write_text(
        f"provider:test {key.with_suffix('.pub').read_text().strip()}\n", encoding="utf-8"
    )
    values: dict[str, object] = {
        "mode": "required",
        "bare_repository": bare,
        "remote": "ssh://example.invalid/repo.git",
        "receipt_store": store,
        "allowed_signers": signers,
        "namespace": "ethos-independent-verification",
        "proof_floor_id": "ethos:promotion-required-gates:v1",
        "action": "publish",
        "freshness_seconds": 600,
        "protected_refs": ["refs/heads/main"],
        "key": key,
        **dict.fromkeys(("implementation_digest", "proof_floor_digest", "policy_digest"), "a" * 64),
    }
    lines = (
        f"{name} = {json.dumps(value.as_posix() if isinstance(value, Path) else value)}"
        for name, value in values.items()
        if name != "key"
    )
    config.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return config, values, _git(work, "rev-parse", "HEAD"), _git(work, "rev-parse", "HEAD^{tree}")


def _write_receipt(values: dict[str, object], commit: str, tree: str, **changes: object) -> None:
    now = datetime.now(UTC)
    receipt = {key: values[key] for key in ADAPTER.FIELDS}
    receipt.update(
        commit=commit,
        tree=tree,
        result="pass",
        key_id="provider:test",
        signature_algorithm="ssh-ed25519",
        issued_at=now.isoformat(),
        valid_until=(now + timedelta(minutes=5)).isoformat(),
        payload_digest="",
        signature="",
    )
    receipt.update(changes)
    receipt["payload_digest"] = hashlib.sha256(ADAPTER.canonical_payload(receipt)).hexdigest()
    message = Path(values["receipt_store"]) / "message"
    message.write_bytes(ADAPTER.canonical_payload(receipt))
    command = ["/usr/bin/ssh-keygen", "-Y", "sign"]
    command += [
        "-f",
        Path(values["key"]).as_posix(),
        "-n",
        str(values["namespace"]),
        message.as_posix(),
    ]
    subprocess.run(command, check=True, capture_output=True)
    receipt["signature"] = message.with_suffix(".sig").read_text(encoding="utf-8")
    (Path(values["receipt_store"]) / f"{commit}-{values['action']}.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )


def test_default_off_adapter_is_extension_local_and_accepts_zulu_time(tmp_path: Path) -> None:
    config = tmp_path / "provider.toml"
    config.write_text('mode = "disabled"\n', encoding="utf-8")
    for path in (MODULE, MODULE.parent / "README.md", MODULE.parent / "adapter.toml"):
        assert path.is_file()
    assert ADAPTER.parse_timestamp("2026-07-13T00:00:00Z") == datetime(2026, 7, 13, tzinfo=UTC)
    ADAPTER.enforce(config, ["not valid input"])


def test_protected_updates_reject_missing_invalid_stale_and_mismatched_receipts(
    tmp_path: Path,
) -> None:
    config, values, commit, tree = _setup(tmp_path)
    line = f"{'0' * 40} {commit} refs/heads/main"
    ADAPTER.enforce(config, [f"{'0' * 40} {commit} refs/heads/topic"])
    with pytest.raises(ADAPTER.RefusalError, match="receipt_missing"):
        ADAPTER.enforce(config, [line])
    _write_receipt(values, commit, tree)
    ADAPTER.enforce(config, [line])
    for field, value, reason, digest in (
        ("signature", "", "receipt_signature_invalid", False),
        ("payload_digest", "d" * 64, "receipt_digest_invalid", False),
        ("tree", "d" * 40, "receipt_binding_mismatch", True),
        ("policy_digest", "d" * 64, "receipt_binding_mismatch", True),
        ("proof_floor_digest", "d" * 64, "receipt_binding_mismatch", True),
    ):
        _write_receipt(values, commit, tree)
        path = Path(values["receipt_store"]) / f"{commit}-{values['action']}.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
        receipt[field] = value
        if digest:
            receipt["payload_digest"] = hashlib.sha256(
                ADAPTER.canonical_payload(receipt)
            ).hexdigest()
        path.write_text(json.dumps(receipt), encoding="utf-8")
        with pytest.raises(ADAPTER.RefusalError, match=reason):
            ADAPTER.enforce(config, [line])
    with pytest.raises(ADAPTER.RefusalError, match="protected_deletion"):
        ADAPTER.enforce(config, [f"{commit} {'0' * 40} refs/heads/main"])
    _write_receipt(
        values,
        commit,
        tree,
        issued_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
        valid_until=(datetime.now(UTC) - timedelta(hours=1)).isoformat(),
    )
    with pytest.raises(ADAPTER.RefusalError, match="receipt_stale"):
        ADAPTER.enforce(config, [line])
