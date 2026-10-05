"""Audit both native dependency locks without conflating unavailable and clean evidence."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Literal

from filelock import FileLock
from filelock import Timeout
from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator

import ethos.adapters.repo.runtime.materialization.input_resolution as input_resolution
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.contracts.verdict import reduce_verdicts
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

    from ethos.contracts.verdict import Verdict

ROOT = Path(__file__).resolve().parents[2]
POLICY = ".config/checks/security/audit.toml"
EVIDENCE = "build/evidence/quality/security"
INPUTS = ("pyproject.toml", "uv.lock", "package.json", "package-lock.json", POLICY)


class AuditDisposition(BaseModel):
    """Bind human-authorized local use to one exact advisory and locked artifact."""

    model_config = ConfigDict(extra="forbid", strict=True)
    ecosystem: Literal["npm"]
    advisory_url: str = Field(pattern=r"^https://[^\s]+$")
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    integrity: str = Field(min_length=1)
    nodes: list[str] = Field(min_length=1)
    lock_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    scope: Literal["local-development"]
    host: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    approval_ref: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expires_at: AwareDatetime

    @field_validator(
        "owner", "approval_ref", "rationale", "package", "version", "integrity", "host"
    )
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            message = "disposition identity and authorization must be nonblank and exact"
            raise ValueError(message)
        return value

    @field_validator("nodes")
    @classmethod
    def unique_nodes(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)) or not all(value):
            message = "disposition nodes must be nonempty and unique"
            raise ValueError(message)
        return value

    def subject(self) -> tuple:
        """Return the exact native finding identity; authorization is evaluated separately."""
        return (
            self.advisory_url,
            self.package,
            self.version,
            self.integrity,
            tuple(sorted(self.nodes)),
        )


class AuditPolicy(BaseModel):
    """Declare native audit execution without accepting silent policy typos."""

    model_config = ConfigDict(extra="forbid", strict=True)
    owner: str
    summary: str
    runner: str
    timeout_seconds: int = Field(gt=0)
    dispositions: list[AuditDisposition] = Field(default_factory=list)


def requested_scope(arguments: tuple[str, ...]) -> str:
    """Accept explicit local iteration only; no ambient setting relaxes the gate."""
    if not arguments:
        return "production-release"
    if arguments in (("--scope", "local-development"), ("--scope", "production-release")):
        return arguments[1]
    message = "dependency_audit_scope_invalid"
    raise ValueError(message)


def _npm_roots(raw: dict) -> dict[str, set[tuple[str, str]]]:
    """Resolve npm package aggregates to concrete advisories without counting strings as IDs."""
    aggregates = raw["vulnerabilities"]
    references, direct = {}, {}
    for name, finding in aggregates.items():
        if finding["name"] != name or not isinstance(finding["via"], list) or not finding["via"]:
            message = "invalid npm aggregate identity"
            raise ValueError(message)
        references[name], direct[name] = set(), set()
        for via in finding["via"]:
            if isinstance(via, str) and via in aggregates:
                references[name].add(via)
            elif isinstance(via, dict):
                url, dependency = via["url"], via["dependency"]
                if not isinstance(url, str) or not url.startswith("https://") or dependency != name:
                    message = "invalid npm advisory identity"
                    raise ValueError(message)
                direct[name].add((url, dependency))
            else:
                message = "unresolved npm aggregate reference"
                raise ValueError(message)
    resolved: dict[str, set[tuple[str, str]]] = {}
    pending = set(aggregates)
    while pending:
        ready = {name for name in pending if references[name] <= resolved.keys()}
        if not ready:
            message = "cyclic npm aggregate references"
            raise ValueError(message)
        for name in ready:
            resolved[name] = direct[name].union(*(resolved[item] for item in references[name]))
        pending -= ready
    return resolved


def _locked_artifact_integrity(node: str, packages: dict) -> str:
    """Bind inBundle bytes to their containing lock artifact, never a fabricated child hash."""
    locked = packages[node]
    integrity = locked.get("integrity")
    if integrity is not None:
        if not isinstance(integrity, str) or not integrity.strip():
            message = "npm locked artifact integrity unavailable"
            raise ValueError(message)
        return integrity
    if locked.get("inBundle") is not True or "/node_modules/" not in node:
        message = "npm locked artifact identity unavailable"
        raise ValueError(message)
    return _locked_artifact_integrity(node.rsplit("/node_modules/", 1)[0], packages)


def _locked_instances(name: str, finding: dict, packages: dict) -> dict:
    """Bind every native aggregate node to its exact package-lock artifact identity."""
    nodes = finding["nodes"]
    if not isinstance(nodes, list) or not nodes:
        message = "npm aggregate nodes missing"
        raise ValueError(message)
    instances: dict[tuple[str, str], set[str]] = {}
    for node in nodes:
        if (
            not isinstance(node, str)
            or "\\" in node
            or any(part in {"", ".", ".."} for part in node.split("/"))
            or not (node == "node_modules/" + name or node.endswith("/node_modules/" + name))
        ):
            message = "invalid npm lock node"
            raise ValueError(message)
        locked = packages[node]
        identity = locked["version"], _locked_artifact_integrity(node, packages)
        if not all(isinstance(value, str) and value.strip() for value in identity):
            message = "npm locked artifact identity unavailable"
            raise ValueError(message)
        instances.setdefault(identity, set()).add(node)
    return instances


def _npm_subjects(root: Path, check: dict) -> tuple[set[tuple], int]:
    """Derive exact advisory subjects while retaining native aggregate counts unchanged."""
    raw = json.loads(check["stdout"])
    roots = _npm_roots(raw)
    packages = json.loads((root / "package-lock.json").read_bytes())["packages"]
    instances = {
        name: _locked_instances(name, finding, packages)
        for name, finding in raw["vulnerabilities"].items()
    }
    subjects = {
        (url, package, version, integrity, tuple(sorted(nodes)))
        for url, package in set().union(*roots.values())
        for (version, integrity), nodes in instances[package].items()
    }
    if not subjects or any(not values for values in roots.values()):
        message = "npm advisory roots unavailable"
        raise ValueError(message)
    return subjects, len(roots)


def _local_decision(root: Path, policy: AuditPolicy, payload: dict, scope: str) -> dict:
    """Separate exact local permission from the unchanged strict native verdict."""
    decision = {"scope": scope, "verdict": payload["verdict"], "reason": "strict_native_result"}
    if scope == "local-development" and os.environ.get("CI"):
        return {**decision, "verdict": "block", "reason": "local_development_context_required"}
    if scope != "local-development" or payload["verdict"] == "pass":
        return decision
    checks = payload["checks"]
    if (
        payload["state"] != "finished"
        or "dependency_audit_inputs_changed" in payload["required_gaps"]
        or len(checks) != 2
        or checks[0]["verdict"] != "pass"
        or checks[1]["verdict"] != "block"
    ):
        return decision
    if checks[1]["exit_code"] not in (0, 1):
        return {**decision, "verdict": "unknown", "reason": "native_execution_failed"}
    try:
        subjects, aggregates = _npm_subjects(root, checks[1])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return {
            **decision,
            "verdict": "unknown",
            "reason": "finding_identity_unavailable",
            "detail": str(error),
        }
    now = datetime.now(UTC)
    matching = [
        record
        for record in policy.dispositions
        if record.lock_sha256 == payload["inputs"]["package-lock.json"]
        and record.host == platform.node()
        and record.subject() in subjects
    ]
    active = [record for record in matching if now < record.expires_at]
    covered = {record.subject() for record in active}
    authorized = subjects <= covered
    return {
        "scope": scope,
        "verdict": "pass" if authorized else "block",
        "reason": "authorized_findings" if authorized else "unapproved_or_expired_findings",
        "evaluated_at": now.isoformat(),
        "host": platform.node(),
        "advisory_count": len({subject[0] for subject in subjects}),
        "covered_package_count": aggregates if authorized else 0,
        "approvals": [record.model_dump(mode="json") for record in active],
        "expired_approvals": [
            record.approval_ref for record in matching if now >= record.expires_at
        ],
        "unapproved_subjects": sorted(subjects - covered),
    }


def _count(value: object) -> bool:
    return type(value) is int and value >= 0


def _python_counts(raw: dict) -> tuple[int, int]:
    summary = raw["summary"]
    counts = tuple(
        summary[key] for key in ("audited_packages", "vulnerabilities", "adverse_statuses")
    )
    if (
        not all(_count(value) for value in counts)
        or counts[0] == 0
        or not isinstance(raw["vulnerabilities"], list)
        or not isinstance(raw["adverse_statuses"], list)
        or counts[1] != len(raw["vulnerabilities"])
        or counts[2] != len(raw["adverse_statuses"])
    ):
        message = "inconsistent native Python counts"
        raise ValueError(message)
    return counts[0], counts[1] + counts[2]


def _npm_counts(raw: dict) -> tuple[int, int]:
    summary = raw["metadata"]
    vulnerabilities = summary["vulnerabilities"]
    counts = tuple(vulnerabilities[key] for key in ("info", "low", "moderate", "high", "critical"))
    total, dependencies = vulnerabilities["total"], summary["dependencies"]["total"]
    if (
        raw["auditReportVersion"] != 2
        or not all(_count(value) for value in (*counts, total, dependencies))
        or dependencies == 0
        or total != sum(counts)
        or not isinstance(raw["vulnerabilities"], dict)
        or total != len(raw["vulnerabilities"])
        or raw.get("error")
    ):
        message = "inconsistent native npm counts"
        raise ValueError(message)
    return dependencies, total


def _interpret(ecosystem: str, output: str, exit_code: int) -> tuple[Verdict, str, dict]:
    try:
        raw = json.loads(output)
        dependencies, findings = (_python_counts if ecosystem == "python" else _npm_counts)(raw)
    except (KeyError, TypeError, ValueError, AttributeError):
        return "unknown", "native_output_invalid", {}
    details = {"dependency_count": dependencies, "finding_count": findings}
    if findings:
        return "block", "vulnerabilities_or_adverse_statuses", details
    if exit_code:
        return "unknown", "native_execution_failed", details
    return "pass", "clean", details


def _workspace_manifests(name: str, data: bytes) -> tuple[str, ...]:
    """Read local workspace identities using each native lock's data format."""
    if name == "package-lock.json":
        packages = json.loads(data)["packages"]
        return tuple(
            f"{path}/package.json"
            for path in packages
            if path and "node_modules" not in Path(path).parts
        )
    if name == "uv.lock":
        packages = tomllib.loads(data.decode()).get("package", [])
        return tuple(
            str(Path(source[kind]) / "pyproject.toml")
            for package in packages
            for source in (package.get("source", {}),)
            for kind in ("editable", "virtual", "directory")
            if kind in source
        )
    return ()


