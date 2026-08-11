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

ROOT = Path(__file__).resolve().parents[2]
CLAIMS = tomllib.loads(
    (Path(__file__).with_name("release_asset_claims.toml")).read_text(encoding="utf-8")
)


@pytest.mark.parametrize("row", CLAIMS["path"], ids=lambda row: row["claim"])
def test_release_asset_paths(row: dict) -> None:
    missing = [path for path in row["paths"] if not (ROOT / path).is_file()]
    assert not missing, row["claim"]


@pytest.mark.parametrize("row", CLAIMS["text"], ids=lambda row: row["claim"])
def test_release_asset_text_claims(row: dict) -> None:
    text = (ROOT / row["owner"]).read_text(encoding="utf-8")
    missing = [token for token in row["required"] if token not in text]
    forbidden = [token for token in row["forbidden"] if token in text]
    assert not missing, row["claim"]
    assert not forbidden, row["claim"]


@pytest.mark.parametrize("row", CLAIMS["state"], ids=lambda row: row["claim"])
def test_release_asset_state_claims(row: dict) -> None:
    actual = tomllib.loads((ROOT / row["owner"]).read_text(encoding="utf-8"))
    for key in row["keys"]:
        actual = actual[key]
    expected = json.loads(row["expected_json"])
    if row["mode"] == "eq":
        passed = actual == expected
    elif row["mode"] == "keys":
        passed = set(actual) == set(expected)
    elif row["mode"] == "has":
        passed = expected in actual
    else:
        passed = expected not in actual
    assert passed, row["claim"]


def test_node_policy_checksum_and_executable_state() -> None:
    policy = tomllib.loads((ROOT / ".config/checks/node/runtime.toml").read_text(encoding="utf-8"))
    checksums = policy["archive_sha256"]
    assert all(set(values) == {"linux_arm64", "linux_x64"} for values in checksums.values())
    assert all(
        re.fullmatch(r"[a-f0-9]{64}", digest)
        for values in checksums.values()
        for digest in values.values()
    )
    runner = ROOT / "tools/ci/scripts/run-node-compatibility.sh"
    assert runner.stat().st_mode & stat.S_IXUSR
    installer = (ROOT / "tools/ci/scripts/install-node.sh").read_text(encoding="utf-8")
    match = re.search(r'version="\$\{NODE_VERSION:-([^}]+)\}"', installer)
    assert match is not None
    assert match.group(1) == policy["default_version"]


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


def _run_node_compatibility(tmp_path: Path, active_version: str):
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
        "NODE_VERSION": "24.19.0",
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


@pytest.mark.parametrize("active_version", ["24.19.0", "26.7.0"])
def test_node_runtime_compatibility_runner_boundaries(
    tmp_path: Path,
    active_version: str,
) -> None:
    result, npm_log = _run_node_compatibility(tmp_path, active_version)
    if active_version == "24.19.0":
        assert result.returncode == 0, result.stderr
        assert npm_log.read_text(encoding="utf-8").splitlines() == [
            "--version|engine=",
            "ci --ignore-scripts|engine=true",
            "run ethos -- --version|engine=true",
            "run test:npm|engine=true",
        ]
    else:
        assert result.returncode != 0
        assert "Node runtime mismatch: requested 24.19.0, active 26.7.0" in result.stderr
        assert not npm_log.exists()
