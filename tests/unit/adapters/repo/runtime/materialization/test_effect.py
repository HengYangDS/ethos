"""Tests for the concrete semantic owner named by this module path."""

from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from contextlib import nullcontext
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.runtime.filesystem as runtime_filesystem
import ethos.adapters.repo.runtime.materialization.effect as materialization
import ethos.adapters.repo.runtime.materialization.python_environment as runtime_python_environment
import tests.support.runtime_scenarios as runtime_scenarios
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.manifest import runtime_environment
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.transition import PackageArtifact
from tests.support.runtime_scenarios import REPOSITORY_ROOT
from tests.support.runtime_scenarios import materialize_runtime_case
from tests.support.runtime_scenarios import runtime_build


def _environment(**changes: str):
    values = {
        "python_abi": "cpython-test",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "dependency_lock_sha256": "d" * 64,
        "platform_name": "test",
        "architecture_name": "test-architecture",
    }
    return runtime_environment(**(values | changes))


def _python_facts(home: Path) -> dict[str, str]:
    return {
        **_environment()._asdict(),
        **dict.fromkeys(("executable", "base_executable"), str((home / "bin/python").resolve())),
        **dict.fromkeys(("prefix", "base_prefix"), str(home)),
    }


def _write(path: Path, payload: bytes = b"payload") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def _generation_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    runtime_root, source = tmp_path / "runtime", tmp_path / "source"
    work, interpreter, wheel = runtime_root / ".work", tmp_path / "python", tmp_path / "ethos.whl"
    source.mkdir()
    _write(interpreter, b"python")
    _write(wheel, b"wheel")
    artifact = PackageArtifact(wheel, "c" * 64, runtime_build("a" * 40, "b" * 40))

    def materialize_python(target: Path, *_args: object, **_kwargs: object) -> None:
        for relative, payload in (("bin/python", b"python"), ("bin/ethos", b"ethos")):
            _write(target / relative, payload)

    observed: list[Path] = []
    inventory = materialization.runtime_file_inventory
    for name, implementation in {
        "materialize_python_image": materialize_python,
        "runtime_file_inventory": lambda root: observed.append(root) or inventory(root),
        "observe_python_facts": lambda python: dict.fromkeys(
            ("prefix", "base_prefix"), python.parent.parent.resolve().as_posix()
        ),
    }.items():
        monkeypatch.setattr(materialization, name, implementation)

    command = Mock(return_value=subprocess.CompletedProcess([], 0, "0.2.0-alpha.5\n", ""))
    monkeypatch.setattr(materialization.subprocess, "run", command)
    return (runtime_root, work, source, interpreter, artifact, _environment()), observed, command


