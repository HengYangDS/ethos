from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import tomllib
from pathlib import Path

import pytest

import tools.ci.python_test_gate as python_test_gate
from tools.ci.dependency_hygiene import declaration_gaps

ROOT = Path(__file__).resolve().parents[2]
NODE_POLICY = tomllib.loads((ROOT / ".config/checks/node/runtime.toml").read_text(encoding="utf-8"))


def test_node_policy_checksum_and_executable_state() -> None:
    checksums = NODE_POLICY["archive_sha256"]
    assert all(set(values) == {"linux_arm64", "linux_x64"} for values in checksums.values())
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", digest)
        for values in checksums.values()
        for digest in values.values()
    )
    runner = ROOT / "tools/ci/scripts/run-node-compatibility.sh"
    assert runner.stat().st_mode & stat.S_IXUSR
    installer = (ROOT / "tools/ci/scripts/install-node.sh").read_text(encoding="utf-8")
    assert 'version="${NODE_VERSION:-}"' in installer
    assert installer.index('version="${NODE_VERSION:-}"') < installer.index("command -v node")
    assert NODE_POLICY["default_version"] not in installer
    assert ".config/checks/node/runtime.toml" in installer


def _nested_values(value: object) -> list[str]:
    if isinstance(value, dict):
        return [item for child in value.values() for item in _nested_values(child)]
    return [str(value)]


def test_downloaded_tool_installers_are_closed_over_the_tool_catalog() -> None:
    catalog = tomllib.loads((ROOT / "system/tools.toml").read_text(encoding="utf-8"))
    supplied = [entry for entry in catalog["tool"] if "checksums" in entry]
    declared_installers = set()
    for entry in supplied:
        policy_path, _, key_path = entry["checksums"].partition("#")
        policy = tomllib.loads((ROOT / policy_path).read_text(encoding="utf-8"))
        owner: object = policy
        for key in key_path.split("."):
            assert isinstance(owner, dict)
            owner = owner[key]
        digests = _nested_values(owner)
        assert digests
        assert all(re.fullmatch(r"[a-f0-9]{64}", digest) for digest in digests)
        assert len(entry["runtime_inputs"]) == 1
        installer_path = entry["runtime_inputs"][0]
        declared_installers.add(installer_path)
        installer = (ROOT / installer_path).read_text(encoding="utf-8")
        assert policy_path in installer
        versions = [
            value for value in _nested_values(policy) if re.fullmatch(r"\d+\.\d+\.\d+", value)
        ]
        assert versions
        assert all(version not in installer for version in versions)

    discovered_installers = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "tools/ci/scripts").glob("install-*.sh")
    } | {"tools/ci/scripts/run-actionlint.sh"}
    assert declared_installers == discovered_installers


def test_python_bootstrap_derives_uv_version_from_project_owner() -> None:
    script = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    assert 'required_uv="0.' not in script
    assert "pyproject.toml" in script


def test_direct_python_bounds_equal_the_locked_resolution() -> None:
    assert declaration_gaps() == []


def test_direct_node_declarations_equal_the_lock_root() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    locked = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))["packages"][""]
    for group in ("dependencies", "devDependencies"):
        assert package.get(group, {}) == locked.get(group, {})


def test_coverage_gate_state() -> None:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    gates = {gate["id"]: gate for gate in declaration["gates"]}
    assert gates["coverage-floor"]["depends_on"] == ["unit-architecture"]
    assert gates["coverage-floor"]["command"] == [
        "{python}",
        "-m",
        "nox",
        "-s",
        "coverage_floor",
    ]


def test_python_test_evidence_cleanup_propagates_removal_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "evidence"
    target.mkdir()

    def denied(_path: Path) -> None:
        message = "cleanup denied"
        raise OSError(message)

    monkeypatch.setattr(python_test_gate.shutil, "rmtree", denied)
    with pytest.raises(OSError, match="cleanup denied"):
        python_test_gate.remove_generated_path(target)


def test_python_test_cleanup_preserves_shared_interpreter_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    cache = root / "src/ethos/__pycache__"
    cache.mkdir(parents=True)
    (cache / "module.pyc").write_bytes(b"cache")
    (root / ".coverage").write_text("generated", encoding="utf-8")
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    gate = python_test_gate.PythonTestGate(
        python_test_gate.Settings(
            head="a" * 40,
            evidence=root / "build/evidence/quality/tests",
            basetemp=tmp_path / "pytest",
            workers=1,
            shards=1,
            durations=1,
            timeout=None,
            lock_wait=0,
            identity=None,
        )
    )
    monkeypatch.setattr(python_test_gate.PythonTestGate, "_single", lambda _self, _session: None)
    monkeypatch.setattr(python_test_gate.PythonTestGate, "_stable_head", lambda _self: None)

    gate.run_tests(object())

    assert cache.is_dir()
    assert not (root / ".coverage").exists()


def _write_fake_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_node_compatibility(tmp_path: Path, requested_version: str, active_version: str):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    npm_log = tmp_path / "npm.log"
    _write_fake_executable(
        fake_bin / "node",
        "#!/bin/sh\nprintf 'v%s\\n' \"${FAKE_NODE_VERSION}\"\n",
    )
    _write_fake_executable(
        fake_bin / "npm",
        '#!/bin/sh\nprintf \'%s|engine=%s\\n\' "$*" "${npm_config_engine_strict:-}" '
        '>> "${FAKE_NPM_LOG}"\n',
    )
    env = os.environ | {
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "NODE_VERSION": requested_version,
        "FAKE_NODE_VERSION": active_version,
        "FAKE_NPM_LOG": str(npm_log),
    }
    result = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-node-compatibility.sh"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result, npm_log


@pytest.mark.parametrize("version", NODE_POLICY["compatibility_versions"])
def test_node_runtime_compatibility_accepts_each_declared_version(
    tmp_path: Path,
    version: str,
) -> None:
    result, npm_log = _run_node_compatibility(tmp_path, version, version)
    assert result.returncode == 0, result.stderr
    assert npm_log.read_text(encoding="utf-8").splitlines() == [
        "--version|engine=",
        "ci --ignore-scripts|engine=true",
        "run ethos -- --version|engine=true",
        "run test:npm|engine=true",
    ]


def test_node_runtime_compatibility_rejects_active_version_drift(tmp_path: Path) -> None:
    requested, active = NODE_POLICY["compatibility_versions"][:2]
    result, npm_log = _run_node_compatibility(tmp_path, requested, active)
    assert result.returncode != 0
    assert f"Node runtime mismatch: requested {requested}, active {active}" in result.stderr
    assert not npm_log.exists()
