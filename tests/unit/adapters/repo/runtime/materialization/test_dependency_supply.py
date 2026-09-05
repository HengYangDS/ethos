"""Lock-current dependency-byte supply contracts for immutable runtimes."""

from __future__ import annotations

import hashlib
import importlib
import subprocess
from pathlib import Path

import pytest


def test_lock_current_environment_supplies_runtime_without_cache_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verified environment bytes are projected, pruned, and wheel-qualified offline."""
    try:
        supply = importlib.import_module(
            "ethos.adapters.repo.runtime.materialization.dependency_supply"
        )
    except ModuleNotFoundError:
        pytest.fail("runtime materialization has no dependency-supply owner")

    project = tmp_path / "project"
    work = tmp_path / "work"
    source_python = project / ".venv/bin/python"
    source_packages = project / ".venv/lib/python3.14/site-packages"
    target_python = tmp_path / "runtime/python/bin/python"
    target_packages = tmp_path / "runtime/python/lib/python3.14/site-packages"
    wheel = tmp_path / "ethos.whl"
    source_python.parent.mkdir(parents=True)
    source_python.write_bytes(b"python")
    target_python.parent.mkdir(parents=True)
    target_python.write_bytes(b"python")
    (source_packages / "annotated_types").mkdir(parents=True)
    (source_packages / "annotated_types/__init__.py").write_text(
        "VERSION = '0.8.0'\n",
        encoding="utf-8",
    )
    wheel.write_bytes(b"wheel")
    commands: list[tuple[tuple[str, ...], Path]] = []

    package_file = source_packages / "annotated_types/__init__.py"
    package_sha256 = hashlib.sha256(package_file.read_bytes()).hexdigest()
    monkeypatch.setattr(
        supply,
        "observe_dependency_supply",
        lambda _python: (
            source_python.parent.parent,
            ((Path("lib/python3.14/site-packages/annotated_types/__init__.py"), package_sha256),),
        ),
    )
    monkeypatch.setattr(
        supply,
        "observe_python_facts",
        lambda python: {
            "python_abi": "cpython-314",
            "python_version": "3.14.7",
            "python_implementation": "cpython",
            "architecture": "arm64",
            "prefix": (
                source_python.parent.parent
                if python == source_python
                else target_python.parent.parent
            ).as_posix(),
        },
    )

    def run(
        _project: Path,
        *command: str,
        python: Path,
    ) -> subprocess.CompletedProcess[str]:
        commands.append((command, python))
        assert "--cache-dir" not in command
        if command[0] == "export":
            output = Path(command[command.index("--output-file") + 1])
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text("annotated-types==0.8.0 --hash=sha256:abc\n", encoding="utf-8")
        if command[:2] == ("pip", "sync"):
            assert (target_packages / "annotated_types/__init__.py").is_file()
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(supply, "run_runtime_tool", run)

    requirements = supply.prepare_locked_requirements(
        project,
        work,
        source_python,
        require_build_tools=True,
    )
    supply.install_locked_runtime(
        project,
        source_python,
        target_python,
        wheel,
        requirements,
    )

    assert requirements == work / "locked-requirements.txt"
    assert [command[:2] for command, _python in commands] == [
        ("sync", "--locked"),
        ("export", "--locked"),
        ("pip", "sync"),
        ("pip", "install"),
    ]
    assert all("--offline" in command for command, _python in commands)
    assert all(python == source_python for _command, python in commands)
    assert "--no-dev" not in commands[0][0]
    assert "--no-dev" in commands[1][0]
    assert (source_packages / "annotated_types/__init__.py").is_file()
    assert (target_packages / "annotated_types/__init__.py").is_file()
    assert "--require-hashes" in commands[2][0]
    assert "--strict" in commands[2][0]
    assert "--no-deps" in commands[3][0]
    assert commands[3][0][-1] == wheel.as_posix()


@pytest.mark.parametrize(
    ("coordinate", "target_value"),
    [
        ("python_abi", "cpython-315"),
        ("python_version", "3.15.0"),
        ("python_implementation", "pypy"),
        ("architecture", "other-architecture"),
    ],
)
def test_dependency_supply_rejects_incongruent_python_before_copy(
    coordinate: str,
    target_value: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Platform-specific dependency bytes cannot cross Python identities."""
    supply = importlib.import_module(
        "ethos.adapters.repo.runtime.materialization.dependency_supply"
    )
    source_prefix = tmp_path / "source"
    target_prefix = tmp_path / "target"
    source_python = source_prefix / "bin/python"
    target_python = target_prefix / "bin/python"
    relative = Path("lib/python3.14/site-packages/package/__init__.py")
    source_file = source_prefix / relative
    target_file = target_prefix / relative
    for python in (source_python, target_python):
        python.parent.mkdir(parents=True)
        python.write_bytes(b"python")
    source_file.parent.mkdir(parents=True)
    source_file.write_bytes(b"dependency")
    identity = {
        "python_abi": "cpython-314",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "architecture": "arm64",
    }
    monkeypatch.setattr(
        supply,
        "observe_dependency_supply",
        lambda _python: (
            source_prefix,
            ((relative, hashlib.sha256(source_file.read_bytes()).hexdigest()),),
        ),
    )
    monkeypatch.setattr(
        supply,
        "observe_python_facts",
        lambda python: {
            **identity,
            "prefix": (source_prefix if python == source_python else target_prefix).as_posix(),
            **({coordinate: target_value} if python == target_python else {}),
        },
    )

    with pytest.raises(ValueError, match="hook_runtime_dependency_supply_incompatible"):
        supply.project_dependency_supply(source_python, target_python)

    assert not target_file.exists()


def test_dependency_supply_validates_the_complete_manifest_before_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later invalid source entry cannot leave an earlier partial projection."""
    supply = importlib.import_module(
        "ethos.adapters.repo.runtime.materialization.dependency_supply"
    )
    source_prefix = tmp_path / "source"
    target_prefix = tmp_path / "target"
    source_python = source_prefix / "bin/python"
    target_python = target_prefix / "bin/python"
    first = Path("lib/python3.14/site-packages/first.py")
    drifted = Path("lib/python3.14/site-packages/drifted.py")
    for python in (source_python, target_python):
        python.parent.mkdir(parents=True)
        python.write_bytes(b"python")
    for relative in (first, drifted):
        source = source_prefix / relative
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(relative.name.encode())
    identity = {
        "python_abi": "cpython-314",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "architecture": "arm64",
    }
    monkeypatch.setattr(
        supply,
        "observe_dependency_supply",
        lambda _python: (
            source_prefix,
            (
                (first, hashlib.sha256((source_prefix / first).read_bytes()).hexdigest()),
                (drifted, "0" * 64),
            ),
        ),
    )
    monkeypatch.setattr(
        supply,
        "observe_python_facts",
        lambda python: {
            **identity,
            "prefix": (source_prefix if python == source_python else target_prefix).as_posix(),
        },
    )

    with pytest.raises(ValueError, match="hook_runtime_dependency_supply_invalid"):
        supply.project_dependency_supply(source_python, target_python)

    assert not (target_prefix / first).exists()
