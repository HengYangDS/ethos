"""Test-owned native audit transport, materials and explicit fixture decisions."""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from contextlib import suppress
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.runtime.materialization.input_resolution as input_resolution
from ethos.repository.policy.quality.dependency_acceptance import AUDIT_INPUTS
from tools.ci import dependency_audit as audit

if TYPE_CHECKING:
    from collections.abc import Callable


def clean_report(ecosystem: str) -> dict:
    """Return native-shaped reports, not a shared fake result schema."""
    if ecosystem == "python":
        return {
            "summary": {"audited_packages": 1, "vulnerabilities": 0, "adverse_statuses": 0},
            "vulnerabilities": [],
            "adverse_statuses": [],
        }
    return {
        "auditReportVersion": 2,
        "vulnerabilities": {},
        "metadata": {
            "vulnerabilities": dict.fromkeys(
                ("info", "low", "moderate", "high", "critical", "total"), 0
            ),
            "dependencies": {"total": 1},
        },
    }


def invoke_audit(root: Path, **options) -> dict:
    """Read the actual persisted result even when Nox refuses the observation."""
    with suppress(pytest.fail.Exception):
        audit.run(Mock(error=pytest.fail), root=root, **options)
    return json.loads((root / audit.EVIDENCE / "dependency-audit.json").read_text())


def native_transport(monkeypatch, respond: Callable) -> list[tuple[str, ...]]:
    """Replace only external execution; command selection stays real."""
    observed: list[tuple[str, ...]] = []
    monkeypatch.setattr(audit, "current_tracked_head", lambda _root: "a" * 40)
    monkeypatch.setattr(
        input_resolution,
        "resolve_node_runtime",
        lambda: SimpleNamespace(executable=Path("/fixture/node"), npm=Path("/fixture/npm-cli.js")),
        raising=False,
    )

    def execute(root: Path, command: tuple[str, ...], **options):
        observed.append(command)
        assert options["timeout"] == 120
        assert options["remove_env_prefixes"] == ("GIT_",)
        ecosystem = "npm" if any("npm-cli.js" in part for part in command) else "python"
        return respond(root, command, ecosystem)

    monkeypatch.setattr(audit, "run_command", execute)
    return observed


def native_result(command, ecosystem):
    return subprocess.CompletedProcess(command, 0, json.dumps(clean_report(ecosystem)), "")


def npm_transport(monkeypatch, output: str, stderr: str = "") -> None:
    """Reuse adverse npm execution without changing raw evidence or diagnostics."""
    native_transport(
        monkeypatch,
        lambda _root, cmd, ecosystem: (
            subprocess.CompletedProcess(cmd, 1, output, stderr)
            if ecosystem == "npm"
            else native_result(cmd, ecosystem)
        ),
    )


def npm_advisories(root: Path) -> dict:
    """Retain the observed one-advisory, six-package npm aggregate journey."""
    relations = {
        "braces": [],
        "micromatch": ["braces"],
        "fast-glob": ["micromatch"],
        "globby": ["fast-glob", "micromatch"],
        "@fission-ai/openspec": ["fast-glob"],
        "markdownlint-cli2": ["globby", "micromatch"],
    }
    raw = clean_report("npm")
    packages = {"": {}}
    for name, via in relations.items():
        node = "node_modules/" + name
        raw["vulnerabilities"][name] = {
            "name": name,
            "via": via,
            "nodes": [node],
            "severity": "high",
        }
        packages[node] = {"version": "1.0.0", "integrity": "sha512-Zml4dHVyZQ=="}
    packages["node_modules/braces"] = {
        "version": "3.0.3",
        "integrity": "sha512-yQbXgO/OSZVD2IsiLlro+7Hf6Q18EJrKSEsdoMzKePKXct3gvD8oLcOQdIzGupr5Fj"
        "+EDe8gO/lxc1BzfMpxvA==",
    }
    raw["vulnerabilities"]["braces"]["via"] = [
        {
            "source": 1240992,
            "name": "braces",
            "dependency": "braces",
            "url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
            "range": "<=3.0.3",
        }
    ]
    raw["metadata"]["vulnerabilities"].update(high=6, total=6)
    raw["metadata"]["dependencies"]["total"] = 407
    (root / "package-lock.json").write_text(json.dumps({"packages": packages}) + "\n")
    return raw


def authorize_fixture(root: Path, **changes) -> None:
    """Create an explicitly test-only approval, never a live policy exception."""
    locked = json.loads((root / "package-lock.json").read_text())["packages"]["node_modules/braces"]
    record = {
        "ecosystem": "npm",
        "advisory_url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
        "package": "braces",
        "version": locked["version"],
        "integrity": locked["integrity"],
        "nodes": ["node_modules/braces"],
        "lock_sha256": hashlib.sha256((root / "package-lock.json").read_bytes()).hexdigest(),
        "scope": "local-development",
        "host": platform.node(),
        "owner": "fixture:owner",
        "approval_ref": "fixture:human-approved-risk",
        "rationale": "Test-only bounded local iteration; no production or release permission.",
        "expires_at": datetime(2050, 1, 1, tzinfo=UTC),
    }
    record.update(changes)
    rendered = ["\n[[dispositions]]"]
    for key, value in record.items():
        if value is None:
            continue
        text = value.isoformat() if isinstance(value, datetime) else json.dumps(value)
        rendered.append(f"{key} = {text}")
    policy = root / audit.POLICY
    policy.write_text(policy.read_text().replace("dispositions = []\n", "") + "\n".join(rendered))


def captured_audit_payload(**changes) -> tuple[str, dict[str, bytes]]:
    sources = {name: f"captured {name}\n".encode() for name in AUDIT_INPUTS}
    payload = {
        "command": "dependency-audit",
        "head": "a" * 40,
        "inputs": {name: hashlib.sha256(value).hexdigest() for name, value in sources.items()},
    }
    payload.update(changes)
    return json.dumps(payload), sources


def native_audit_observation(fault: str) -> tuple[dict, bytes]:
    lock = b'{"packages": {"": {}}}\n'
    checks = [
        {
            "ecosystem": ecosystem,
            "exit_code": 0,
            "stdout": json.dumps(clean_report(ecosystem)),
            "verdict": "pass",
            "reason": "clean",
        }
        for ecosystem in ("python", "npm")
    ]
    payload = {
        "state": "finished",
        "required_gaps": [],
        "checks": checks,
        "verdict": "pass",
        "inputs": {"package-lock.json": hashlib.sha256(lock).hexdigest()},
    }
    if fault == "incomplete":
        payload["state"] = "running"
    elif fault == "verdict":
        checks[0]["verdict"] = "block"
    elif fault == "reduction":
        payload["verdict"] = "block"
    else:
        checks[1].update(exit_code=1, verdict="unknown", reason="native_execution_failed")
        payload.update(verdict="unknown", required_gaps=["npm:native_execution_failed"])
    return payload, lock
