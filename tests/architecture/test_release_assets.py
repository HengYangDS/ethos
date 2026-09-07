from __future__ import annotations

import ast
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

import tools.ci.local_ci as local_ci
import tools.ci.python_test_gate as python_test_gate
import tools.ci.sessions as ci_sessions
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
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


def _write_empty_node_package_supply(root: Path) -> Path:
    supply = root / "node_modules"
    supply.mkdir(parents=True)
    (root / "package-lock.json").write_text(
        '{"lockfileVersion":3,"packages":{"":{}}}\n',
        encoding="utf-8",
    )
    (supply / ".package-lock.json").write_text(
        '{"lockfileVersion":3,"packages":{}}\n',
        encoding="utf-8",
    )
    return supply


def test_downloaded_tool_installers_bind_one_native_supply_policy() -> None:
    retired = ("system/tools.toml", "src/ethos/quality")
    assert all(not (ROOT / path).exists() for path in retired)
    installers = sorted((ROOT / "tools/ci/scripts").glob("install-*.sh"))
    installers.append(ROOT / "tools/ci/scripts/run-actionlint.sh")
    declared_policies = set()
    for installer_path in installers:
        installer = installer_path.read_text(encoding="utf-8")
        policy_paths = set(re.findall(r"\.config/[A-Za-z0-9_./-]+\.toml", installer))
        assert len(policy_paths) == 1
        policy_path = policy_paths.pop()
        declared_policies.add(policy_path)
        policy = tomllib.loads((ROOT / policy_path).read_text(encoding="utf-8"))
        digests = [
            value for value in _nested_values(policy) if re.fullmatch(r"[a-f0-9]{64}", value)
        ]
        assert digests
        assert all(re.fullmatch(r"[a-f0-9]{64}", digest) for digest in digests)
        versions = [
            value for value in _nested_values(policy) if re.fullmatch(r"\d+\.\d+\.\d+", value)
        ]
        assert versions
        assert all(version not in installer for version in versions)

    assert declared_policies == {
        ".config/checks/github/actionlint.toml",
        ".config/checks/lychee/supply.toml",
        ".config/checks/node/runtime.toml",
        ".config/checks/secrets/supply.toml",
        ".config/release/supply-chain.toml",
    }


def test_python_bootstrap_derives_uv_version_from_project_owner() -> None:
    script = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    assert 'required_uv="0.' not in script
    assert "pyproject.toml" in script


def test_python_bootstrap_supplies_the_declared_linux_signing_tool() -> None:
    script = (ROOT / "tools/ci/scripts/bootstrap-python.sh").read_text(encoding="utf-8")
    assert "command -v ssh-keygen" in script
    assert "missing_packages+=(openssh-client)" in script


