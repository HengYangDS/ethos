"""Interpret exact native findings and bounded permission without executing an audit."""

from __future__ import annotations

import hashlib
import json
import sys
import tomllib
from pathlib import PurePosixPath
from typing import TYPE_CHECKING
from typing import Literal

import tomli_w
from pydantic import AwareDatetime
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from ethos.contracts.gates import bind_gate_command
from ethos.contracts.verdict import reduce_verdicts
from ethos.repository.policy.quality.gate_composition import canonical_gate_command
from ethos.repository.policy.quality.upstream_fixes import npm_owners
from ethos.repository.policy.quality.upstream_fixes import python_findings
from ethos.repository.policy.quality.upstream_fixes import unfixed_npm_subjects

if TYPE_CHECKING:
    from collections.abc import Iterable
    from collections.abc import Mapping
    from datetime import datetime

    from ethos.contracts.verdict import Verdict

AUDIT_POLICY_PATH = ".config/checks/dependency-vulnerabilities/policy.toml"
AUDIT_INPUTS = (
    "pyproject.toml",
    "uv.lock",
    "package.json",
    "package-lock.json",
    AUDIT_POLICY_PATH,
    "tools/ci/dependency_audit.py",
    "tools/ci/sessions.py",
)

AuditScope = Literal["production-release", "local-development"]
AuditSubject = tuple[str, str, str, str, tuple[str, ...]]


class AuditDisposition(BaseModel):
    """Bind accepted risk to an exact advisory/artifact and its authorized context."""

    model_config = ConfigDict(extra="forbid", strict=True)
    ecosystem: Literal["npm"]
    advisory_url: str = Field(pattern=r"^https://[^\s]+$")
    package: str = Field(min_length=1)
    version: str = Field(min_length=1)
    integrity: str = Field(min_length=1)
    nodes: list[str] = Field(default_factory=list)
    lock_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    scope: AuditScope
    host: str | None = Field(default=None, min_length=1)
    owner: str = Field(min_length=1)
    approval_ref: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    expires_at: AwareDatetime | None = None

    @field_validator("owner", "approval_ref", "rationale", "package", "version", "integrity")
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

    @model_validator(mode="after")
    def bounded_local_context(self) -> AuditDisposition:
        """Local-only permission always names its host, lock, instances and deadline."""
        if self.host is not None and self.host != self.host.strip():
            message = "disposition host must be exact"
            raise ValueError(message)
        if self.scope == "local-development" and not all(
            (self.host, self.lock_sha256, self.nodes, self.expires_at)
        ):
            message = "local-development disposition requires host, lock, nodes and expiry"
            raise ValueError(message)
        return self

    def matches(self, subject: AuditSubject, *, lock_sha256: str, host: str) -> bool:
        """Match actual locked artifact bytes; optional coordinates only narrow authority."""
        return (
            self.subject()[:4] == subject[:4]
            and (not self.nodes or tuple(sorted(self.nodes)) == subject[4])
            and (self.lock_sha256 is None or self.lock_sha256 == lock_sha256)
            and (self.host is None or self.host == host)
        )

    def subject(self) -> AuditSubject:
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


def product_audit_projection(source: bytes) -> bytes:
    """Ship exact portable release approvals, never host-local development authority."""
    policy = AuditPolicy.model_validate(tomllib.loads(source.decode("utf-8")))
    records = [record for record in policy.dispositions if record.scope == "production-release"]
    if any(record.host is not None for record in records):
        message = "product_audit_policy_host_bound"
        raise ValueError(message)
    projected = policy.model_copy(update={"dispositions": records})
    return tomli_w.dumps(projected.model_dump(mode="python", exclude_none=True)).encode("utf-8")


def compose_audit_policies(subject: AuditPolicy, product: AuditPolicy) -> AuditPolicy:
    """Compose exact approvals once while retaining the subject's execution declaration."""
    records: list[AuditDisposition] = []
    for record in (*subject.dispositions, *product.dispositions):
        if record not in records:
            records.append(record)
    return subject.model_copy(update={"dispositions": records})


def audit_workspace_manifests(name: str, data: bytes) -> tuple[str, ...]:
    """Derive the audited local input closure from each native lock once."""
    if name == "package-lock.json":
        return tuple(
            f"{path}/package.json"
            for path in json.loads(data)["packages"]
            if path and "node_modules" not in PurePosixPath(path).parts
        )
    if name == "uv.lock":
        return tuple(
            str(PurePosixPath(source[kind]) / "pyproject.toml")
            for package in tomllib.loads(data.decode()).get("package", [])
            for source in (package.get("source", {}),)
            for kind in ("editable", "virtual", "directory")
            if kind in source
        )
    return ()


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


def _npm_subjects(lock_source: bytes, check: dict) -> tuple[set[AuditSubject], int]:
    """Derive exact advisory subjects while retaining native aggregate counts unchanged."""
    raw = json.loads(check["stdout"])
    roots = _npm_roots(raw)
    packages = json.loads(lock_source)["packages"]
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


def npm_upstream_owners(lock_source: bytes, subjects: Iterable[AuditSubject]) -> set[str]:
    """Name the locked artifacts whose latest stable release decides selected findings."""
    owners = npm_owners(subjects, lock_source).values()
    return {name for artifacts in owners for name, _version in artifacts}


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


def _npm_advisory_request_failed(output: str) -> bool:
    """Recognize npm's audit error object for a bulk advisory request that never answered."""
    try:
        raw = json.loads(output)
    except ValueError:
        return False
    message = raw.get("message") if isinstance(raw, dict) else None
    return (
        isinstance(message, str)
        and message.startswith("request to ")
        and "/-/npm/v1/security/advisories/bulk failed" in message
        and isinstance(raw.get("error"), dict)
        and "vulnerabilities" not in raw
        and "metadata" not in raw
    )