@pytest.mark.parametrize("supply", ["packaged", "split-image", "source", "selected"])
def test_materialization_binds_package_dependency_and_image_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, supply: str
) -> None:
    """Package, source, and selected-runtime supply preserve their own coordinates."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(("git", "init", "--quiet", "--initial-branch=dev"), cwd=repo, check=True)
    source_file = materialization.__file__
    package = Path(source_file).resolve().parents[6]
    project = tmp_path / "runtime-project"
    invoked = _write(tmp_path / "managed-python/bin/python", b"python")
    dependency = project / ".venv/bin/python" if supply == "source" else invoked
    image = (
        tmp_path / "native-python" if supply in {"source", "split-image"} else invoked.parent.parent
    )
    facts = _python_facts(image)
    interpreter = Path(facts["executable"])
    wheel = _write(tmp_path / "ethos.whl", b"wheel")
    requirements = _write(tmp_path / "requirements.txt", b"package==1\n")
    artifact = PackageArtifact(wheel, "c" * 64, runtime_build("a" * 40, "b" * 40))
    environment = _environment()
    observed: dict[str, object] = {}

    def record(key: str, value: object, result: object) -> object:
        observed[key] = value
        return result

    def generation(_root, _work, source, python, package_artifact, actual_environment, **kwargs):
        return record(
            "generation",
            (source, python, package_artifact, actual_environment, kwargs),
            tmp_path / "runtime-generation",
        )

    patches = {
        "resolve_runtime_project": lambda _root: project,
        "resolve_locked_environment_python": lambda _root: dependency,
        "_reusable_runtime": lambda *_args: None,
        "is_selected_runtime_source": lambda _source: supply == "selected",
        "require_python_image_source": lambda python: record("image_source", python, facts),
        "observe_runtime_environment": lambda source, python, **kwargs: record(
            "environment", (source, python, kwargs["python_facts"]), environment
        ),
        "prepare_locked_requirements": lambda source, _work, python, **kwargs: record(
            "prepared", (source, python, kwargs["require_build_tools"]), requirements
        ),
        "resolve_runtime_wheel": lambda source, _work, *, python: record(
            "wheel", (source, python), wheel
        ),
        "materialize_package_wheel": lambda *_args, **_kwargs: artifact,
        "materialize_runtime_generation": generation,
    }
    for name, value in patches.items():
        monkeypatch.setattr(materialization, name, value)

    assert materialization.__file__ == source_file
    result = materialization.materialize_runtime(
        repo,
        invoked,
        expected_build=artifact.build,
        build_source=project if supply == "source" else None,
    )

    expected = {
        "image_source": dependency,
        "environment": (project, interpreter, facts),
        "wheel": (project if supply == "source" else package, dependency),
        "generation": (
            project,
            interpreter,
            artifact,
            environment,
            {
                "dependency_python": None if supply == "selected" else dependency,
                "python_facts": facts,
                "locked_requirements": None if supply == "selected" else requirements,
            },
        ),
    }
    if supply != "selected":
        expected["prepared"] = (project, dependency, supply == "source")
    assert observed == expected
    assert result == tmp_path / "runtime-generation/python"


def test_runtime_generation_hashes_only_prepared_and_exposed_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, observed, commands = _generation_case(tmp_path, monkeypatch)
    runtime_root, environment = args[0], args[5]
    target = materialization.materialize_runtime_generation(*args, locked_requirements=None)

    commands.assert_called_once()
    command = commands.call_args.args[0]
    assert command[0] == materialization.runtime_python(command[0].parent.parent)
    assert command[1:] == ("-B", "-I", "-m", "ethos.cli", "--version")
    assert len(observed) == 2
    assert observed[0].name.startswith(".runtime-build-")
    assert observed[1] == target
    for path in (target, *target.rglob("*")):
        assert path.is_symlink() or stat.S_IMODE(path.stat().st_mode) & 0o222 == 0
    assert materialization.materialize_runtime_generation(*args, locked_requirements=None) == target
    is_dir = Path.is_dir
    mode = stat.S_IMODE(runtime_root.stat().st_mode)
    runtime_root.chmod(mode | stat.S_IWUSR)
    with monkeypatch.context() as context:
        seen: set[Path] = set()
        context.setattr(
            Path,
            "is_dir",
            lambda path: is_dir(path) if path != target or path in seen else bool(seen.add(path)),
        )
        context.setattr(
            Path, "rename", lambda _path, _target: (_ for _ in ()).throw(FileExistsError)
        )
        assert (
            materialization.materialize_runtime_generation(*args, locked_requirements=None)
            == target
        )
    runtime_root.chmod(mode)
    for name, value, reason in (
        ("runtime_file_inventory", {}, "hook_runtime_manifest_invalid"),
        (
            "observe_python_facts",
            dict.fromkeys(("prefix", "base_prefix"), "wrong"),
            "hook_runtime_python_not_relocatable",
        ),
    ):
        with monkeypatch.context() as context:
            context.setattr(materialization, name, lambda _path, value=value: value)
            verify = (
                partial(materialization.require_runtime_identity, target, args[4], environment)
                if name == "runtime_file_inventory"
                else partial(materialization.require_runtime_execution, target)
            )
            with pytest.raises(ValueError, match=reason):
                verify()


@pytest.mark.parametrize("failure", [ValueError, subprocess.TimeoutExpired, KeyboardInterrupt])
def test_failed_runtime_verification_removes_only_its_new_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: type[BaseException]
) -> None:
    """Reject failed verification without retaining unverified or deleting accepted bytes."""
    execute = subprocess.run
    args, _observed, _commands = _generation_case(tmp_path, monkeypatch)
    target = materialization.materialize_runtime_generation(*args, locked_requirements=None)

    preserved = materialization.runtime_file_inventory(target)

    def failed_verification(*_args, **_kwargs):
        if failure is ValueError:
            return subprocess.CompletedProcess([], 7, "out", "failed")
        if failure is KeyboardInterrupt:
            raise KeyboardInterrupt
        return execute([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1)

    monkeypatch.setattr(materialization.subprocess, "run", failed_verification)
    pattern = (
        r"hook_runtime_module_smoke_failed:command=.*python -B -I -m ethos\.cli "
        "--version:returncode=7:stdout=out:stderr=failed"
    )
    with pytest.raises(failure, match=pattern if failure is ValueError else None):
        materialization.materialize_runtime_generation(
            *args[:-1], _environment(architecture_name="other"), locked_requirements=None
        )
    assert {path for path in args[0].iterdir() if path.is_dir()} == {target}
    assert materialization.runtime_file_inventory(target) == preserved


def test_runtime_generation_compares_windows_prefixes_as_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    args, _observed, _commands = _generation_case(tmp_path, monkeypatch)
    target = materialization.materialize_runtime_generation(*args, locked_requirements=None)
    prefix = (target / "python").resolve().as_posix()
    windows_spelling = prefix.replace("/", "\\").upper()
    monkeypatch.setattr(
        runtime_python_environment,
        "os",
        SimpleNamespace(name="nt", fspath=os.fspath),
    )
    for spelling in (windows_spelling, r"D:\external"):
        monkeypatch.setattr(
            materialization,
            "observe_python_facts",
            lambda _python, spelling=spelling: dict.fromkeys(("prefix", "base_prefix"), spelling),
        )
        expectation = (
            nullcontext()
            if spelling == windows_spelling
            else pytest.raises(ValueError, match="hook_runtime_python_not_relocatable")
        )
        with expectation:
            materialization.require_runtime_execution(target)


@pytest.mark.parametrize("shape", ["missing", "present", "sealed", "symlink"])
def test_runtime_publication_is_nonexecuting_and_requires_unbound_owned_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    """The signing boundary neither executes code nor changes bound or linked inputs."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = runtime
    python = materialization.runtime_python(runtime / "python")
    if shape != "missing":
        _write(python)
    if shape == "sealed":
        _write(runtime / "manifest.json", b"previous identity")
    staging = runtime
    if shape == "symlink":
        staging = tmp_path / "linked"
        staging.symlink_to(runtime, target_is_directory=True)
    artifact = PackageArtifact(tmp_path / "wheel", "c" * 64, runtime_build("a" * 40, "b" * 40))
    for owner, name in (
        (materialization, "observe_python_facts"),
        (materialization.subprocess, "run"),
    ):
        monkeypatch.setattr(owner, name, Mock(side_effect=AssertionError("candidate executed")))
    reason = "hook_runtime_python_missing" if shape == "missing" else "hook_runtime_staging_invalid"
    expectation = nullcontext() if shape == "present" else pytest.raises(ValueError, match=reason)
    try:
        with expectation:
            target, created = materialization.publish_runtime_generation(
                tmp_path, staging, artifact, _environment()
            )
            assert created is True
        assert (target / "manifest.json").is_file() is (shape in {"present", "sealed"})
        if shape in {"sealed", "symlink"}:
            assert python.read_bytes() == b"payload"
            assert stat.S_IMODE(python.stat().st_mode) == 0o644
    finally:
        if staging.is_symlink():
            staging.unlink()
        for path in {runtime, target}:
            materialization.remove_generated_tree(path, ignore_errors=True)