@pytest.mark.parametrize(
    ("system", "image_state", "expected_apt", "install_state"),
    [
        (
            "Linux",
            "available",
            ["update", "install -y --no-install-recommends procps util-linux"],
            "not-required",
        ),
        ("Darwin", "missing", None, "required"),
        ("Darwin", "available", None, "not-required"),
    ],
)
def test_python_bootstrap_supplies_platform_prerequisites(
    tmp_path: Path,
    system: str,
    image_state: str,
    expected_apt: list[str] | None,
    install_state: str,
) -> None:
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
    uv_log = tmp_path / "uv.log"
    native_image = tmp_path / "native-image"
    commands = {
        "git": (
            f"#!/bin/sh\n[ \"$1 $2\" = 'rev-parse --show-toplevel' ] && printf '%s\\n' '{repo}'\n"
        ),
        "uname": f"#!/bin/sh\nprintf '{system}\\n'\n",
        "uv": (
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$*\" >>'{uv_log}'\n"
            "if [ \"$1\" = --version ]; then printf 'uv 0.12.10\\n'; exit 0; fi\n"
            "if [ \"$1\" = run ]; then cat >/dev/null; printf '0.12.10\\n'; exit 0; fi\n"
            "if [ \"$1 $2 $3 $4\" = 'python install --no-bin 3.14.7' ]; then "
            f": >'{native_image}'; exit 0; fi\n"
            '[ "$1" = sync ] && exit 0\n'
            "exit 2\n"
        ),
        "npx": "#!/bin/sh\nexit 0\n",
        "apt-get": f"#!/bin/sh\nprintf '%s\\n' \"$*\" >>'{apt_log}'\n",
    }
    if system == "Linux":
        commands |= {
            "ssh-keygen": "#!/bin/sh\nexit 0\n",
            "ldconfig": "#!/bin/sh\nprintf 'libatomic.so.1\\n'\n",
        }
    for name, body in commands.items():
        _write_fake_executable(fake_bin / name, body)
    for name in ("awk", "cat", "dirname", "grep"):
        (fake_bin / name).symlink_to(shutil.which(name))
    openspec = repo / "node_modules/.bin/openspec"
    openspec.parent.mkdir(parents=True)
    _write_fake_executable(openspec, "#!/bin/sh\nprintf '1.12.0\\n'")
    (repo / ".venv/bin").mkdir(parents=True)
    _write_fake_executable(
        repo / ".venv/bin/python",
        "#!/bin/sh\n"
        'case "$*" in\n'
        "  *platform.python_version*) printf '3.14.7\\n'; exit 0 ;;\n"
        "  '-B -I -') cat >/dev/null\n"
        f"    [ '{image_state}' = available ] || [ -f '{native_image}' ]\n"
        "    exit $? ;;\n"
        "esac\n"
        "exit 2\n",
    )
    (repo / "pyproject.toml").write_text(
        '[dependency-groups]\ndev = ["uv>=0.12.10"]\n', encoding="utf-8"
    )

    result = subprocess.run(
        ("/bin/bash", str(script_dir / "bootstrap-python.sh")),
        cwd=repo,
        env=os.environ | {"PATH": str(fake_bin)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    observed_apt = apt_log.read_text(encoding="utf-8").splitlines() if apt_log.exists() else None
    assert observed_apt == expected_apt
    observed_uv = uv_log.read_text(encoding="utf-8").splitlines()
    if install_state == "required":
        assert observed_uv.index("sync --locked --group dev") < observed_uv.index(
            "python install --no-bin 3.14.7"
        )
        assert native_image.is_file()
    else:
        assert not any(command.startswith("python install ") for command in observed_uv)


def test_direct_python_bounds_equal_the_locked_resolution() -> None:
    assert declaration_gaps() == []


def test_local_ci_logs_use_declared_disposable_runtime_home() -> None:
    declaration = load_generated_artifact_topology_declaration(
        ROOT / "system/policies/generated-artifact-topology.toml"
    )
    relative = local_ci.LOG_ROOT.relative_to(ROOT).as_posix()

    assert relative == "build/runtime/work/local-ci/logs"
    assert path_policy_from_declaration(relative, declaration)["decision"] == "allow"


def test_direct_node_declarations_equal_the_lock_root() -> None:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    locked = json.loads((ROOT / "package-lock.json").read_text(encoding="utf-8"))["packages"][""]
    for group in ("dependencies", "devDependencies"):
        assert package.get(group, {}) == locked.get(group, {})


def test_node_package_supply_environment_has_one_python_owner() -> None:
    def reads_supply_environment(path: Path) -> bool:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and node.args:
                key = node.args[0]
                function = node.func
                if (
                    isinstance(key, ast.Constant)
                    and key.value == "ETHOS_NODE_PACKAGE_SUPPLY"
                    and isinstance(function, ast.Attribute)
                    and (
                        (
                            function.attr == "getenv"
                            and isinstance(function.value, ast.Name)
                            and function.value.id == "os"
                        )
                        or (
                            function.attr == "get"
                            and isinstance(function.value, ast.Attribute)
                            and function.value.attr == "environ"
                            and isinstance(function.value.value, ast.Name)
                            and function.value.value.id == "os"
                        )
                    )
                ):
                    return True
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.ctx, ast.Load)
                and isinstance(node.value, ast.Attribute)
                and node.value.attr == "environ"
                and isinstance(node.value.value, ast.Name)
                and node.value.value.id == "os"
                and isinstance(node.slice, ast.Constant)
                and node.slice.value == "ETHOS_NODE_PACKAGE_SUPPLY"
            ):
                return True
        return False

    readers = {
        path.relative_to(ROOT).as_posix()
        for parent in (ROOT / "src", ROOT / "tools", ROOT / "tests")
        for path in parent.rglob("*.py")
        if reads_supply_environment(path)
    }

    assert readers == {"src/ethos/adapters/repo/runtime/materialization/node_package_supply.py"}


