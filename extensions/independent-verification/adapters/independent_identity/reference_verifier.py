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


def _hex(value: object, lengths: tuple[int, ...]) -> bool:
    return (
        isinstance(value, str)
        and len(value) in lengths
        and not set(value) - set("0123456789abcdef")
    )


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        _fail(f"config_invalid:{field}")
    return value


def _path(value: object, field: str, *, keep: bool = False) -> Path:
    path = Path(_string(value, field)).expanduser()
    if not path.is_absolute():
        _fail(f"config_invalid:{field}")
    return path if keep else path.resolve()


def load_config(path: Path) -> ReferenceVerifierConfig:
    """Load an explicit provider-owned TOML configuration."""
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        _fail("config_unreadable")
    identity, source, runtime, signing, storage = (
        value if isinstance(value := payload.get(field), dict) else {}
        for field in ("identity", "source", "runtime", "signing", "storage")
    )
    if not _hex(
        implementation_digest := _string(
            runtime.get("implementation_digest"), "implementation_digest"
        ),
        (_SHA256_LENGTH,),
    ):
        _fail("config_invalid:implementation_digest")
    if not _hex(commit := _string(source.get("commit"), "commit"), (40, 64)):
        _fail("config_invalid:commit")
    return ReferenceVerifierConfig(
        account=_string(identity.get("account"), "account"),
        remote=_string(source.get("remote"), "remote"),
        commit=commit,
        runtime_python=_path(runtime.get("python"), "runtime.python", keep=True),
        implementation_digest=implementation_digest,
        signing_key=_path(signing.get("key"), "signing.key"),
        key_id=_string(signing.get("key_id"), "signing.key_id"),
        receipt_store=_path(storage.get("receipt_store"), "storage.receipt_store"),
        checkout_root=_path(storage.get("checkout_root"), "storage.checkout_root"),
        sandbox_exec=_path(
            payload.get("sandbox_exec", _DEFAULT_SANDBOX.as_posix()), "sandbox_exec"
        ),
    )


def validate_request(config: ReferenceVerifierConfig, request: dict[str, object]) -> None:
    """Require the request to match the configured immutable source and proof form."""
    for field, expected, error in (
        ("remote", config.remote, "remote_not_allowlisted"),
        ("commit", config.commit, "foreign_commit"),
        ("action", "publish", "action_not_allowlisted"),
        ("proof_floor_id", "ethos:promotion-required-gates:v1", "proof_floor_not_allowlisted"),
    ):
        if request.get(field) != expected:
            _fail(error)
    if request.get("implementation_digest") not in {"", config.implementation_digest}:
        _fail("implementation_mismatch")
    if not _hex(request.get("tree"), (40, 64)):
        _fail("request_invalid:tree")
    for field in ("proof_floor_digest", "policy_digest"):
        if not _hex(request.get(field), (_SHA256_LENGTH,)):
            _fail(f"request_invalid:{field}")


def proof_child_environment(
    config: ReferenceVerifierConfig, *, checkout: Path | None = None
) -> dict[str, str]:
    """Return a key-free, offline environment bound to one checkout when present."""
    python = config.runtime_python.as_posix()
    environment = {
        "HOME": config.checkout_root.parent.as_posix(),
        "LANG": "C.UTF-8",
        "PATH": f"{config.runtime_python.parent.as_posix()}:"
        "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin",
        "ETHOS_PYTHON": python,
        "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENSPEC_TELEMETRY": "0",
        "UV_OFFLINE": "1",
        "UV_PROJECT_ENVIRONMENT": config.runtime_python.parent.parent.as_posix(),
    }
    if checkout is None:
        return environment
    scratch, cache = checkout.parent / "scratch", checkout.parent / "scratch" / "cache"
    return environment | {
        "HOME": scratch.as_posix(),
        "TMPDIR": scratch.as_posix(),
        "UV_CACHE_DIR": cache.as_posix(),
        "XDG_CACHE_HOME": cache.as_posix(),
        "RUFF_CACHE_DIR": (cache / "ruff").as_posix(),
        "PYTHONPATH": ":".join(
            (checkout / path).as_posix()
            for path in ("packages/ethos/src", "packages/ethos-core/src")
        ),
    }


def _sandbox_profile(config: ReferenceVerifierConfig, checkout: Path) -> str:
    """Build a deny-by-default profile for the fixed Git and Python proof commands."""
    return "\n".join(
        [
            "(version 1)",
            "(deny default)",
            '(import "system.sb")',
            "(deny network*)",
            "(allow file-read*)",
            f'(allow file-write* (subpath "{checkout.parent.as_posix()}"))',
            '(allow file-write* (literal "/dev/null"))',
            '(allow file-read-metadata (literal "/dev"))',
            "(allow process-exec)",
            "(allow process-fork)",
            '(allow mach-lookup (global-name "com.apple.SystemConfiguration.configd"))',
            '(allow process-exec (with no-sandbox) (literal "/bin/ps"))',
            '(deny file-read* file-write* (subpath "/etc/ethos"))',
            '(deny file-read* file-write* (subpath "/var/db/ethos"))',
            '(deny file-read* file-write* (subpath "/Library/Application Support/ETHOS"))',
            f'(deny file-read* file-write* (literal "{config.signing_key.as_posix()}"))',
            f'(deny file-read* file-write* (subpath "{config.receipt_store.as_posix()}"))',
        ]
    )


def sandboxed_command(
    config: ReferenceVerifierConfig, command: list[str], checkout: Path
) -> list[str]:
    """Prefix one fixed command with mandatory sandbox-exec or refuse execution."""
    if not config.sandbox_exec.is_file() or not os.access(config.sandbox_exec, os.X_OK):
        _fail("sandbox_unavailable")
    if not command or command[0] not in (_GIT.as_posix(), config.runtime_python.as_posix()):
        _fail("command_not_allowlisted")
    return [config.sandbox_exec.as_posix(), "-p", _sandbox_profile(config, checkout), *command]


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
    config: ReferenceVerifierConfig,
    command: list[str],
    checkout: Path,
    *,
    proof: bool = False,
) -> subprocess.CompletedProcess[bytes]:
    cwd = checkout.parent
    cwd.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        sandboxed_command(config, command, checkout),
        cwd=cwd,
        env=proof_child_environment(config, checkout=checkout if proof else None),
        input=None,
        capture_output=True,
        check=False,
        timeout=1800,
    )


def _git_text(config: ReferenceVerifierConfig, checkout: Path, *args: str) -> str:
    command = [_GIT.as_posix(), "-c", "core.hooksPath=/dev/null", "-C", checkout.as_posix(), *args]
    completed = _run(config, command, checkout, proof=True)
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
    data = result.get("data")
    graph = data.get("action_graph") if isinstance(data, dict) else {}
    nodes = graph.get("nodes") if isinstance(graph, dict) else ()
    gate_ids = sorted(
        node["id"]
        for node in (nodes if isinstance(nodes, list) else ())
        if isinstance(node, dict) and isinstance(node.get("id"), str)
    )
    return hashlib.sha256(
        json.dumps({"gate_ids": gate_ids}, sort_keys=True, separators=(",", ":")).encode("utf-8")
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
            proof=True,
        )
        if clone.returncode != 0:
            _fail("independent_checkout_failed")
        _git_text(config, checkout, "checkout", "--detach", config.commit)
        actual_commit = _git_text(config, checkout, "rev-parse", "HEAD")
        actual_tree = _git_text(config, checkout, "rev-parse", "HEAD^{tree}")
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
