"""Audit both native dependency locks without conflating unavailable and clean evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import nodejs_wheel
from filelock import FileLock
from filelock import Timeout
from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_executable
from ethos.contracts.verdict import reduce_verdicts
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

    from ethos.contracts.verdict import Verdict

ROOT = Path(__file__).resolve().parents[2]
POLICY = ".config/checks/security/audit.toml"
EVIDENCE = "build/evidence/quality/security"
INPUTS = ("pyproject.toml", "uv.lock", "package.json", "package-lock.json", POLICY)


class AuditPolicy(BaseModel):
    """Declare native audit execution without accepting silent policy typos."""

    model_config = ConfigDict(extra="forbid", strict=True)
    owner: str
    summary: str
    runner: str
    timeout_seconds: int = Field(gt=0)


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


def _inputs(root: Path) -> tuple[dict[str, str | None], dict[str, list[str]]]:
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
        data = (root / path).read_bytes()
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
    npm = Path(nodejs_wheel.__file__).parent / "lib/node_modules/npm/bin/npm-cli.js"
    if not npm.is_file():
        raise FileNotFoundError(npm)
    return (
        str(resolve_node_executable()),
        str(npm),
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

    except (OSError, RuntimeError, ProcessExecutionError, subprocess.TimeoutExpired) as error:

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


def run(session: nox.Session, *, root: Path = ROOT) -> None:
    """Own one bounded audit attempt; contention never overwrites active evidence."""
    root = root.resolve()
    evidence = root / EVIDENCE
    evidence.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(evidence / ".dependency-audit.lock", timeout=0):
            _run(session, root=root)
    except Timeout:
        session.error("dependency_audit_in_use: " + str(evidence))


def _run(session: nox.Session, *, root: Path = ROOT) -> None:
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
    }
    _write(summary, payload)
    try:
        policy = AuditPolicy.model_validate(
            tomllib.loads((root / POLICY).read_text(encoding="utf-8"))
        )
        timeout = policy.timeout_seconds
        head, before = current_tracked_head(root), _inputs(root)
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
        if head != current_tracked_head(root) or before != _inputs(root):
            verdict = "block"
            gaps.append("dependency_audit_inputs_changed")
        payload.update(verdict=verdict, state="finished", required_gaps=gaps)
    except (OSError, ValueError, KeyError, TypeError) as error:
        payload.update(verdict="unknown", state="unavailable", required_gaps=[str(error)])
    _write(summary, payload)
    session.log(json.dumps(payload, sort_keys=True))
    if payload["verdict"] != "pass":
        session.error("Dependency audit did not pass; inspect " + str(summary))
