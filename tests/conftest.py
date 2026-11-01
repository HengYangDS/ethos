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

import os
import shutil
import sys
from pathlib import Path

import allure
import pytest
from hypothesis import settings
from hypothesis.configuration import set_hypothesis_home_dir

import tests.support.runtime_scenarios as runtime_scenarios
import tests.support.tier_guard as tier_guard
from ethos.adapters.repo.runtime.materialization.node_package_supply import (
    resolve_node_package_supply,
)

_REPO_ROOT = Path(__file__).resolve().parents[1]
# What every case and its children inherit, set once before xdist starts its workers: hidden Git
# configuration with one overlay entry, no prompt, bytecode only under a named prefix, absolute tool
# supplies and no inherited actor.
for _name in [
    key for key in os.environ if key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))
]:
    del os.environ[_name]
os.environ.update(
    {
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "core.fsmonitor",
        "GIT_CONFIG_VALUE_0": "false",
        "GIT_TERMINAL_PROMPT": "0",
    }
)
os.environ.pop("ETHOS_ACTOR", None)
if _cache := os.environ.get("UV_CACHE_DIR"):
    os.environ["UV_CACHE_DIR"] = str((_REPO_ROOT / _cache).resolve())
if "ETHOS_NODE_PACKAGE_SUPPLY" not in os.environ:
    os.environ["ETHOS_NODE_PACKAGE_SUPPLY"] = str(resolve_node_package_supply(_REPO_ROOT))
# Under a named prefix, the probe's scratch, every process of the run shares one bytecode cache
# that leaves with it; without one nothing is written beside the sources.
if os.environ.get("PYTHONPYCACHEPREFIX"):
    os.environ.pop("PYTHONDONTWRITEBYTECODE", None)
    sys.dont_write_bytecode = False
else:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    sys.dont_write_bytecode = True
# A proof is reproducible: `--hypothesis-profile` selects another profile explicitly.
settings.register_profile("proof", derandomize=True, deadline=None, database=None)
settings.load_profile("proof")
if "HYPOTHESIS_STORAGE_DIRECTORY" not in os.environ:
    set_hypothesis_home_dir(
        _REPO_ROOT
        / "build/runtime/tool-cache/hypothesis"
        / os.environ.get("PYTEST_XDIST_WORKER", "local")
    )


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Register the report-only tier guard and send Allure results to the attempt's report root.

    The guard's name is the one `-p no:ethos-tier-guard` blocks. allure-pytest reads its directory
    when it configures, so the attempt's root is chosen first and only when none is given.
    """
    config.pluginmanager.register(tier_guard, "ethos-tier-guard")
    if (root := os.environ.get("ETHOS_NATIVE_OUTPUT_DIR")) and not config.option.allure_report_dir:
        config.option.allure_report_dir = str(Path(root) / "allure/results")


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
    # Runtimes that product code pins during a test stay in that test's own host store, while
    # Mise keeps the data directory, and so the installed tool supply, it resolved before.
    if not os.environ.get("MISE_DATA_DIR"):
        shared = os.environ.get("XDG_DATA_HOME") or (
            os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData/Local")
            if os.name == "nt"
            else str(Path.home() / ".local/share")
        )
        monkeypatch.setenv("MISE_DATA_DIR", str(Path(shared) / "mise"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "user-data"))
    # What mise loads or trusts during a test is recorded with that test, not for the host. As on
    # a host that uses mise, the state directory exists before native mise first reads it.
    (tmp_path / "user-state").mkdir(exist_ok=True)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "user-state"))
    # Fixture full proofs keep their per-repository slot but never wait on the test host's load.
    monkeypatch.setenv("ETHOS_PROOF_HOST_LOAD_LIMIT", "0")
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    monkeypatch.delenv("ETHOS_CI_SUPPLY_MANIFEST", raising=False)
    # Commands a case runs cannot write into the attempt's report root.
    monkeypatch.delenv("ETHOS_NATIVE_OUTPUT_DIR", raising=False)
