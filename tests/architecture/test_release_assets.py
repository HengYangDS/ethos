from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.python_test_gate as python_test_gate
from tools.ci.dependency_hygiene import declaration_gaps

if TYPE_CHECKING:
    import nox

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


def test_python_bootstrap_supplies_the_declared_linux_signing_tool() -> None:
    script = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    assert "command -v ssh-keygen" in script
    assert "missing_packages+=(openssh-client)" in script


def test_python_bootstrap_does_not_use_apt_get_on_darwin(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    script_dir = repo / "tools/ci/scripts"
    script_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "tools/ci/scripts/bootstrap-python.sh", script_dir)
    _write_fake_executable(
        script_dir / "with-python-runtime.sh",
        '#!/bin/sh\n[ "$1" != -- ] || shift\nexec "$@"\n',
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    apt_log = tmp_path / "apt-get.log"
    _write_fake_executable(
        fake_bin / "git",
        f"#!/bin/sh\n[ \"$1 $2\" = 'rev-parse --show-toplevel' ] && printf '%s\\n' '{repo}'\n",
    )
    _write_fake_executable(fake_bin / "uname", "#!/bin/sh\nprintf 'Darwin\\n'\n")
    _write_fake_executable(
        fake_bin / "uv",
        "#!/bin/sh\n"
        "if [ \"$1\" = --version ]; then printf 'uv 0.12.7\\n'; exit 0; fi\n"
        "if [ \"$1\" = run ]; then cat >/dev/null; printf '0.12.7\\n'; exit 0; fi\n"
        '[ "$1" = sync ] && exit 0\n'
        "exit 2\n",
    )
    _write_fake_executable(fake_bin / "npx", "#!/bin/sh\nexit 0\n")
    _write_fake_executable(
        fake_bin / "apt-get",
        f"#!/bin/sh\nprintf '%s\\n' \"$*\" >>'{apt_log}'\nexit 99\n",
    )
    openspec = repo / "node_modules/.bin/openspec"
    openspec.parent.mkdir(parents=True)
    _write_fake_executable(openspec, "#!/bin/sh\nprintf '1.11.0\\n'\n")
    (repo / "pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["uv>=0.12.7"]\n', encoding="utf-8"
    )

    result = subprocess.run(
        ("/bin/bash", str(script_dir / "bootstrap-python.sh")),
        cwd=repo,
        env={**os.environ, "PATH": f"{fake_bin}:/bin:/usr/bin"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not apt_log.exists()


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


def test_coverage_floor_reuses_the_test_run_configuration(tmp_path, monkeypatch) -> None:
    policy = tomllib.loads(python_test_gate.COVERAGE_POLICY.read_text(encoding="utf-8"))
    settings = python_test_gate.Settings(
        head="a" * 40,
        evidence=tmp_path / "evidence",
        basetemp=tmp_path / "pytest",
        basetemp_owned=True,
        workers=None,
        shards=None,
        durations=0,
        timeout=None,
        lock_wait=0,
        identity=None,
    )
    gate = python_test_gate.PythonTestGate(settings)
    gate.coverage.mkdir(parents=True)
    gate.data.touch()
    gate.head_file.write_text(settings.head + "\n", encoding="utf-8")
    monkeypatch.setattr(gate, "_stable_head", lambda: None)
    commands: list[tuple[str, ...]] = []

    class Session:
        @staticmethod
        def run(*command: str, **_kwargs: object) -> None:
            commands.append(command)

    gate.enforce_floor(cast("nox.Session", Session()))

    assert commands == [
        (
            str(python_test_gate.PYTHON),
            "-m",
            "coverage",
            "report",
            f"--rcfile={python_test_gate.COVERAGE_CONFIG}",
            f"--data-file={gate.data}",
            f"--fail-under={policy['current_hard_floor']}",
        )
    ]


def test_python_cleanup_propagates_removal_failure(tmp_path, monkeypatch) -> None:
    target = tmp_path / "evidence"
    target.mkdir()

    def denied(_path: Path) -> None:
        message = "cleanup denied"
        raise OSError(message)

    monkeypatch.setattr(python_test_gate.shutil, "rmtree", denied)
    with pytest.raises(OSError, match="cleanup denied"):
        python_test_gate.remove_generated_path(target)


def test_python_cleanup_removes_owned_readonly_runtime_tree(tmp_path) -> None:
    target = tmp_path / "evidence"
    runtime = target / "repo/.git/ethos/runtime/digest"
    runtime.mkdir(parents=True)
    payload = runtime / "manifest.json"
    payload.write_text("{}\n", encoding="utf-8")
    payload.chmod(0o444)
    runtime.chmod(0o555)

    python_test_gate.remove_generated_path(target)

    assert not target.exists()


@pytest.mark.parametrize(
    ("failure", "ownership"),
    [("", "owned"), ("pytest", "owned"), ("prepare", "owned"), ("", "external")],
)
def test_python_basetemp_ownership(tmp_path, monkeypatch, failure, ownership) -> None:
    root, external = tmp_path / "repo", tmp_path / "external"
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(python_test_gate.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(python_test_gate, "_head", lambda: "a" * 40)
    monkeypatch.delenv("ETHOS_TEST_BASETEMP", raising=False)
    if ownership == "external":
        monkeypatch.setenv("ETHOS_TEST_BASETEMP", str(external))
    gate = python_test_gate.PythonTestGate.from_environment()
    cache = root / "src/ethos/__pycache__"
    cache.mkdir(parents=True)
    monkeypatch.setattr(gate, "_stable_head", lambda: None)

    def fail(*_args: object) -> None:
        gate.s.basetemp.mkdir(parents=True, exist_ok=True)
        message = f"{failure} failed"
        raise RuntimeError(message)

    monkeypatch.setattr(
        gate,
        "_prepare" if failure == "prepare" else "_single",
        fail if failure else lambda *_: None,
    )
    if failure:
        with pytest.raises(RuntimeError, match=failure):
            gate.run_tests(cast("nox.Session", object()))
    else:
        gate.run_tests(cast("nox.Session", object()))

    assert (gate.s.basetemp.exists(), cache.is_dir()) == (ownership == "external", True)


def test_identity_drop_projects_repository_git_identity(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    settings = python_test_gate.Settings(
        head="a" * 40,
        evidence=tmp_path / "evidence",
        basetemp=tmp_path / "pytest",
        basetemp_owned=True,
        workers=None,
        shards=None,
        durations=0,
        timeout=None,
        lock_wait=0,
        identity=(65534, 65534),
    )
    values = {
        "user.name": "ETHOS Hosted Tests",
        "user.email": "hosted-tests@example.invalid",
    }
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(
        python_test_gate,
        "run_git",
        lambda _root, *args, **_kwargs: type(
            "Result", (), {"returncode": 0, "stdout": values[args[-1]] + "\n", "stderr": ""}
        )(),
    )

    gate = python_test_gate.PythonTestGate(settings)
    environment = vars(python_test_gate.PythonTestGate)["_env"](gate)
    count = int(environment["GIT_CONFIG_COUNT"])
    overlay = tuple(
        (environment[f"GIT_CONFIG_KEY_{index}"], environment[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    )

    assert ("safe.directory", root.as_posix()) in overlay
    assert ("user.name", values["user.name"]) in overlay
    assert ("user.email", values["user.email"]) in overlay
    assert all(value for _, value in overlay)
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


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