@pytest.mark.parametrize(
    ("external", "fault"),
    [
        (external, fault)
        for external in (False, True)
        for fault in ("valid", "missing", "content", "encoding", "mode", "lock")
    ]
    + [(True, fault) for fault in ("absent", "wheel")],
)
def test_runtime_reuse_requires_current_supply_and_entry(tmp_path, monkeypatch, fault, *, external):
    """Local repair rebuilds; broken external supply never changes ownership implicitly."""
    create_python = runtime_scenarios.create_fixture_python
    entry_fault = fault

    def with_entry(target, **kwargs):
        create_python(target, **kwargs)
        if entry_fault == "missing":
            (target / "bin/ethos").unlink(missing_ok=True)
            return
        payload = materialization.render_console_script("ethos").encode()
        payload = {"content": b"obsolete", "encoding": b"\xff"}.get(entry_fault, payload)
        _write(target / "bin/ethos", payload).chmod(0o644 if entry_fault == "mode" else 0o755)

    monkeypatch.setattr(runtime_scenarios, "create_fixture_python", with_entry)
    repo, runtime = materialize_runtime_case(tmp_path, monkeypatch)
    common = Path(git_common_dir(repo))
    if external:
        supply = tmp_path / "installed"
        shutil.copytree(common / "ethos", supply)
        runtime = supply / "runtime" / runtime.parent.name / "python"
    selected = activate_runtime(common, runtime.parent)
    original = materialization.runtime_file_inventory(selected.root)
    materialize = partial(
        materialization.materialize_runtime,
        repo,
        Path(sys.executable),
        expected_build=selected.build,
    )
    selector = common / "ethos/runtime/CURRENT"
    before = selector.read_bytes()
    digest = materialization.file_sha256
    if fault == "lock":
        monkeypatch.setattr(
            materialization,
            "file_sha256",
            lambda path: "e" * 64 if path == REPOSITORY_ROOT / "uv.lock" else digest(path),
        )
    elif fault == "absent":
        materialization.remove_generated_tree(selected.root)
    elif fault == "wheel":
        next((selected.root.parent.parent / "packages").rglob("*.whl")).unlink()
    invalid = fault in {"lock", "absent", "wheel"} or (fault != "valid" and os.name != "nt")
    expectation = nullcontext()
    if invalid:
        expectation = (
            pytest.raises(ValueError, match="hook_runtime_installed_supply_unavailable")
            if external
            else pytest.raises(AssertionError, match="rebuild required")
        )
    with monkeypatch.context() as probe:
        probe.setattr(
            materialization,
            "require_python_image_source",
            Mock(side_effect=AssertionError("rebuild required")),
        )
        with expectation:
            assert materialize() == selected.root / "python"
    assert selector.read_bytes() == before
    if invalid and fault != "lock" and not external:
        entry_fault = "valid"
        repaired = materialize(build_source=REPOSITORY_ROOT)
        assert repaired != runtime
        assert repaired.joinpath("bin/ethos").read_text() == materialization.render_console_script(
            "ethos"
        )
        activate_runtime(common, repaired.parent)
        assert materialize() == repaired
    if fault != "absent":
        assert materialization.runtime_file_inventory(selected.root) == original


