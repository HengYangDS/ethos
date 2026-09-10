from __future__ import annotations

import ast
import json
import os
import re
import shutil
import stat
import subprocess
import tomllib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import pytest

import tools.ci.local_ci as local_ci
import tools.ci.python_test_gate as python_test_gate
import tools.ci.sessions as ci_sessions
from ethos.adapters.gates.runner import ActionRunResult
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration
from ethos.contracts.gates import GateRegistryDeclaration
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
            ["update", "install -y --no-install-recommends procps lsof util-linux"],
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
        executable = shutil.which(name)
        assert executable is not None, name
        (fake_bin / name).symlink_to(executable)
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


@pytest.mark.parametrize("full", [False, True])
def test_coverage_gate_is_in_the_resolved_proof_closure(*, full: bool) -> None:
    declaration = GateRegistryDeclaration.model_validate(
        tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    )
    selected = declaration.proof_gates(full=full, python_executable=str(python_test_gate.PYTHON))
    identifiers = [gate.id for gate in selected]
    assert identifiers.count("coverage-floor") == 1
    assert identifiers.index("unit-architecture") < identifiers.index("coverage-floor")
    gate = selected[identifiers.index("coverage-floor")]
    assert gate.command == (str(python_test_gate.PYTHON), "-m", "nox", "-s", "coverage_floor")


@pytest.mark.parametrize(("covered", "exit_code"), [(94, 2), (95, 0)])
def test_coverage_floor_rejects_below_required_measurement(
    tmp_path, monkeypatch, covered, exit_code
):
    subject = tmp_path / "subject.py"
    subject.write_text(
        "def uncalled():\n" + "    value = 0\n" * (100 - covered) + "value = 1\n" * (covered - 1),
        encoding="utf-8",
    )
    gate = _test_gate(tmp_path)
    gate.coverage.mkdir(parents=True)
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("COVERAGE")
    }
    subprocess.run(
        [
            str(python_test_gate.PYTHON),
            "-m",
            "coverage",
            "run",
            f"--rcfile={python_test_gate.COVERAGE_CONFIG}",
            f"--data-file={gate.data}",
            f"--source={tmp_path}",
            str(subject),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    subprocess.run(
        [
            str(python_test_gate.PYTHON),
            "-m",
            "coverage",
            "combine",
            f"--rcfile={python_test_gate.COVERAGE_CONFIG}",
            f"--data-file={gate.data}",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=True,
    )
    gate.head_file.write_text(gate.s.head + "\n", encoding="utf-8")
    before = gate.data.read_bytes()
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    observed = []

    class Session:
        @staticmethod
        def run(*command: str, **_kwargs: object) -> None:
            observed.append(
                subprocess.run(
                    command,
                    cwd=tmp_path,
                    env=environment,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            )

    gate.enforce_floor(cast("nox.Session", Session()))

    assert len(observed) == 1
    assert observed[0].returncode == exit_code, observed[0].stdout + observed[0].stderr
    assert "TOTAL" in observed[0].stdout
    assert f"{covered}.00%" in observed[0].stdout
    assert gate.data.read_bytes() == before


def _test_gate(tmp_path: Path):
    return python_test_gate.PythonTestGate(
        python_test_gate.Settings(
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
        )
    )


@pytest.mark.parametrize(
    "case",
    [
        "pass",
        "coverage",
        "dirty",
        "head-missing",
        "policy",
        "empty",
        "missing",
        "duplicate",
        "command",
        "no-exit",
        "bad-exit",
        "overlay",
        "head",
        "policy-drift",
        "crash",
    ],
)
def test_local_ci_requires_complete_exact_source_evidence(tmp_path, monkeypatch, case):
    """A transport cannot mint HEAD success from an overlay or incomplete execution."""
    monkeypatch.setattr(local_ci, "EVIDENCE", tmp_path / "result.json")
    monkeypatch.setattr(local_ci, "LOG_ROOT", tmp_path / "logs")
    monkeypatch.setattr(
        local_ci, "current_tracked_head", lambda _root: "" if case == "head-missing" else "a" * 40
    )
    monkeypatch.setattr(local_ci, "dirty_content_sha256", lambda _root: "before")
    monkeypatch.setattr(
        local_ci,
        "dirty_provenance",
        lambda _root: {"state": "dirty" if case == "dirty" else "clean"},
        raising=False,
    )
    policy = local_ci.resolve_gate_policy(ROOT, full=True)
    if case == "policy":
        policy = replace(policy, gaps=("invalid_policy",))
    monkeypatch.setattr(local_ci, "resolve_gate_policy", lambda *_a, **_k: policy)
    observed = []
    base_run = local_ci.run_gate_waves

    class Runner:
        def run(self, node, _gate, *, root):
            assert root == ROOT
            observed.append(node.id)
            verdict = "block" if case == "coverage" and node.id == "coverage-floor" else "pass"
            return ActionRunResult(node.id, node.command, verdict, int(verdict != "pass"))

    def execute(*args, **kwargs):
        if case == "crash":
            message = "interrupted runner"
            raise RuntimeError(message)
        result = base_run(*args, **kwargs)
        if case in {"overlay", "head", "policy-drift"}:
            name, value = {
                "overlay": ("dirty_content_sha256", "after"),
                "head": ("current_tracked_head", "b" * 40),
                "policy-drift": (
                    "resolve_gate_policy",
                    replace(policy, sources=(("ruff", (("ruff.toml", "changed"),)),)),
                ),
            }[case]
            monkeypatch.setattr(local_ci, name, lambda *_a, **_k: value)
        return (
            ()
            if case == "empty"
            else result[:-1]
            if case == "missing"
            else (
                (*result, result[0])
                if case == "duplicate"
                else (replace(result[0], command=("wrong",)), *result[1:])
                if case == "command"
                else (replace(result[0], exit_code=None if case == "no-exit" else 7), *result[1:])
                if case in {"no-exit", "bad-exit"}
                else result
            )
        )

    monkeypatch.setattr(local_ci, "LocalGateRunner", Runner)
    monkeypatch.setattr(local_ci, "run_gate_waves", execute)
    session = SimpleNamespace(error=pytest.fail, log=lambda _message: None)
    if case == "pass":
        local_ci.run(cast("nox.Session", session))
        assert observed.index("coverage-floor") < observed.index("build")
    else:
        with pytest.raises((pytest.fail.Exception, RuntimeError)):
            local_ci.run(cast("nox.Session", session))
    payload = json.loads(local_ci.EVIDENCE.read_text())
    assert payload["verdict"] == ("pass" if case == "pass" else "block")
    if case in {"dirty", "head-missing", "policy", "crash"}:
        assert not observed
    else:
        assert observed.count("unit-architecture") == observed.count("coverage-floor") == 1
    if case == "coverage":
        assert not {"build", "local-install-smoke"}.intersection(observed)
    assert len(observed) == len(set(observed))


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


@pytest.mark.parametrize("arguments", [("--",), ("--", "true"), ("--invalid",)])
def test_container_bootstrap_refuses_non_entrypoint_invocation(tmp_path, arguments) -> None:
    before = tuple(tmp_path.iterdir())
    result = subprocess.run(
        ("/bin/bash", str(ROOT / "tools/ci/scripts/bootstrap-python.sh"), *arguments),
        cwd=tmp_path,
        env=os.environ | {"CI_PROJECT_DIR": str(tmp_path)},
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 2
    assert "container_job_entrypoint_required" in result.stderr
    assert tuple(tmp_path.iterdir()) == before


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
