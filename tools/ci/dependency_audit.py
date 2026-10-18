"""Audit both native dependency locks without conflating unavailable and clean evidence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from filelock import FileLock
from filelock import Timeout

import ethos.adapters.repo.runtime.materialization.input_resolution as input_resolution
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.dependency_acceptance import product_audit_snapshot
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.runtime.authority import invoking_build_identity
from ethos.contracts.verdict import reduce_verdicts
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_POLICY_PATH
from ethos.repository.policy.quality.dependency_acceptance import AuditPolicy
from ethos.repository.policy.quality.dependency_acceptance import audit_workspace_manifests
from ethos.repository.policy.quality.dependency_acceptance import compose_audit_policies
from ethos.repository.policy.quality.dependency_acceptance import evaluate_dependency_acceptance
from ethos.repository.policy.quality.dependency_acceptance import interpret_native_audit
from ethos.repository.policy.quality.dependency_acceptance import npm_upstream_owners
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

    from ethos.repository.policy.quality.dependency_acceptance import AuditScope

ROOT = Path(__file__).resolve().parents[2]
POLICY = AUDIT_POLICY_PATH
EVIDENCE = "build/evidence/quality/security"
# npm never retries POST, so a dropped bulk advisory request is observed again here.
_ATTEMPTS = 3
_RETRY_PAUSE_SECONDS = 2


def requested_scope(arguments: tuple[str, ...]) -> AuditScope:
    """Accept explicit local iteration only; no ambient setting relaxes the gate."""
    if not arguments:
        return "production-release"
    if arguments in (("--scope", "local-development"), ("--scope", "production-release")):
        return "local-development" if arguments[1] == "local-development" else "production-release"
    message = "dependency_audit_scope_invalid"
    raise ValueError(message)


def _local_decision(policy: AuditPolicy, payload: dict, scope: str, *, lock_source: bytes) -> dict:
    """Capture native context separately from the shared pure permission algebra."""
    return evaluate_dependency_acceptance(
        policy,
        payload,
        lock_source=lock_source,
        scope=requested_scope(("--scope", scope)),
        host=platform.node(),
        now=datetime.now(UTC),
        ci=bool(os.environ.get("CI")),
    )


def _inputs(
    root: Path, *, policy_bytes: bytes | None = None
) -> tuple[dict[str, str | None], dict[str, list[str]], dict[str, bytes]]:
    """Observe each native scope independently, including missing input identities."""
    hashes: dict[str, str | None] = {}
    materials: dict[str, bytes] = {}
    errors: dict[str, list[str]] = {"python": [], "npm": []}

    def bind(name: str) -> bytes:
        if name in materials:
            return materials[name]
        path = Path(name)
        hashes[name] = None
        if (
            path.is_absolute()
            or ".." in path.parts
            or not (root / path).resolve().is_relative_to(root)
        ):
            message = f"audit input escapes repository: {name}"
            raise ValueError(message)
        data = (
            policy_bytes
            if name == POLICY and policy_bytes is not None
            else (root / path).read_bytes()
        )
        hashes[name] = hashlib.sha256(data).hexdigest()
        materials[name] = data
        return data

    for shared in AUDIT_INPUTS[4:]:
        bind(shared)
    for ecosystem, names in (("python", AUDIT_INPUTS[:2]), ("npm", AUDIT_INPUTS[2:4])):
        for name in names:
            try:
                data = bind(name)
                for manifest in audit_workspace_manifests(name, data):
                    bind(manifest)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                errors[ecosystem].append(f"{name}: {error}")
    return hashes, errors, materials


def _command(ecosystem: str, root: Path) -> tuple[str, ...]:
    """Resolve tools from the current locked interpreter, never ambient PATH."""
    if ecosystem == "python":
        return (
            ProjectRuntime.discover(root).script("uv"),
            "audit",
            "--preview-features",
            "audit-command",
            "--preview-features",
            "json-output",
            "--frozen",
            "--output-format",
            "json",
        )
    runtime = input_resolution.resolve_node_runtime()
    return (
        str(runtime.executable),
        str(runtime.npm),
        "audit",
        "--package-lock-only",
        "--ignore-scripts",
        "--include=dev",
        "--include=optional",
        "--include=peer",
        "--json",
    )


def _observe(root: Path, ecosystem: str, timeout: int) -> dict:
    """Repeat only a failed npm advisory request; every attempt stays in the receipt."""
    attempts: list[dict] = []
    while True:
        result = _observe_once(root, ecosystem, timeout)
        attempts.append(
            {key: result.get(key) for key in ("verdict", "reason", "exit_code", "stderr")}
        )
        if result["reason"] != "advisory_request_failed" or len(attempts) == _ATTEMPTS:
            return {**result, "attempts": attempts}
        time.sleep(_RETRY_PAUSE_SECONDS)


def _observe_once(root: Path, ecosystem: str, timeout: int) -> dict:
    """Settle one external observation, preserving failures before continuing."""
    command: tuple[str, ...] = ()
    try:
        command = _command(ecosystem, root)
        completed = run_command(root, command, timeout=timeout, remove_env_prefixes=("GIT_",))
        verdict, reason, details = interpret_native_audit(
            ecosystem, completed.stdout, completed.returncode
        )

    except (
        OSError,
        ValueError,
        RuntimeError,
        ProcessExecutionError,
        subprocess.TimeoutExpired,
    ) as error:

        def text(value: str | bytes | None) -> str:
            return value.decode(errors="replace") if isinstance(value, bytes) else value or ""

        return {
            "ecosystem": ecosystem,
            "command": command,
            "verdict": "unknown",
            "reason": "native_execution_unavailable",
            "exit_code": None,
            "stdout": text(getattr(error, "output", None)),
            "stderr": text(getattr(error, "stderr", None)) or str(error),
            "failure": error.evidence()
            if isinstance(error, ProcessExecutionError)
            else {
                "kind": type(error).__name__,
                "cause": str(error),
            },
        }

    else:
        return {
            "ecosystem": ecosystem,
            "command": command,
            "verdict": verdict,
            "reason": reason,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            **details,
        }


def _upstream(root: Path, checks: list[dict], lock_source: bytes, timeout: int) -> dict:
    """Observe each npm finding owner's latest stable release; any failure stays unobserved."""
    observation: dict = {"npm": {}, "observed_at": datetime.now(UTC).isoformat()}
    try:
        adverse = checks[1]["verdict"] == "block"
        owners = sorted(npm_upstream_owners(lock_source, checks[1])) if adverse else []
        runtime = input_resolution.resolve_node_runtime() if owners else None
    except (IndexError, KeyError, TypeError, ValueError, OSError, RuntimeError):
        return observation
    if runtime is None:
        return observation
    for name in owners:
        command = (str(runtime.executable), str(runtime.npm), "view", f"{name}@latest", "version")
        try:
            completed = run_command(
                root, (*command, "--json"), timeout=timeout, remove_env_prefixes=("GIT_",)
            )
            value = json.loads(completed.stdout) if completed.returncode == 0 else None
        except (OSError, ValueError, ProcessExecutionError, subprocess.TimeoutExpired):
            value = None
        # The native `name@latest` view is a one-element array; any other shape stays unobserved.
        if isinstance(value, list) and len(value) == 1 and isinstance(value[0], str) and value[0]:
            observation["npm"][name] = value[0]
    return observation