def test_python_test_sessions_receive_the_frozen_node_package_supply(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    supply = tmp_path / "node_modules"
    session = cast("nox.Session", object())
    observed: list[tuple[str, object]] = []

    class Gate:
        @classmethod
        def from_environment(cls, *, node_package_supply: Path):
            observed.append(("supply", node_package_supply))
            return cls()

        @staticmethod
        def run_tests(actual_session: object) -> None:
            observed.append(("tests", actual_session))

        @staticmethod
        def enforce_floor(actual_session: object) -> None:
            observed.append(("coverage", actual_session))

    monkeypatch.setattr(ci_sessions, "NODE_PACKAGE_SUPPLY", supply)
    monkeypatch.setattr(ci_sessions, "PythonTestGate", Gate)

    ci_sessions.tests(session)
    ci_sessions.coverage_floor(session)

    assert observed == [
        ("supply", supply),
        ("tests", session),
        ("supply", supply),
        ("coverage", session),
    ]


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
        uv_cache=None,
        node_package_supply=tmp_path / "node_modules",
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
    _write_empty_node_package_supply(root)
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(python_test_gate.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(python_test_gate, "_head", lambda: "a" * 40)
    monkeypatch.delenv("ETHOS_TEST_BASETEMP", raising=False)
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    if ownership == "external":
        monkeypatch.setenv("ETHOS_TEST_BASETEMP", str(external))
    gate = python_test_gate.PythonTestGate.from_environment(
        node_package_supply=root / "node_modules"
    )
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


def test_identity_drop_projects_only_repository_safe_directory(tmp_path, monkeypatch) -> None:
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
        uv_cache=None,
        node_package_supply=tmp_path / "node_modules",
        identity=(65534, 65534),
    )
    monkeypatch.setattr(python_test_gate, "ROOT", root)

    gate = python_test_gate.PythonTestGate(settings)
    environment = vars(python_test_gate.PythonTestGate)["_env"](gate)
    count = int(environment["GIT_CONFIG_COUNT"])
    overlay = tuple(
        (environment[f"GIT_CONFIG_KEY_{index}"], environment[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    )

    assert ("safe.directory", root.as_posix()) in overlay
    assert not {"user.name", "user.email"} & {key for key, _value in overlay}
    assert all(value for _, value in overlay)
    assert environment["GIT_TERMINAL_PROMPT"] == "0"


def test_identity_boundary_consumes_run_as_controls(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    _write_empty_node_package_supply(root)
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(python_test_gate, "_head", lambda: "a" * 40)
    monkeypatch.setattr(python_test_gate.os, "getuid", lambda: 0)
    monkeypatch.setattr(python_test_gate.shutil, "which", lambda _name: "/usr/bin/setpriv")
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)
    monkeypatch.setenv("ETHOS_TEST_RUN_AS_UID", "65534")
    monkeypatch.setenv("ETHOS_TEST_RUN_AS_GID", "65534")
    gate = python_test_gate.PythonTestGate.from_environment(
        node_package_supply=root / "node_modules"
    )
    for method in ("_prepare", "_cleanup", "_stable_head"):
        monkeypatch.setattr(gate, method, lambda: None)
    observed: dict[str, str | None] = {}

    class Session:
        @staticmethod
        def run(*_command: str, **kwargs: object) -> None:
            observed.update(cast("dict[str, str | None]", kwargs["env"]))

    gate.run_tests(cast("nox.Session", Session()))

    assert observed["ETHOS_TEST_RUN_AS_UID"] is None
    assert observed["ETHOS_TEST_RUN_AS_GID"] is None


def test_test_environment_freezes_locked_supply_as_absolute_paths(tmp_path, monkeypatch) -> None:
    root = tmp_path / "repo"
    supply = _write_empty_node_package_supply(root)
    monkeypatch.setattr(python_test_gate, "ROOT", root)
    monkeypatch.setattr(python_test_gate, "_head", lambda: "a" * 40)
    monkeypatch.setenv("UV_CACHE_DIR", "build/runtime/tool-cache/uv")
    monkeypatch.delenv("ETHOS_NODE_PACKAGE_SUPPLY", raising=False)

    gate = python_test_gate.PythonTestGate.from_environment(node_package_supply=supply)
    monkeypatch.setenv("UV_CACHE_DIR", "another-cache")
    monkeypatch.setenv("ETHOS_NODE_PACKAGE_SUPPLY", str(tmp_path / "other-supply"))
    for method in ("_prepare", "_cleanup", "_stable_head"):
        monkeypatch.setattr(gate, method, lambda: None)
    observed: dict[str, str | None] = {}

    class Session:
        @staticmethod
        def run(*_command: str, **kwargs: object) -> None:
            observed.update(cast("dict[str, str | None]", kwargs["env"]))

    gate.run_tests(cast("nox.Session", Session()))

    assert observed["UV_CACHE_DIR"] == str(root / "build/runtime/tool-cache/uv")
    assert observed["ETHOS_NODE_PACKAGE_SUPPLY"] == str(supply)


def test_config_quality_consumes_source_bound_node_package_supply(tmp_path, monkeypatch) -> None:
    supply = tmp_path / "node_modules"
    supply.mkdir()
    node = tmp_path / "node"
    node.write_text("node\n", encoding="utf-8")
    observed: dict[str, object] = {}

    class ConfigQuality:
        @staticmethod
        def run(paths, *, node, package_supply):
            observed.update(paths=paths, node=node, package_supply=package_supply)
            return ()

    class Session:
        posargs: tuple[str, ...] = ()

        @staticmethod
        def run(*_command: str, **_kwargs: object) -> None:
            return None

        @staticmethod
        def error(message: str) -> None:
            raise AssertionError(message)

    monkeypatch.setattr(ci_sessions, "NODE", node)
    monkeypatch.setattr(ci_sessions, "NODE_PACKAGE_SUPPLY", supply, raising=False)
    monkeypatch.setattr(ci_sessions, "import_module", lambda _name: ConfigQuality)

    ci_sessions.config_quality(cast("nox.Session", Session()))

    assert observed == {"paths": (), "node": node, "package_supply": supply}


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
