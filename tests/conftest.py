"""Shared pytest fixtures for the ETHOS test suite.

The autouse process fixture gives the suite a HERMETIC identity: many tests shell out
to `git commit` in throwaway repos, which fails when the runner has no global
user.name/user.email (the case in CI's clean container — the dominant cause of
"passes locally, red in CI"). Binding GIT_AUTHOR_*/GIT_COMMITTER_* per test makes
the suite self-contained instead of depending on the developer's ambient machine
config. System and user Git config are hidden entirely, while
`init.templateDir` points to a repository-owned empty template directory so
temporary test repositories never inherit developer-global hooks such as
pre-commit. Repository-local config remains authoritative so hook tests exercise
the same `core.hooksPath` semantics as production. The fixture also disables
fsmonitor so temporary test repositories never depend on a host-local filesystem
monitor. Native OpenSpec telemetry and update checks are disabled for raw process
probes as well as the public adapter, so background requests cannot delay exit.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import zipfile
from pathlib import Path

import allure
import pytest
from hypothesis.configuration import set_hypothesis_home_dir

import tests.support.runtime_scenarios as runtime_scenarios
import tools.ci.python_test_gate as python_test_gate
from ethos.adapters.repo.runtime.transition import PackageArtifact
from ethos.repository.release.identity import build_identity
from ethos.repository.release.identity import build_identity_bytes
from ethos.repository.release.resources import BUILD_IDENTITY_RESOURCE
from ethos.repository.release.resources import WHEEL_RESOURCE_ROOT

_REPO_ROOT = Path(__file__).resolve().parents[1]
set_hypothesis_home_dir(
    _REPO_ROOT
    / "build/runtime/tool-cache/hypothesis"
    / os.environ.get("PYTEST_XDIST_WORKER", "local")
)


@pytest.fixture
def python_gate_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> PackageArtifact:
    """Supply valid package bytes to scheduling tests without building an entire product."""
    build = build_identity(product="0.2.0-alpha.5", source_commit="a" * 40, source_tree="b" * 40)
    wheel = tmp_path / "ethos-test.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr(
            (WHEEL_RESOURCE_ROOT / BUILD_IDENTITY_RESOURCE).as_posix(),
            build_identity_bytes(build),
        )
    artifact = PackageArtifact(wheel, hashlib.sha256(wheel.read_bytes()).hexdigest(), build)

    def select(_repo: Path, *, head: str) -> PackageArtifact:
        assert head == build.source_commit
        if artifact.path.is_relative_to(_repo):
            return artifact
        selected = _repo / "build/artifacts/python" / wheel.name
        selected.parent.mkdir(parents=True, exist_ok=True)
        selected.write_bytes(wheel.read_bytes())
        return PackageArtifact(selected, artifact.sha256, build)

    monkeypatch.setattr("tools.ci.delivery.artifact.source_build_identity", lambda _: build)
    monkeypatch.setattr(python_test_gate, "selected_wheel", select)
    return artifact


@pytest.fixture(autouse=True)
def _report_case_identity(request: pytest.FixtureRequest) -> None:
    """Keep distinct pytest cases separate when display parameters lose information."""
    if request.config.getoption("--alluredir", default=None):
        allure.dynamic.parameter(
            "pytest_nodeid", request.node.nodeid, mode=allure.parameter_mode.HIDDEN
        )


@pytest.fixture(scope="session", autouse=True)
def _governance_executable_supply(tmp_path_factory: pytest.TempPathFactory):
    """Share only a test-owned read-only POSIX binary, never mutable runtime state."""
    if os.name == "nt":
        yield
        return
    executable = tmp_path_factory.mktemp("governance-python") / "python"
    shutil.copy2(sys.executable, executable)
    executable.chmod(0o555)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(runtime_scenarios, "_GOVERNANCE_PYTHON", executable)
        yield


@pytest.fixture(autouse=True)
def _hermetic_process_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Bind deterministic identity and offline native probes without replacing repo policy."""
    git_template = tmp_path / "empty-git-template"
    git_template.mkdir(parents=True, exist_ok=True)
    for role in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{role}_NAME", "ETHOS Test")
        monkeypatch.setenv(f"GIT_{role}_EMAIL", "test@example.invalid")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    count = int(os.environ.get("GIT_CONFIG_COUNT", "0"))
    entries = [
        (os.environ[f"GIT_CONFIG_KEY_{index}"], os.environ[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    ]
    declared = {key for key, _value in entries}
    entries.extend(
        (key, value)
        for key, value in (
            ("init.templateDir", git_template.as_posix()),
            ("core.fsmonitor", "false"),
        )
        if key not in declared
    )
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(entries)))
    for index, (key, value) in enumerate(entries):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{index}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", value)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    monkeypatch.setenv("OPENSPEC_TELEMETRY", "0")
    monkeypatch.setenv("OPENSPEC_NO_UPDATE_CHECK", "1")
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    # Fixture full proofs keep their per-repository slot but never wait on the test host's load.
    monkeypatch.setenv("ETHOS_PROOF_HOST_LOAD_LIMIT", "0")
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    monkeypatch.delenv("ETHOS_CI_SUPPLY_MANIFEST", raising=False)
