"""Lock-current dependency-byte supply contracts for immutable runtimes."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tomllib
import venv
import zipfile
from pathlib import Path

import pytest
import tomli_w

import ethos.adapters.repo.runtime.materialization.dependency_supply as supply


def _supply_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    source, target = tmp_path / "source", tmp_path / "target"
    entries = (Path("lib/first.py"), Path("lib/second.py"))
    for prefix in (source, target):
        (prefix / "bin").mkdir(parents=True)
        (prefix / "bin/python").write_bytes(b"python")
    files = []
    for relative in entries:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(relative.name.encode())
        files.append((relative, hashlib.sha256(path.read_bytes()).hexdigest()))
    facts = {
        "python_abi": "cpython-314",
        "python_version": "3.14.7",
        "python_implementation": "cpython",
        "architecture": "arm64",
    }
    identities = {
        prefix / "bin/python": facts | {"prefix": prefix.as_posix()} for prefix in (source, target)
    }
    monkeypatch.setattr(
        supply, "observe_dependency_supply", lambda _python, **_kwargs: (source, tuple(files))
    )
    monkeypatch.setattr(supply, "observe_python_facts", identities.__getitem__)
    return source, target, files, identities


@pytest.mark.parametrize("build_tools", [True, False])
def test_lock_current_environment_supplies_native_artifact_installation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, build_tools: bool
) -> None:
    source, target, files, _identities = _supply_case(tmp_path, monkeypatch)
    source_python, target_python = source / "bin/python", target / "bin/python"
    wheel, work = tmp_path / "ethos.whl", tmp_path / "work"
    wheel.write_bytes(b"wheel")
    work.mkdir()
    commands = []

    def run(project, *command, python, use_cache=False):
        assert project == source
        assert python == source_python
        commands.append(command)
        assert "--offline" in command
        assert "--cache-dir" not in command
        if command[0] == "export":
            Path(command[-1]).write_text(
                'lock-version = "1.0"\n[[packages]]\nname = "package"\nversion = "1"\n',
                encoding="utf-8",
            )
        if command[:2] == ("pip", "sync"):
            assert use_cache
            assert not any((target / relative).exists() for relative, _ in files)
        else:
            assert not use_cache
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(supply, "run_runtime_tool", run)
    requirements = supply.prepare_locked_requirements(
        source, work, source_python, require_build_tools=build_tools
    )
    supply.install_locked_runtime(source, source_python, target_python, wheel, requirements)
    assert requirements == work / "pylock.toml"
    assert [command[:2] for command in commands] == [
        ("sync", "--locked"),
        ("export", "--locked"),
        ("pip", "sync"),
        ("pip", "install"),
    ]
    assert ("--no-dev" in commands[0]) is not build_tools
    assert "--no-dev" in commands[1]
    assert {"--require-hashes", "--strict", "--reinstall", "--no-build"} <= set(commands[2])
    assert commands[2][4:6] == ("--preview-features", "pylock")
    assert not any("venv" in command for command in commands)
    assert commands[1][-2:] == ("--output-file", str(requirements))
    assert commands[2][-1] == str(requirements)
    assert "--no-deps" in commands[3]
    assert commands[3][-1] == wheel.as_posix()
    assert all(
        hashlib.sha256((source / path).read_bytes()).hexdigest() == digest for path, digest in files
    )
    assert not any((target / path).exists() for path, _ in files)


@pytest.mark.parametrize(
    "coordinate",
    [
        "python_abi",
        "python_version",
        "python_implementation",
        "architecture",
        "prefix",
        "alias",
        "digest",
        "source-link",
        "target-link",
        "copy-corruption",
    ],
)
def test_dependency_supply_preserves_identity_and_complete_manifest_before_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, coordinate: str
) -> None:
    source, target, files, identities = _supply_case(tmp_path, monkeypatch)
    source_python, target_python = source / "bin/python", target / "bin/python"
    expected = "hook_runtime_dependency_supply_invalid"
    source_bytes = {(source / p): (source / p).read_bytes() for p, _ in files}
    if coordinate in {"python_abi", "python_version", "python_implementation", "architecture"}:
        identities[target_python][coordinate] = "incongruent"
        expected = "hook_runtime_dependency_supply_incompatible"
    elif coordinate in {"prefix", "alias"}:
        identities[source_python if coordinate == "prefix" else target_python]["prefix"] = (
            tmp_path if coordinate == "prefix" else source
        ).as_posix()
        expected = (
            "hook_runtime_dependency_supply_invalid"
            if coordinate == "prefix"
            else "hook_runtime_dependency_supply_alias"
        )
    elif coordinate == "digest":
        files[-1] = (files[-1][0], "0" * 64)
    elif coordinate in {"source-link", "target-link"}:
        linked = (source if coordinate == "source-link" else target) / files[-1][0]
        linked.unlink(missing_ok=True)
        linked.parent.mkdir(parents=True, exist_ok=True)
        linked.symlink_to(source / files[0][0])
    else:
        monkeypatch.setattr(
            supply.shutil, "copy2", lambda _source, target: target.write_bytes(b"corrupt")
        )
    with pytest.raises(ValueError, match=expected):
        supply.project_dependency_supply(source_python, target_python)
    if coordinate == "copy-corruption":
        assert (target / files[0][0]).read_bytes() == b"corrupt"
    else:
        assert not (target / files[0][0]).exists()
    assert all(
        path.read_bytes() == payload
        for path, payload in source_bytes.items()
        if not path.is_symlink()
    )


@pytest.mark.parametrize("fault", ["alias", "incompatible"])
def test_locked_install_rejects_unsafe_target_before_native_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """Changing the supply mechanism cannot permit source mutation or ABI drift."""
    source, target, _files, facts = _supply_case(tmp_path, monkeypatch)
    source_python, target_python = source / "bin/python", target / "bin/python"
    if fault == "alias":
        facts[target_python]["prefix"] = source.as_posix()
    else:
        facts[target_python]["python_abi"] = "different"
    calls = []
    monkeypatch.setattr(
        supply, "run_runtime_tool", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    expected = "alias" if fault == "alias" else "incompatible"
    with pytest.raises(ValueError, match=f"dependency_supply_{expected}"):
        supply.install_locked_runtime(
            tmp_path, source_python, target_python, tmp_path / "wheel", tmp_path / "pylock.toml"
        )

    assert not calls


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "json",
        "missing",
        "relative-prefix",
        "absent-prefix",
        "exit",
        "absolute-file",
        "traversal",
        "digest",
    ],
)
def test_dependency_observation_validates_native_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    payload = {"prefix": tmp_path.as_posix(), "files": {"lib/module.py": "a" * 64}}
    if fault in {"relative-prefix", "absent-prefix"}:
        payload["prefix"] = "relative" if fault == "relative-prefix" else str(tmp_path / "absent")
    if fault in {"absolute-file", "traversal", "digest"}:
        key = {
            "absolute-file": str(tmp_path / "module.py"),
            "traversal": "../module.py",
            "digest": "lib/module.py",
        }[fault]
        payload["files"] = {key: "bad" if fault == "digest" else "a" * 64}
    output = "{" if fault == "json" else json.dumps({} if fault == "missing" else payload)
    calls = []
    python = tmp_path / "python"

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return subprocess.CompletedProcess(
            command, 2 if fault == "exit" else 0, output, "native failure"
        )

    monkeypatch.setattr(supply.subprocess, "run", run)
    if fault == "none":
        assert supply.observe_dependency_supply(python) == (
            tmp_path,
            ((Path("lib/module.py"), "a" * 64),),
        )
    else:
        with pytest.raises(ValueError, match="hook_runtime_dependency_supply_invalid"):
            supply.observe_dependency_supply(python)
    assert calls == [
        (
            (python.as_posix(), "-B", "-I", "-c", vars(supply)["_SUPPLY_OBSERVATION"]),
            {"capture_output": True, "check": False, "text": True},
        )
    ]


def test_locked_requirements_require_the_exported_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = []
    monkeypatch.setattr(
        supply, "run_runtime_tool", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    with pytest.raises(ValueError, match="hook_runtime_locked_requirements_missing"):
        supply.prepare_locked_requirements(tmp_path, tmp_path, tmp_path / "python")
    assert len(calls) == 2


def _artifact_wheel(root: Path, name: str, value: str) -> Path:
    """Create a local immutable-input wheel without running its module."""
    wheel = root / f"{name}-1.0-py3-none-any.whl"
    metadata = f"{name}-1.0.dist-info"
    files = {
        f"{name}.py": f"VALUE = {value!r}\n",
        f"{metadata}/METADATA": f"Metadata-Version: 2.4\nName: {name}\nVersion: 1.0\n\n",
        f"{metadata}/WHEEL": ("Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n"),
    }
    files[f"{metadata}/RECORD"] = "".join(f"{path},,\n" for path in files)
    with zipfile.ZipFile(wheel, "w") as archive:
        for path, data in files.items():
            archive.writestr(path, data)
    return wheel


@pytest.mark.parametrize(
    "fault",
    ["none", "altered-target", "missing", "altered-artifact", "marker", "format", "version"],
)
def test_native_locked_install_uses_artifacts_not_installed_package_identity(
    tmp_path: Path, fault: str
) -> None:
    """Native installation ignores installed source bytes and repairs stale targets."""
    wheel = _artifact_wheel(tmp_path, "dependency", "locked")
    product = _artifact_wheel(tmp_path, "product", "product")
    lock = tmp_path / "pylock.toml"
    lock.write_text(
        tomli_w.dumps(
            {
                "lock-version": "1.0",
                "created-by": "ethos-test",
                "requires-python": ">=3.12",
                "packages": [
                    {
                        "name": "dependency",
                        "version": "1.0",
                        "wheels": [
                            {
                                "url": wheel.as_uri(),
                                "hashes": {
                                    "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()
                                },
                            }
                        ],
                    }
                ],
            }
        )
    )
    environment = tmp_path / "target"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    purelib = Path(
        subprocess.check_output(
            (
                str(python),
                "-B",
                "-I",
                "-c",
                "import sysconfig; print(sysconfig.get_path('purelib'))",
            ),
            text=True,
            timeout=15,
        ).strip()
    )
    if fault in {"marker", "format", "version"}:
        payload = tomllib.loads(lock.read_text())
        if fault == "marker":
            payload["packages"][0]["marker"] = "unknown_variable"
        elif fault == "format":
            payload["lock-version"] = "2.0"
        else:
            payload["packages"][0]["version"] = "2.0"
        lock.write_text(tomli_w.dumps(payload))
    elif fault == "altered-target":
        with zipfile.ZipFile(wheel) as archive:
            archive.extractall(purelib)
        (purelib / "dependency.py").write_text("VALUE = 'altered-installed-bytes'\n")
    elif fault == "missing":
        wheel.unlink()
    elif fault == "altered-artifact":
        _artifact_wheel(tmp_path, "dependency", "altered-artifact")

    if fault not in {"none", "altered-target"}:
        with pytest.raises(ValueError, match="error:"):
            supply.install_locked_runtime(tmp_path, Path(sys.executable), python, product, lock)
        assert not (purelib / "product.py").exists()
        return

    supply.install_locked_runtime(tmp_path, Path(sys.executable), python, product, lock)

    assert (purelib / "dependency.py").read_text() == "VALUE = 'locked'\n"
    assert (purelib / "product.py").read_text() == "VALUE = 'product'\n"
    assert not (purelib / "dependency.py").is_symlink()
    assert not (purelib / "product.py").is_symlink()
