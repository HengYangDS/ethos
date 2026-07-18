#!/usr/bin/env python3
"""Default-off, provider-local generic Git pre-receive receipt gate."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import tomllib
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path

from cyclopts import App

GIT, SSH_KEYGEN = "/usr/bin/git", "/usr/bin/ssh-keygen"
SHA256_SIZE, REF_UPDATE_FIELDS = 64, 3
FIELDS = (
    "remote",
    "action",
    "proof_floor_id",
    "proof_floor_digest",
    *("policy_digest", "implementation_digest"),
)


class RefusalError(RuntimeError):
    """Fail-closed provider-hook refusal."""


def fail(code: str):
    """Raise one stable refusal code."""
    raise RefusalError(code)


def _hex(value: object, sizes: set[int]) -> bool:
    return (
        isinstance(value, str)
        and len(value) in sizes
        and all(char in "0123456789abcdef" for char in value)
    )


def _path(value: object, field: str) -> Path:
    path = Path(value).expanduser() if isinstance(value, str) and value else None
    if path is None or not path.is_absolute():
        fail(f"config_invalid:{field}")
    return path.resolve()


def canonical_payload(receipt: dict[str, object]) -> bytes:
    """Render the signed receipt body without its digest or signature."""
    body = {
        key: value for key, value in receipt.items() if key not in {"signature", "payload_digest"}
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def load_config(path: Path) -> dict[str, object]:
    """Load only protected provider-owned hook configuration."""
    try:
        if path.stat().st_mode & 0o022 or path.parent.stat().st_mode & 0o022:
            fail("config_untrusted")
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        fail("config_unreadable")
    mode = config.get("mode") if isinstance(config, dict) else None
    if mode not in {"disabled", "required"}:
        fail("config_invalid:mode")
    if mode == "disabled":
        return config
    strings = ("remote", "action", "namespace", "proof_floor_id")
    hashes = ("proof_floor_digest", "policy_digest", "implementation_digest")
    valid_strings = all(isinstance(config.get(key), str) and config[key] for key in strings)
    if not valid_strings or not all(_hex(config.get(key), {SHA256_SIZE}) for key in hashes):
        fail("config_invalid:binding")
    refs, ttl = config.get("protected_refs"), config.get("freshness_seconds")
    valid_refs = (
        isinstance(refs, list)
        and refs
        and all(isinstance(ref, str) and ref.startswith("refs/") for ref in refs)
    )
    if not valid_refs:
        fail("config_invalid:protected_refs")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 1:
        fail("config_invalid:freshness_seconds")
    for field, kind in (
        ("bare_repository", "is_dir"),
        ("receipt_store", "is_dir"),
        ("allowed_signers", "is_file"),
    ):
        value = _path(config.get(field), field)
        if not getattr(value, kind)():
            fail("config_invalid:provider_store")
        config[field] = value
    return config


def _run(args: list[str], *, text: bool = False, data: bytes | None = None):
    return subprocess.run(args, input=data, capture_output=True, text=text, check=False, timeout=5)


def _signature_ok(receipt: dict[str, object], config: dict[str, object]) -> bool:
    signature = receipt.get("signature")
    if not isinstance(signature, str) or receipt.get("signature_algorithm") != "ssh-ed25519":
        return False
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as temporary:
            temporary.write(signature)
            temporary.flush()
            command = [SSH_KEYGEN, "-Y", "verify"]
            for option, value in (
                ("-f", str(config["allowed_signers"])),
                ("-I", str(receipt.get("key_id", ""))),
                ("-n", str(config["namespace"])),
                ("-s", temporary.name),
            ):
                command.extend((option, value))
            return _run(command, data=canonical_payload(receipt)).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def _tree(config: dict[str, object], commit: str) -> str:
    result = _run(
        [GIT, "--git-dir", str(config["bare_repository"]), "rev-parse", f"{commit}^{{tree}}"],
        text=True,
    )
    if result.returncode or not _hex(result.stdout.strip(), {40, SHA256_SIZE}):
        fail("proposed_tree_unavailable")
    return result.stdout.strip()


def parse_timestamp(value: object) -> datetime:
    """Parse one receipt timestamp as a timezone-aware UTC instant."""
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        fail("receipt_invalid")
    if parsed.tzinfo is None:
        fail("receipt_invalid")
    return parsed.astimezone(UTC)


def _receipt(config: dict[str, object], commit: str, tree: str) -> None:
    try:
        path = Path(config["receipt_store"]) / f"{commit}-{config['action']}.json"
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("receipt_missing")
    if not isinstance(receipt, dict) or receipt.get("result") != "pass":
        fail("receipt_invalid")
    if not _hex(receipt.get("payload_digest"), {SHA256_SIZE}):
        fail("receipt_invalid")
    if hashlib.sha256(canonical_payload(receipt)).hexdigest() != receipt["payload_digest"]:
        fail("receipt_digest_invalid")
    issued, until = map(parse_timestamp, (receipt.get("issued_at"), receipt.get("valid_until")))
    if not issued <= datetime.now(UTC) <= until or until - issued > timedelta(
        seconds=int(config["freshness_seconds"])
    ):
        fail("receipt_stale")
    expected = {**{field: config[field] for field in FIELDS}, "commit": commit, "tree": tree}
    if any(receipt.get(field) != value for field, value in expected.items()):
        fail("receipt_binding_mismatch")
    if not _signature_ok(receipt, config):
        fail("receipt_signature_invalid")


def enforce(config_path: Path, lines: list[str]) -> None:
    """Check protected proposed refs without reading pushed repository configuration."""
    config = load_config(config_path)
    if config["mode"] == "disabled":
        return
    for line in lines:
        fields = line.split()
        if len(fields) != REF_UPDATE_FIELDS:
            fail("stdin_invalid")
        _old, new, ref = fields
        if ref not in config["protected_refs"]:
            continue
        if not _hex(new, {40, SHA256_SIZE}) or set(new) == {"0"}:
            fail("protected_deletion")
        _receipt(config, new, _tree(config, new))


app = App(name="ethos-generic-pre-receive")


@app.default
def main(*, config: Path) -> int:
    """Run the provider-installed hook with standard pre-receive input."""
    try:
        enforce(config, sys.stdin.read().splitlines())
    except RefusalError as exc:
        sys.stderr.write(f"ethos-generic-pre-receive:{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    app(sys.argv[1:])