def interpret_native_audit(
    ecosystem: str, output: str, exit_code: int
) -> tuple[Verdict, str, dict]:
    try:
        raw = json.loads(output)
        dependencies, findings = (_python_counts if ecosystem == "python" else _npm_counts)(raw)
    except (KeyError, TypeError, ValueError, AttributeError):
        if ecosystem == "npm" and exit_code and _npm_advisory_request_failed(output):
            return "unknown", "advisory_request_failed", {}
        return "unknown", "native_output_invalid", {}
    details = {"dependency_count": dependencies, "finding_count": findings}
    if findings:
        return "block", "vulnerabilities_or_adverse_statuses", details
    if exit_code:
        return "unknown", "native_execution_failed", details
    return "pass", "clean", details


def _native_observation_gaps(payload: dict, lock_source: bytes) -> tuple[str, str]:
    """Validate a completed raw observation before applying any disposition."""
    checks = payload["checks"]
    if (
        payload["state"] != "finished"
        or not isinstance(payload["required_gaps"], (list, tuple))
        or len(checks) != 2
    ):
        return "unknown", "dependency_audit_incomplete"
    if (
        "dependency_audit_inputs_changed" in payload["required_gaps"]
        or hashlib.sha256(lock_source).hexdigest() != payload["inputs"]["package-lock.json"]
    ):
        return "block", "dependency_audit_inputs_changed"
    for ecosystem, check in zip(("python", "npm"), checks, strict=True):
        if check["ecosystem"] != ecosystem or type(check["exit_code"]) is not int:
            return "unknown", "native_execution_failed"
        verdict, reason, _details = interpret_native_audit(
            ecosystem, check["stdout"], check["exit_code"]
        )
        if verdict != check["verdict"] or reason != check["reason"]:
            return "unknown", "native_audit_verdict_mismatch"
    expected_gaps = [
        f"{check['ecosystem']}:{check['reason']}" for check in checks if check["verdict"] != "pass"
    ]
    native_verdict = reduce_verdicts(*(check["verdict"] for check in checks))
    if payload["verdict"] != native_verdict or list(payload["required_gaps"]) != expected_gaps:
        return "unknown", "native_audit_reduction_mismatch"
    return "pass", ""


def evaluate_dependency_acceptance(
    policy: AuditPolicy,
    payload: dict,
    *,
    lock_source: bytes,
    scope: AuditScope,
    host: str,
    now: datetime,
    ci: bool,
) -> dict:
    """Reevaluate captured native evidence; saved decisions never grant permission."""
    decision = {"scope": scope, "verdict": "unknown", "reason": "strict_native_result"}
    if scope == "local-development" and ci:
        return {**decision, "verdict": "block", "reason": "local_development_context_required"}
    try:
        verdict, reason = _native_observation_gaps(payload, lock_source)
        if verdict != "pass":
            return {**decision, "verdict": verdict, "reason": reason}
        decision["verdict"] = payload["verdict"]
        checks = payload["checks"]
        python = python_findings(checks[0])
        if payload["verdict"] == "pass" or python is None:
            return decision
        if checks[1]["verdict"] not in ("pass", "block") or checks[1]["exit_code"] not in (0, 1):
            return {**decision, "verdict": "unknown", "reason": "native_execution_failed"}
        subjects, aggregates = (
            _npm_subjects(lock_source, checks[1]) if checks[1]["verdict"] == "block" else (set(), 0)
        )
        upstream = payload.get("upstream", {}).get("npm", {})
        unfixed = unfixed_npm_subjects(npm_owners(subjects, lock_source), upstream) | python[1]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        return {
            **decision,
            "verdict": "unknown",
            "reason": "finding_identity_unavailable",
            "detail": str(error),
        }
    matching = [
        record
        for record in policy.dispositions
        if record.scope in ("production-release", scope)
        and any(
            record.matches(subject, lock_sha256=payload["inputs"]["package-lock.json"], host=host)
            for subject in subjects
        )
    ]
    active = [record for record in matching if record.expires_at is None or now < record.expires_at]
    covered = {
        subject
        for subject in subjects
        if any(
            record.matches(subject, lock_sha256=payload["inputs"]["package-lock.json"], host=host)
            for record in active
        )
    }
    findings = subjects | python[0]
    reported = (findings - covered) & unfixed
    blocking = findings - covered - reported
    reason = "unfixed_upstream_findings_reported" if reported else "authorized_findings"
    return {
        "scope": scope,
        "verdict": "block" if blocking else "pass",
        "reason": "unapproved_or_expired_findings" if blocking else reason,
        "evaluated_at": now.isoformat(),
        "host": host,
        "advisory_count": len({subject[0] for subject in findings}),
        "covered_package_count": 0 if blocking else aggregates,
        "approvals": [record.model_dump(mode="json") for record in active],
        "expired_approvals": [
            record.approval_ref
            for record in matching
            if record.expires_at is not None and now >= record.expires_at
        ],
        "unapproved_subjects": sorted(blocking),
        "unfixed_upstream_subjects": sorted(reported),
    }


def native_dependency_audit_scope(gate: Mapping[str, object]) -> AuditScope | None:
    """Select only the canonical audit owner and its explicit execution scope."""
    command = gate.get("execution_identity", gate.get("command"))
    if gate.get("tool_adapter") != "vulnerabilities" or not isinstance(command, tuple | list):
        return None
    identity = canonical_gate_command(bind_gate_command(tuple(command), sys.executable))
    native = ("python", "-m", "nox", "-s", "vulnerabilities")
    if identity in (native, (*native, "--", "--scope", "production-release")):
        return "production-release"
    return (
        "local-development" if identity == (*native, "--", "--scope", "local-development") else None
    )
