"""Dependency declaration evidence for the sole Python distribution."""

from __future__ import annotations

import json
import re
import subprocess
import tomllib
from datetime import UTC
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import TypeAdapter

from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import current_tracked_head
from ethos.contracts.verdict import execution_succeeded
from tools.ci.toolchain.environment import ProjectRuntime

if TYPE_CHECKING:
    import nox

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/evidence/quality/dependency/deptry-ethos.json"
SUMMARY = ROOT / "build/evidence/quality/dependency/summary.json"
PROJECT = ROOT / "pyproject.toml"
RUNTIME = ProjectRuntime.discover(ROOT)
LOWER_BOUND = re.compile(r"^(?P<name>[A-Za-z0-9_.-]+)>=(?P<version>[^,;\s]+)$")


def _declared_requirements() -> list[str]:
    project = tomllib.loads(PROJECT.read_text(encoding="utf-8"))
    runtime = project.get("project", {}).get("dependencies", [])
    groups = project.get("dependency-groups", {})
    development = [item for values in groups.values() for item in values]
    build = project.get("build-system", {}).get("requires", [])
    return list(dict.fromkeys(str(item) for item in (*runtime, *development, *build)))


def _locked_versions() -> dict[str, str]:
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    return {
        str(package["name"]).lower().replace("_", "-"): str(package["version"])
        for package in lock.get("package", [])
        if isinstance(package, dict) and "name" in package and "version" in package
    }


def declaration_gaps() -> list[str]:
    gaps = []
    locked = _locked_versions()
    for requirement in _declared_requirements():
        match = LOWER_BOUND.fullmatch(requirement)
        if match is None:
            gaps.append(f"direct_dependency_not_single_lower_bound:{requirement}")
            continue
        name = match.group("name").lower().replace("_", "-")
        version = match.group("version")
        if locked.get(name) != version:
            gaps.append(f"direct_dependency_lock_mismatch:{name}:{version}:{locked.get(name, '')}")
    return gaps


PolicyText = Annotated[str, Field(pattern=r"^\S(?:.*\S)?$")]
PolicyItem = Annotated[str, Field(pattern=r"^[^\s,]+$")]


class DependencyPackagePolicy(BaseModel):
    """The existing package table, validated without a second hand-written schema."""

    model_config = ConfigDict(strict=True, extra="forbid")
    id: PolicyText
    root: PolicyText
    config: PolicyText
    known_first_party: list[PolicyItem]
    package_module_name_map: list[PolicyItem]
    per_rule_ignores: list[PolicyItem]


class DependencyPolicy(BaseModel):
    """One policy declaration; its metadata does not create another executor."""

    model_config = ConfigDict(strict=True, extra="forbid")
    owner: PolicyText
    summary: PolicyText
    runner: PolicyText
    package: list[DependencyPackagePolicy] = Field(min_length=1, max_length=1)


def _policy_arguments() -> tuple[str, ...]:
    """Project validated configuration to Deptry's native argument protocol."""
    policy = DependencyPolicy.model_validate(
        tomllib.loads((ROOT / ".config/checks/deptry/policy.toml").read_text())
    )
    package = policy.package[0]
    for value in (package.root, package.config):
        if (
            Path(value).is_absolute()
            or value.startswith("-")
            or not (ROOT / value).resolve().is_relative_to(ROOT.resolve())
        ):
            message = "dependency_hygiene_policy_path_invalid"
            raise ValueError(message)
    arguments = [package.root, "--config", package.config]
    arguments.extend(
        part for name in package.known_first_party for part in ("--known-first-party", name)
    )
    for field in ("package_module_name_map", "per_rule_ignores"):
        if values := getattr(package, field):
            arguments.extend(("--" + field.replace("_", "-"), ",".join(values)))
    return tuple(arguments)


def run(session: nox.Session) -> None:
    """Run deptry and write one bounded verdict over its JSON result."""
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.unlink(missing_ok=True)
    SUMMARY.unlink(missing_ok=True)
    arguments = _policy_arguments()
    command = (RUNTIME.script("deptry"), *arguments, "--json-output", str(OUTPUT), "--no-ansi")
    execution, verdict, state, gaps = _observe(command)
    if declarations := declaration_gaps():
        verdict, state = "block", "declaration_invalid"
        gaps.extend(declarations)
    payload = {
        "schema_version": 1,
        "kind": "ethos_dependency_hygiene",
        "verdict": verdict,
        "state": state,
        "head": current_tracked_head(ROOT),
        "config": ".config/checks/deptry/policy.toml",
        "generated_at": datetime.now(UTC).isoformat(),
        "tool": "deptry",
        "command": command,
        "cwd": str(ROOT),
        **execution,
        "evidence_class": "local_owner_gate",
        "required_gaps": gaps,
        "not_claimed": ["vulnerability scan", "hosted CI passed"],
        "outputs": [OUTPUT.relative_to(ROOT).as_posix()],
    }
    SUMMARY.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    session.log(json.dumps(payload, indent=2, sort_keys=True))
    if not execution_succeeded(payload):
        session.error(f"dependency hygiene did not pass; see {SUMMARY}")


def _observe(command: tuple[str, ...]) -> tuple[dict, str, str, list[str]]:
    """Retain native execution and report failures without claiming a successful run."""
    try:
        result = run_command(ROOT, command, timeout=120)
    except (OSError, ProcessExecutionError, subprocess.TimeoutExpired) as error:
        streams = {
            key: value.decode(errors="replace") if isinstance(value, bytes) else value or ""
            for key, value in {
                "stdout": getattr(error, "output", None),
                "stderr": getattr(error, "stderr", None) or str(error),
            }.items()
        }
        return (
            {
                "exit_code": None,
                **streams,
                "failure": error.evidence()
                if isinstance(error, ProcessExecutionError)
                else {"kind": type(error).__name__, "cause": str(error)},
            },
            "unknown",
            "execution_unavailable",
            ["dependency_hygiene_execution_unavailable"],
        )
    execution = {"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}
    try:
        findings = TypeAdapter(list[dict[str, object]]).validate_json(
            OUTPUT.read_bytes(), strict=True
        )
    except (OSError, ValueError):
        verdict, state, gaps = (
            "unknown",
            "unobservable",
            ["dependency_hygiene_output_unparseable"],
        )
    else:
        verdict, state, gaps = (
            ("block", "findings_reported", ["dependency_hygiene_findings_reported"])
            if findings
            else ("pass", "passed", [])
        )
    if result.returncode and not (result.returncode == 1 and state == "findings_reported"):
        verdict, state = "block", "execution_failed"
        gaps.append("dependency_hygiene_execution_failed")
    return execution, verdict, state, gaps