def _inputs(
    root: Path, *, policy_bytes: bytes | None = None
) -> tuple[dict[str, str | None], dict[str, list[str]]]:
    """Observe each native scope independently, including missing input identities."""
    hashes: dict[str, str | None] = {}
    errors: dict[str, list[str]] = {"python": [], "npm": []}

    def bind(name: str) -> bytes:
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
        return data

    for shared in (POLICY, "tools/ci/dependency_audit.py", "tools/ci/sessions.py"):
        bind(shared)
    for ecosystem, names in (("python", INPUTS[:2]), ("npm", INPUTS[2:4])):
        for name in names:
            try:
                data = bind(name)
                for manifest in _workspace_manifests(name, data):
                    bind(manifest)
            except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
                errors[ecosystem].append(f"{name}: {error}")
    return hashes, errors


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
    """Settle one external observation, preserving failures before continuing."""
    command: tuple[str, ...] = ()
    try:
        command = _command(ecosystem, root)
        completed = run_command(root, command, timeout=timeout, remove_env_prefixes=("GIT_",))
        verdict, reason, details = _interpret(ecosystem, completed.stdout, completed.returncode)

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
        payload.update(head=head, inputs=before[0], timeout_seconds=timeout)
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
        payload.update(verdict=verdict, state="finished", required_gaps=gaps)
        payload["decision"] = _local_decision(root, policy, payload, scope)
        if head != current_tracked_head(root) or before != _inputs(root):
            payload["verdict"] = "block"
            gaps.append("dependency_audit_inputs_changed")
            payload["decision"] = {
                "scope": scope,
                "verdict": "block",
                "reason": "dependency_audit_inputs_changed",
            }
    except (OSError, ValueError, KeyError, TypeError) as error:
        payload.update(verdict="unknown", state="unavailable", required_gaps=[str(error)])
        payload["decision"] = {"scope": scope, "verdict": "unknown", "reason": "audit_unavailable"}
    _write(summary, payload)
    session.log(json.dumps(payload, sort_keys=True))
    if payload["decision"]["verdict"] != "pass":
        session.error("Dependency audit did not pass; inspect " + str(summary))