def _write(path: Path, payload: dict) -> None:
    """Replace the diagnostic receipt atomically; old success cannot survive a new attempt."""
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _require_head(head: str) -> None:
    if not head:
        message = "audit source HEAD missing"
        raise ValueError(message)


def run(session: nox.Session, *, root: Path = ROOT, scope: str = "production-release") -> None:
    """Own one bounded audit attempt; contention never overwrites active evidence."""
    root = root.resolve()
    evidence = root / EVIDENCE
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(evidence / ".dependency-audit.lock", timeout=0):
            _run(session, root=root, scope=scope)
    except Timeout:
        session.error("dependency_audit_in_use: " + str(evidence))


def _run(session: nox.Session, *, root: Path = ROOT, scope: str = "production-release") -> None:
    """Observe both native ecosystems and reject incomplete or changed inputs."""
    root = root.resolve()
    evidence = root / EVIDENCE
    evidence.mkdir(parents=True, exist_ok=True)
    summary = evidence / "dependency-audit.json"
    payload: dict = {
        "command": "dependency-audit",
        "verdict": "unknown",
        "state": "running",
        "generated_at": datetime.now(UTC).isoformat(),
        "checks": [],
        "required_gaps": ["dependency_audit_incomplete"],
        "not_claimed": ["hosted CI", "image scanning", "remote publication"],
        "decision": {"scope": scope, "verdict": "unknown", "reason": "dependency_audit_incomplete"},
    }
    _write(summary, payload)
    try:
        requested_scope(("--scope", scope))
        policy_bytes = (root / POLICY).read_bytes()
        policy = AuditPolicy.model_validate(tomllib.loads(policy_bytes.decode("utf-8")))
        timeout = policy.timeout_seconds
        head, before = current_tracked_head(root), _inputs(root, policy_bytes=policy_bytes)
        _require_head(head)
        product, binding = product_audit_snapshot(build=invoking_build_identity())
        payload.update(head=head, inputs=before[0], timeout_seconds=timeout, product_policy=binding)
        checks = payload["checks"]
        for ecosystem in ("python", "npm"):
            problems = before[1][ecosystem]
            result = (
                {
                    "ecosystem": ecosystem,
                    "verdict": "unknown",
                    "reason": "audit_inputs_unavailable",
                    "input_errors": problems,
                    "command": (),
                    "exit_code": None,
                    "stdout": "",
                    "stderr": "\n".join(problems),
                }
                if problems
                else _observe(root, ecosystem, timeout)
            )
            checks.append(result)
            _write(summary, payload)
        gaps = [
            f"{check['ecosystem']}:{check['reason']}"
            for check in checks
            if check["verdict"] != "pass"
        ]
        verdict = reduce_verdicts(*(check["verdict"] for check in checks))
        lock_source = before[2].get("package-lock.json", b"")
        payload["upstream"] = _upstream(root, checks, lock_source, timeout)
        payload.update(verdict=verdict, state="finished", required_gaps=gaps)
        payload["decision"] = _local_decision(
            compose_audit_policies(policy, product),
            payload,
            scope,
            lock_source=lock_source,
        )
        if head != current_tracked_head(root) or before != _inputs(root):
            payload["verdict"] = "block"
            gaps.append("dependency_audit_inputs_changed")
            payload["decision"] = {
                "scope": scope,
                "verdict": "block",
                "reason": "dependency_audit_inputs_changed",
            }
        _product, after_binding = product_audit_snapshot(build=invoking_build_identity())
        if binding != after_binding:
            payload["verdict"] = "block"
            gaps.append("dependency_audit_product_policy_changed")
            payload["decision"] = {
                "scope": scope,
                "verdict": "block",
                "reason": "dependency_audit_product_policy_changed",
            }
    except (OSError, ValueError, KeyError, TypeError) as error:
        payload.update(verdict="unknown", state="unavailable", required_gaps=[str(error)])
        payload["decision"] = {"scope": scope, "verdict": "unknown", "reason": "audit_unavailable"}
    _write(summary, payload)
    print(json.dumps(payload, sort_keys=True), flush=True)
    if payload["decision"]["verdict"] != "pass":
        session.error("Dependency audit did not pass; inspect " + str(summary))
