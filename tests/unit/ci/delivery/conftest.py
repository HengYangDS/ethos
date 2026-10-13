"""Attempt-owned installed acceptance fixtures shared by the delivery journeys."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

from ethos.repository.release.identity import BuildIdentity
from tests.support.runtime_scenarios import runtime_executable
from tools.ci.delivery.acceptance import effect
from tools.ci.delivery.acceptance import receipt

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def acceptance_case(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Isolate expensive lifecycle effects while retaining the real receipt compiler."""
    artifacts = tmp_path / "artifacts"
    work = tmp_path / "work"
    evidence = tmp_path / "evidence/smoke.json"
    artifacts.mkdir()
    wheel = artifacts / "ethos-0.2.0a3-py3-none-any.whl"
    wheel.write_bytes(b"wheel")
    sealed_runtime = work / "shared-installation" / ("f" * 64) / "python"
    sealed_runtime.mkdir(parents=True)
    sealed_payload = sealed_runtime / "sealed.txt"
    sealed_payload.write_text("immutable runtime\n", encoding="utf-8")
    sealed_payload.chmod(0o444)
    sealed_runtime.chmod(0o555)
    sealed_runtime.parent.chmod(0o555)
    lifecycle = {stage: {"state": "passed"} for stage in receipt.REQUIRED_LIFECYCLE_STAGES}
    build = BuildIdentity("0.2.0-alpha.3", "0.2.0a3.dev0+ga.ta", "a" * 40, "b" * 40)
    lifecycle["successor_activation"]["runtime_digest"] = "f" * 64
    monkeypatch.setattr(effect, "git_common_dir", lambda root: str(root / ".git"))
    runtime_python = runtime_executable(sealed_runtime, "python")
    selected_runtime = Mock(
        return_value=SimpleNamespace(
            root=sealed_runtime.parent, python=runtime_python, digest="f" * 64, build=build
        )
    )
    monkeypatch.setattr(effect, "current_runtime", selected_runtime)
    origin = tmp_path / "installed/ethos/__init__.py"
    guidance = origin.parent / "resources/skills/ethos-repository-work/SKILL.md"
    guidance.parent.mkdir(parents=True)
    guidance.write_bytes(b"Use the selected immutable product.\n")
    origin.write_text("", encoding="utf-8")
    observed: dict[str, object] = {}
    logs: list[str] = []
    cleanup_evidence_states: list[bool] = []
    remove_generated_tree = effect.remove_generated_tree

    source_python = tmp_path / "project-python"
    for name, value in {
        "ROOT": tmp_path,
        "ARTIFACTS": artifacts,
        "WORK": work,
        "EVIDENCE": evidence,
        "RUNTIME": SimpleNamespace(python=source_python, script=lambda _name: "/locked/uv"),
        "current_tracked_head": lambda _root: "a" * 40,
        "wheel_build_identity": lambda _wheel: build,
        "_run": lambda *_command, **_kwargs: "",
        "prepare_locked_requirements": lambda _root, work, _python: (
            work / "locked-requirements.txt"
        ),
        "install_locked_runtime": lambda *args: observed.update(supply=args),
        "observe_runtime_lifecycle": lambda **kwargs: observed.update(kwargs) or lifecycle,
    }.items():
        monkeypatch.setattr(effect, name, value)
    for owner, method, value in (
        (
            effect,
            "package_runtime",
            {"path": "archive", "runtime_digest": "f" * 64},
        ),
        (effect.runtime_acceptance, "prove_shared_supply", {"state": "passed"}),
        (effect.runtime_acceptance, "require_manifest", runtime_python),
        (
            effect.runtime_acceptance,
            "activate_from_runtime",
            {"python": str(runtime_python)},
        ),
        (effect.adopter_fixture, "materialize_adopter", "d" * 40),
        (effect.adopter_fixture, "line_ending_conformance", ["lf", "crlf"]),
        (
            effect.adopter_fixture,
            "prove_formation",
            {"state": "passed", "first_change": "lane_admitted", "agent_handoff": "passed"},
        ),
        (
            effect,
            "observe_installed_package",
            (
                str(origin),
                "ethos 0.2.0-alpha.3",
                {"state": "passed", "native_git_loss": "not_qualified"},
            ),
        ),
        (effect, "observe_independent_command_plane", {"external_governance_available": False}),
        (effect, "_verify_resources", ["ethos/resources/system/gates.toml"]),
    ):
        monkeypatch.setattr(owner, method, Mock(return_value=value))
    monkeypatch.setattr(
        effect.brownfield_acceptance,
        "prove_brownfield",
        Mock(
            return_value={
                "state": "passed",
                "authored_content_preserved": True,
                "planned_files": [".ethos/profile.toml", "openspec/config.yaml"],
            }
        ),
    )

    def remove_owned_work(path: Path) -> None:
        cleanup_evidence_states.append(evidence.exists())
        remove_generated_tree(path)

    monkeypatch.setattr(effect, "remove_generated_tree", remove_owned_work)
    compile_receipt = Mock(wraps=receipt.package_acceptance_evidence)
    monkeypatch.setattr(effect, "package_acceptance_evidence", compile_receipt)
    return SimpleNamespace(
        executable=runtime_executable(sealed_runtime, "ethos"),
        guidance=guidance,
        receipt=compile_receipt,
        wheel=wheel,
        build=build,
        lifecycle=lifecycle,
        observed=observed,
        logs=logs,
        cleanup=cleanup_evidence_states,
        sealed_payload=sealed_payload,
        selected_runtime=selected_runtime,
    )
