#!/usr/bin/env python3
"""Default-off, provider-local generic Git pre-receive receipt gate."""

from __future__ import annotations

import argparse
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
from typing import NoReturn

GIT = "/usr/bin/git"
SSH_KEYGEN = "/usr/bin/ssh-keygen"
FIELDS = (
    "remote",
    "commit",
    "tree",
    "action",
    "proof_floor_id",
    "proof_floor_digest",
    "policy_digest",
    "implementation_digest",
)


class RefusalError(RuntimeError):
    """Fail-closed provider-hook refusal."""


def fail(code: str) -> NoReturn:
    """Raise a stable refusal code."""
    raise RefusalError(code)


def _sha(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)
    )


def _oid(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(c in "0123456789abcdef" for c in value)
    )


def _path(value: object, field: str) -> Path:
    path = Path(value).expanduser() if isinstance(value, str) and value else None
    if path is None or not path.is_absolute():
        fail(f"config_invalid:{field}")
    return path.resolve()


def _payload(receipt: dict[str, object]) -> bytes:
    body = {
        key: value for key, value in receipt.items() if key not in {"signature", "payload_digest"}
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode()


def load_config(path: Path) -> dict[str, object]:
    """Load only protected provider-owned hook configuration."""
    try:
        stat = path.stat()
        if stat.st_mode & 0o022 or path.parent.stat().st_mode & 0o022:
            fail("config_untrusted")
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        fail("config_unreadable")
    if not isinstance(raw, dict) or raw.get("mode") not in {"disabled", "required"}:
        fail("config_invalid:mode")
    if raw["mode"] == "disabled":
        return raw
    strings = ("remote", "action", "namespace", "proof_floor_id")
    hashes = ("proof_floor_digest", "policy_digest", "implementation_digest")
    if any(not isinstance(raw.get(key), str) or not raw[key] for key in strings) or any(
        not _sha(raw.get(key)) for key in hashes
    ):
        fail("config_invalid:binding")
    refs = raw.get("protected_refs")
    if (
        not isinstance(refs, list)
        or not refs
        or any(not isinstance(ref, str) or not ref.startswith("refs/") for ref in refs)
    ):
        fail("config_invalid:protected_refs")
    ttl = raw.get("freshness_seconds")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or ttl < 1:
        fail("config_invalid:freshness_seconds")
    raw.update(
        bare_repository=_path(raw.get("bare_repository"), "bare_repository"),
        receipt_store=_path(raw.get("receipt_store"), "receipt_store"),
        allowed_signers=_path(raw.get("allowed_signers"), "allowed_signers"),
    )
    if (
        not raw["bare_repository"].is_dir()
        or not raw["receipt_store"].is_dir()
        or not raw["allowed_signers"].is_file()
    ):
        fail("config_invalid:provider_store")
    return raw


def _signature_ok(receipt: dict[str, object], config: dict[str, object]) -> bool:
    if (
        not isinstance(receipt.get("signature"), str)
        or receipt.get("signature_algorithm") != "ssh-ed25519"
    ):
        return False
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as signature:
            signature.write(receipt["signature"])
            signature.flush()
            result = subprocess.run(
                [
                    SSH_KEYGEN,
                    "-Y",
                    "verify",
                    "-f",
                    str(config["allowed_signers"]),
                    "-I",
                    str(receipt.get("key_id", "")),
                    "-n",
                    str(config["namespace"]),
                    "-s",
                    signature.name,
                ],
                input=_payload(receipt),
                capture_output=True,
                check=False,
                timeout=5,
            )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


def _tree(config: dict[str, object], commit: str) -> str:
    result = subprocess.run(
        [
            GIT,
            "--git-dir",
            str(config["bare_repository"]),
            "rev-parse",
            f"{commit}^{{tree}}",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=5,
    )
    if result.returncode or not _oid(result.stdout.strip()):
        fail("proposed_tree_unavailable")
    return result.stdout.strip()


def _timestamp(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        fail("receipt_invalid")
    if parsed.tzinfo is None:
        fail("receipt_invalid")
    return parsed.astimezone(UTC)


def _receipt(config: dict[str, object], commit: str, tree: str) -> None:
    try:
        payload = json.loads(
            (Path(config["receipt_store"]) / f"{commit}-{config['action']}.json").read_text(
                encoding="utf-8"
            )
        )
    except (OSError, json.JSONDecodeError):
        fail("receipt_missing")
    if (
        not isinstance(payload, dict)
        or payload.get("result") != "pass"
        or not _sha(payload.get("payload_digest"))
    ):
        fail("receipt_invalid")
    if hashlib.sha256(_payload(payload)).hexdigest() != payload["payload_digest"]:
        fail("receipt_digest_invalid")
    issued, until = (
        _timestamp(payload.get("issued_at")),
        _timestamp(payload.get("valid_until")),
    )
    now = datetime.now(UTC)
    if (
        now < issued
        or now > until
        or until - issued > timedelta(seconds=int(config["freshness_seconds"]))
    ):
        fail("receipt_stale")
    expected = {
        **{field: config[field] for field in FIELDS if field not in {"commit", "tree"}},
        "commit": commit,
        "tree": tree,
    }
    if any(payload.get(field) != value for field, value in expected.items()):
        fail("receipt_binding_mismatch")
    if not _signature_ok(payload, config):
        fail("receipt_signature_invalid")


def enforce(config_path: Path, lines: list[str]) -> None:
    """Check protected proposed refs without reading pushed repository configuration."""
    config = load_config(config_path)
    if config["mode"] == "disabled":
        return
    for line in lines:
        fields = line.split()
        if len(fields) != 3:
            fail("stdin_invalid")
        _old, new, ref = fields
        if ref not in config["protected_refs"]:
            continue
        if not _oid(new) or set(new) == {"0"}:
            fail("protected_deletion")
        _receipt(config, new, _tree(config, new))


def main(argv: list[str] | None = None) -> int:
    """Run the provider-installed hook with standard pre-receive input."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        enforce(args.config, sys.stdin.read().splitlines())
    except RefusalError as exc:
        sys.stderr.write(f"ethos-generic-pre-receive:{exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
