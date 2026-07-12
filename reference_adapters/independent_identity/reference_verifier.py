#!/usr/bin/env python3
"""One-shot, provider-local reference adapter for independent proof re-execution.

This program is deliberately not an ETHOS command.  An operator installs its TOML
configuration, signing key, receipt directory, and trust anchor outside a governed
repository, owned by a dedicated verifier identity.  It accepts no shell command,
no provider URL override, and no scheduling or daemon mode.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any
from typing import NoReturn

_GIT = Path("/usr/bin/git")
_SSH_KEYGEN = Path("/usr/bin/ssh-keygen")
_DEFAULT_SANDBOX = Path("/usr/bin/sandbox-exec")
_NAMESPACE = "ethos-independent-verification"
_SHA256_LENGTH = 64


class VerificationError(RuntimeError):
    """A fail-closed reference-adapter refusal with a stable reason token."""


def _fail(code: str) -> NoReturn:
    """Raise one stable machine-readable failure code."""
    raise VerificationError(code)


@dataclass(frozen=True)
class ReferenceVerifierConfig:
    """Provider-local configuration; never place this in an adopter repository."""

    account: str
    remote: str
    commit: str
    runtime_python: Path
    implementation_digest: str
    signing_key: Path
    key_id: str
    receipt_store: Path
    checkout_root: Path
    sandbox_exec: Path = _DEFAULT_SANDBOX


def _sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == _SHA256_LENGTH
        and all(char in "0123456789abcdef" for char in value)
    )


def _git_object_id(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) in {40, 64}
        and all(char in "0123456789abcdef" for char in value)
    )


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _absolute(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        _fail(f"config_invalid:{field}")
    path = Path(value).expanduser()
    if not path.is_absolute():
        _fail(f"config_invalid:{field}")
    return path.resolve()


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"config_invalid:{field}")
    return value


def load_config(path: Path) -> ReferenceVerifierConfig:
    """Load an explicit provider-owned TOML configuration."""
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        _fail("config_unreadable")
    identity = _mapping(payload.get("identity"))
    source = _mapping(payload.get("source"))
    runtime = _mapping(payload.get("runtime"))
    signing = _mapping(payload.get("signing"))
    storage = _mapping(payload.get("storage"))
    implementation_digest = _string(runtime.get("implementation_digest"), "implementation_digest")
    if not _sha256(implementation_digest):
        _fail("config_invalid:implementation_digest")
    commit = _string(source.get("commit"), "commit")
    if not _git_object_id(commit):
        _fail("config_invalid:commit")
    return ReferenceVerifierConfig(
        account=_string(identity.get("account"), "account"),
        remote=_string(source.get("remote"), "remote"),
        commit=commit,
        runtime_python=_absolute(runtime.get("python"), "runtime.python"),
        implementation_digest=implementation_digest,
        signing_key=_absolute(signing.get("key"), "signing.key"),
        key_id=_string(signing.get("key_id"), "signing.key_id"),
        receipt_store=_absolute(storage.get("receipt_store"), "storage.receipt_store"),
        checkout_root=_absolute(storage.get("checkout_root"), "storage.checkout_root"),
        sandbox_exec=_absolute(
            payload.get("sandbox_exec", _DEFAULT_SANDBOX.as_posix()), "sandbox_exec"
        ),
    )


def validate_request(config: ReferenceVerifierConfig, request: dict[str, object]) -> None:
    """Require the request to match the configured immutable source and proof form."""
    if request.get("remote") != config.remote:
        _fail("remote_not_allowlisted")
    if request.get("commit") != config.commit:
        _fail("foreign_commit")
    if request.get("action") != "publish":
        _fail("action_not_allowlisted")
    if request.get("proof_floor_id") != "ethos:promotion-required-gates:v1":
        _fail("proof_floor_not_allowlisted")
    request_implementation = request.get("implementation_digest")
    if request_implementation not in {"", config.implementation_digest}:
        _fail("implementation_mismatch")
    if not _git_object_id(request.get("tree")):
        _fail("request_invalid:tree")
    for field in ("proof_floor_digest", "policy_digest"):
        if not _sha256(request.get(field)):
            _fail(f"request_invalid:{field}")


def proof_child_environment(config: ReferenceVerifierConfig) -> dict[str, str]:
    """Return the tiny, key-free environment passed to clone and proof children."""
    return {
        "HOME": config.checkout_root.parent.as_posix(),
        "LANG": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
    }


def _sandbox_profile(config: ReferenceVerifierConfig, checkout: Path) -> str:
    """Build a deny-by-default profile for the fixed Git and Python proof commands."""
    roots = [
        "/System",
        "/usr",
        config.runtime_python.parent.parent.as_posix(),
        config.checkout_root.as_posix(),
        checkout.parent.as_posix(),
    ]
    reads = " ".join(f'(subpath "{root}")' for root in roots)
    return "\n".join(
        [
            "(version 1)",
            "(deny default)",
            f"(allow file-read* {reads})",
            f'(allow file-write* (subpath "{config.checkout_root.as_posix()}"))',
            "(allow process-exec",
            f'  (literal "{_GIT.as_posix()}")',
            f'  (literal "{config.runtime_python.as_posix()}")',
            '  (literal "/bin/sh")',
            '  (literal "/bin/bash")',
            f'  (subpath "{checkout.as_posix()}"))',
            "(allow process-fork)",
            "(deny network*)",
        ]
    )


def sandboxed_command(
    config: ReferenceVerifierConfig, command: list[str], checkout: Path
) -> list[str]:
    """Prefix one fixed command with mandatory sandbox-exec or refuse execution."""
    if not config.sandbox_exec.is_file() or not os.access(config.sandbox_exec, os.X_OK):
        _fail("sandbox_unavailable")
    if not command or Path(command[0]) not in {_GIT, config.runtime_python}:
        _fail("command_not_allowlisted")
    return [
        config.sandbox_exec.as_posix(),
        "-p",
        _sandbox_profile(config, checkout),
        *command,
    ]


def publish_receipt(
    config: ReferenceVerifierConfig, filename: str, payload: dict[str, object]
) -> Path:
    """Atomically publish an agent-readonly receipt to the provider-owned store."""
    if Path(filename).name != filename or not config.receipt_store.is_dir():
        _fail("receipt_publication_failed")
    target = config.receipt_store / filename
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=config.receipt_store, delete=False
        ) as temporary:
            temporary.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            temporary_path = Path(temporary.name)
        temporary_path.chmod(0o444)
        temporary_path.replace(target)
    except OSError:
        _fail("receipt_publication_failed")
    return target


def _run(
    config: ReferenceVerifierConfig, command: list[str], checkout: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        sandboxed_command(config, command, checkout),
        cwd=config.checkout_root,
        env=proof_child_environment(config),
        input=None,
        capture_output=True,
        check=False,
        timeout=1800,
    )


def _git_text(config: ReferenceVerifierConfig, checkout: Path, *args: str) -> str:
    completed = _run(config, [_GIT.as_posix(), *args], checkout)
    if completed.returncode != 0:
        _fail("independent_checkout_failed")
    return completed.stdout.decode("utf-8", errors="replace").strip()


def _canonical_payload(payload: dict[str, object]) -> bytes:
    body = {
        key: value for key, value in payload.items() if key not in {"signature", "payload_digest"}
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sign(config: ReferenceVerifierConfig, payload: dict[str, object], workspace: Path) -> str:
    if not _SSH_KEYGEN.is_file() or not config.signing_key.is_file():
        _fail("signing_unavailable")
    key_stat = config.signing_key.stat()
    if key_stat.st_uid != os.geteuid() or key_stat.st_mode & 0o077:
        _fail("signing_key_unprotected")
    message = workspace / "receipt-payload"
    message.write_bytes(_canonical_payload(payload))
    completed = subprocess.run(
        [
            _SSH_KEYGEN.as_posix(),
            "-Y",
            "sign",
            "-f",
            config.signing_key.as_posix(),
            "-n",
            _NAMESPACE,
            message.as_posix(),
        ],
        env=proof_child_environment(config),
        capture_output=True,
        check=False,
        timeout=30,
    )
    signature_path = message.with_suffix(".sig")
    if completed.returncode != 0 or not signature_path.is_file():
        _fail("receipt_signing_failed")
    return signature_path.read_text(encoding="utf-8")


def _assert_identity(config: ReferenceVerifierConfig) -> None:
    try:
        current = pwd.getpwuid(os.geteuid()).pw_name
    except KeyError:
        _fail("verifier_identity_unknown")
    if current != config.account:
        _fail("verifier_identity_mismatch")


def _proof_floor_digest(result: dict[str, object]) -> str:
    data = _mapping(result.get("data"))
    graph = _mapping(data.get("action_graph"))
    nodes = graph.get("nodes")
    gate_ids = (
        [
            node.get("id")
            for node in nodes
            if isinstance(node, dict) and isinstance(node.get("id"), str)
        ]
        if isinstance(nodes, list)
        else []
    )
    return hashlib.sha256(
        json.dumps({"gate_ids": sorted(gate_ids)}, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def reexecute(config: ReferenceVerifierConfig, request: dict[str, object]) -> Path:
    """Clone an allowlisted commit, run only the out-of-tree proof floor, and sign it."""
    _assert_identity(config)
    validate_request(config, request)
    request = {**request, "implementation_digest": config.implementation_digest}
    if not config.checkout_root.is_dir() or not config.receipt_store.is_dir():
        _fail("provider_storage_unavailable")
    with tempfile.TemporaryDirectory(dir=config.checkout_root) as tempdir:
        workspace = Path(tempdir)
        checkout = workspace / "checkout"
        clone = _run(
            config,
            [
                _GIT.as_posix(),
                "clone",
                "--no-checkout",
                config.remote,
                checkout.as_posix(),
            ],
            checkout,
        )
        if clone.returncode != 0:
            _fail("independent_checkout_failed")
        _git_text(
            config,
            checkout,
            "-C",
            checkout.as_posix(),
            "checkout",
            "--detach",
            config.commit,
        )
        actual_commit = _git_text(config, checkout, "-C", checkout.as_posix(), "rev-parse", "HEAD")
        actual_tree = _git_text(
            config, checkout, "-C", checkout.as_posix(), "rev-parse", "HEAD^{tree}"
        )
        if actual_commit != config.commit or actual_tree != request["tree"]:
            _fail("independent_checkout_binding_mismatch")
        proof = _run(
            config,
            [
                config.runtime_python.as_posix(),
                "-m",
                "ethos.cli",
                "prove",
                "--execute",
                "--expect-head",
                config.commit,
                "--root",
                checkout.as_posix(),
                "--json",
            ],
            checkout,
        )
        try:
            proof_payload = json.loads(proof.stdout.decode("utf-8"))
        except json.JSONDecodeError:
            _fail("independent_proof_invalid")
        if proof.returncode != 0 or proof_payload.get("ok") is not True:
            _fail("independent_proof_failed")
        if _proof_floor_digest(proof_payload) != request["proof_floor_digest"]:
            _fail("independent_proof_floor_mismatch")
        record_path = checkout / ".ethos" / "state" / "proof" / f"{config.commit}.json"
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            _fail("independent_proof_record_missing")
        if record.get("gate_policy_digest") != request["policy_digest"]:
            _fail("independent_policy_mismatch")
        now = datetime.now(UTC)
        receipt = {
            **request,
            "result": "pass",
            "issuer": f"local-independent-identity:{config.account}",
            "key_id": config.key_id,
            "signature_algorithm": "ssh-ed25519",
            "signature": "",
            "issued_at": now.isoformat(),
            "valid_until": (now + timedelta(minutes=10)).isoformat(),
            "payload_digest": "",
        }
        receipt["payload_digest"] = hashlib.sha256(_canonical_payload(receipt)).hexdigest()
        receipt["signature"] = _sign(config, receipt, workspace)
        return publish_receipt(config, f"{config.commit}-{request['action']}.json", receipt)


def _load_request(path: Path) -> dict[str, object]:
    """Load one JSON request before the command's exception boundary."""
    request = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        _fail("request_invalid")
    return request


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        receipt = reexecute(load_config(args.config), _load_request(args.request))
    except (OSError, json.JSONDecodeError, VerificationError) as exc:
        sys.stdout.write(json.dumps({"ok": False, "error": str(exc)}) + "\n")
        return 1
    sys.stdout.write(json.dumps({"ok": True, "receipt": receipt.as_posix()}) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