@pytest.mark.parametrize("operation", ["seal", "remove"])
def test_runtime_mutation_rejects_hardlinks_without_changing_the_external_inode(
    tmp_path: Path,
    operation: str,
) -> None:
    external = tmp_path / "external"
    external.write_text("shared bytes\n", encoding="utf-8")
    external.chmod(0o644)
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    try:
        os.link(external, runtime / "shared")
    except OSError as error:
        pytest.skip(f"hardlinks unavailable: {error}")

    effect = (
        vars(materialization)["_seal_runtime_payload"]
        if operation == "seal"
        else materialization.remove_generated_tree
    )
    with pytest.raises(ValueError, match="hook_runtime_generation_hardlink_invalid"):
        effect(runtime)

    assert stat.S_IMODE(external.stat().st_mode) == 0o644
    assert runtime.is_dir()


def test_generated_tree_cleanup_rejects_a_junction_without_touching_its_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated = tmp_path / "generated"
    junction = generated / "junction"
    junction.mkdir(parents=True)
    sentinel = junction / "sentinel"
    sentinel.write_text("outside authority\n", encoding="utf-8")
    with monkeypatch.context() as context:
        context.setattr(runtime_filesystem, "is_junction", lambda path: path == junction)
        with pytest.raises(ValueError, match="hook_runtime_generation_tree_invalid"):
            materialization.remove_generated_tree(generated)

    assert generated.is_dir()
    assert sentinel.read_text(encoding="utf-8") == "outside authority\n"
    materialization.remove_generated_tree(generated)
    failed = tmp_path / "failed"
    failed.mkdir()
    monkeypatch.setattr(
        materialization.shutil,
        "rmtree",
        lambda _path: (_ for _ in ()).throw(OSError("busy")),
    )
    with pytest.raises(OSError, match="busy"):
        materialization.remove_generated_tree(failed)
    materialization.remove_generated_tree(failed, ignore_errors=True)
