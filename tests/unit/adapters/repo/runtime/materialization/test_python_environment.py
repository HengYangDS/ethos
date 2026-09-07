"""Observed Python identity contracts for runtime materialization."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.runtime.materialization.python_environment as python_environment
from ethos.adapters.repo.runtime.materialization.python_environment import observe_python_facts
from ethos.adapters.repo.runtime.materialization.python_environment import (
    require_python_image_source,
)

_IDENTITY = {
    "python_abi": "cpython-314",
    "python_version": "3.14.7",
    "python_implementation": "cpython",
    "architecture": "test",
}


def _python(path: Path) -> Path:
    """Create one executable-coordinate fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


def _image(root: Path) -> Path:
    """Create the minimum copyable POSIX Python-image fixture."""
    interpreter = _python(root / "bin/python")
    _python(root / "lib/python3.14/os.py")
    return interpreter


def _facts(
    executable: Path | str,
    *,
    base_executable: Path | str | None = None,
    prefix: Path | str | None = None,
    base_prefix: Path | str | None = None,
    framework: str = "",
    identity: dict[str, str] | None = None,
) -> dict[str, str]:
    """Describe one observed interpreter using only semantic coordinates."""
    executable_path = Path(executable)
    effective_prefix = prefix if prefix is not None else executable_path.parent.parent
    return {
        **(identity or _IDENTITY),
        "executable": str(executable),
        "base_executable": str(base_executable or executable),
        "prefix": str(effective_prefix),
        "base_prefix": str(base_prefix if base_prefix is not None else effective_prefix),
        "python_framework": framework,
    }


def _observed_pair(
    tmp_path: Path,
    *,
    framework: str = "",
) -> tuple[Path, Path, Path, dict[Path, dict[str, str]]]:
    """Create one invocation-to-image relation and its observed facts."""
    invoked = _python(tmp_path / "venv/bin/python")
    source_root = tmp_path / "base"
    source = _image(source_root)
    observations = {
        invoked.resolve(): _facts(
            invoked,
            base_executable=source,
            prefix=invoked.parent.parent,
            base_prefix=source_root,
            framework=framework,
        ),
        source.resolve(): _facts(source, prefix=source_root, framework=framework),
    }
    return invoked, source, source_root, observations


def _observe(
    monkeypatch: pytest.MonkeyPatch,
    observations: dict[Path, dict[str, str]],
) -> None:
    """Project one deterministic observation map into the adapter."""
    monkeypatch.setattr(
        python_environment,
        "observe_python_facts",
        lambda path: observations[path.resolve()],
    )


def _reject_without_candidates(
    invoked: Path,
    observations: dict[Path, dict[str, str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Assert fail-closed admission after the supplied observations."""
    _observe(monkeypatch, observations)
    monkeypatch.setattr(python_environment, "_installed_python_candidates", lambda *_args: ())
    with pytest.raises(ValueError, match="hook_runtime_interpreter_source_unavailable"):
        require_python_image_source(invoked)


def test_python_facts_bind_the_invoked_and_base_executables() -> None:
    """Python facts identify both the authenticated invocation and its base."""
    invoked = Path(sys.executable)

    facts = observe_python_facts(invoked)

    assert Path(facts["executable"]).resolve() == invoked.resolve()
    assert Path(facts["base_executable"]).is_file()


def test_python_path_identity_prefers_native_object_identity(tmp_path):
    """Hard links identify the same Python object without lexical equality."""
    source = _python(tmp_path / "python")
    alias = tmp_path / "alias"
    alias.hardlink_to(source)
    assert python_environment.same_python_path(source, alias)
    assert not python_environment.same_python_path(source, _python(tmp_path / "other"))


@pytest.mark.parametrize("invocation", ["venv", "direct"])
def test_congruent_image_uses_native_containment_without_candidate_discovery(
    tmp_path, monkeypatch, invocation
):
    """An admitted direct image supplies native identity for either invocation."""
    invoked, source, source_root, observations = _observed_pair(tmp_path)
    if invocation == "direct":
        invoked = source
    _observe(monkeypatch, observations)
    monkeypatch.setattr(
        python_environment,
        "_installed_python_candidates",
        lambda *_a: pytest.fail("admitted image triggered candidate discovery"),
    )
    native = python_environment.python_path_within
    relations = []

    def within(path, root):
        relations.append((Path(path).resolve(), Path(root).resolve()))
        return native(path, root)

    monkeypatch.setattr(python_environment, "python_path_within", within)
    facts = require_python_image_source(invoked)
    assert Path(facts["executable"]).resolve() == source.resolve()
    assert facts["prefix"] == facts["base_prefix"] == str(source_root)
    assert {key: facts[key] for key in _IDENTITY} == _IDENTITY
    assert facts["python_framework"] == ""
    assert relations == [
        (invoked.resolve(), invoked.parent.parent.resolve()),
        (source.resolve(), source_root.resolve()),
    ]


@pytest.mark.parametrize("base_kind", ["framework", "missing-stdlib"])
def test_image_source_discovery_is_read_only_and_uses_the_invoking_python(
    monkeypatch, tmp_path, base_kind
):
    """Fallback discovery enumerates installed candidates without provisioning Python."""
    invoked, base, home, observations = _observed_pair(
        tmp_path, framework="Python" if base_kind == "framework" else ""
    )
    if base_kind == "missing-stdlib":
        shutil.rmtree(home / "lib")
    incompatible = _image(tmp_path / "incompatible")
    observations[incompatible.resolve()] = _facts(
        incompatible, identity=_IDENTITY | {"architecture": "other"}
    )
    standalone_root = tmp_path / "standalone"
    standalone = _image(standalone_root)
    observations[standalone.resolve()] = _facts(standalone, prefix=standalone_root)
    _observe(monkeypatch, observations)
    commands: list[tuple[str, ...]] = []
    monkeypatch.setenv("VIRTUAL_ENV", str(tmp_path / "ambient"))

    def run(command: tuple[str, ...], **kwargs) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert "VIRTUAL_ENV" not in kwargs["env"]
        assert {
            key: kwargs["env"][key] for key in ("UV_NO_CACHE", "UV_OFFLINE", "UV_PYTHON_DOWNLOADS")
        } == {"UV_NO_CACHE": "1", "UV_OFFLINE": "1", "UV_PYTHON_DOWNLOADS": "never"}
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                [
                    {"path": str(path)}
                    for path in (standalone, base, incompatible, standalone, "relative")
                ]
            ),
            "",
        )

    monkeypatch.setattr(python_environment.subprocess, "run", run)

    source_facts = require_python_image_source(invoked)

    assert Path(source_facts["executable"]).resolve() == standalone.resolve()
    assert commands == [
        (
            invoked.as_posix(),
            "-B",
            "-I",
            "-m",
            "uv",
            "python",
            "list",
            "--only-installed",
            "--output-format",
            "json",
            "--no-python-downloads",
            "--offline",
            "--no-config",
            _IDENTITY["python_version"],
        )
    ]


@pytest.mark.parametrize(
    "invalidity",
    [
        "missing",
        "outside_base_prefix",
        "virtual_source",
        "identity_mismatch",
        "relative_source",
        "incomplete_facts",
        "invoked_executable",
        "source_base_executable",
        "invocation_outside_prefix",
        "relative_observation",
    ],
)
def test_python_image_source_rejects_invalid_native_identity(tmp_path, monkeypatch, invalidity):
    """Image ancestry cannot override exact, independent, congruent coordinates."""
    invoked, source, base, observations = _observed_pair(tmp_path)
    outside = _python(tmp_path / "outside/bin/python")
    candidate = {"missing": base / "bin/missing-python", "outside_base_prefix": outside}.get(
        invalidity, source
    )
    observations[invoked.resolve()]["base_executable"] = str(candidate)
    observations[candidate.resolve()] = _facts(candidate, prefix=base)
    if invalidity == "incomplete_facts":
        observations[candidate.resolve()].pop("base_prefix")
    elif invalidity == "relative_observation":
        observations[invoked.resolve()] |= {
            "base_executable": "base/bin/python",
            "base_prefix": "base",
        }
        observations[source.resolve()] = _facts("base/bin/python", prefix="base")
        monkeypatch.chdir(tmp_path)
    elif invalidity in {"invoked_executable", "invocation_outside_prefix"}:
        field = "executable" if invalidity == "invoked_executable" else "prefix"
        observations[invoked.resolve()][field] = str(outside)
    else:
        updates = {
            "virtual_source": {"prefix": str(base / "virtual")},
            "identity_mismatch": {"python_version": "3.14.8"},
            "relative_source": {"prefix": "relative-prefix"},
            "source_base_executable": {"base_executable": str(outside)},
        }
        observations[candidate.resolve()] |= updates.get(invalidity, {})
    _reject_without_candidates(invoked, observations, monkeypatch)


@pytest.mark.parametrize(("payload", "status"), [("not-json", 0), ("[]", 0), ("{}", 0), ("{}", 2)])
def test_python_facts_reject_failed_or_incomplete_observation(monkeypatch, payload, status):
    monkeypatch.setattr(
        python_environment.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], status, payload, "probe failed"),
    )
    with pytest.raises(ValueError, match="hook_runtime_python_abi_invalid"):
        observe_python_facts(Path(sys.executable))


@pytest.mark.parametrize(
    ("payload", "status"),
    [
        ("bad-json", 0),
        ("{}", 0),
        ("[null]", 0),
        ('[{"path":1}]', 0),
        ('[{"path":"relative"}]', 0),
        ("[]", 0),
        ("[]", 2),
    ],
)
def test_installed_image_discovery_rejects_invalid_coordinates(
    tmp_path, monkeypatch, payload, status
):
    invoked, _base, _root, observations = _observed_pair(tmp_path, framework="Python")
    _observe(monkeypatch, observations)
    monkeypatch.setattr(
        python_environment.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], status, payload, ""),
    )
    with pytest.raises(ValueError, match="hook_runtime_interpreter_source_unavailable"):
        require_python_image_source(invoked)


@pytest.mark.parametrize(
    ("link", "admitted"),
    [("inside", True), ("escape", False), ("absolute", False), ("broken", False)],
)
def test_python_image_requires_relocatable_library_links(tmp_path, link, admitted):
    source = _image(tmp_path / "image")
    library = source.parent.parent / "lib"
    stdlib = library / "python3.14"
    _python(tmp_path / "outside.py")
    destination = {
        "inside": "os.py",
        "escape": "../../../outside.py",
        "absolute": str(stdlib / "os.py"),
        "broken": "missing.py",
    }[link]
    (stdlib / "alias.py").symlink_to(destination)
    _python(library / "libpython3.14.1.dylib")
    (library / "libpython3.14.dylib").symlink_to("libpython3.14.1.dylib")
    assert python_environment.python_image_source_capable(source, _facts(source)) is admitted


@pytest.mark.parametrize(
    ("candidate", "boundary", "contained"),
    [
        (r"C:\PYTHON\python.exe", r"c:\python", True),
        (r"D:\python.exe", r"C:\python", False),
        (r"C:\python-other\python.exe", r"C:\python", False),
    ],
)
def test_windows_python_containment_uses_native_drive_boundaries(
    monkeypatch, candidate, boundary, contained
):
    monkeypatch.setattr(python_environment, "os", SimpleNamespace(name="nt", fspath=os.fspath))
    assert python_environment.python_path_within(candidate, boundary) is contained


@pytest.mark.parametrize(
    "fault",
    ["none", "missing-dlls", "linked-home", "linked-python", "linked-stdlib", "linked-dlls"],
)
def test_windows_image_requires_a_copyable_native_prefix(tmp_path, monkeypatch, fault):
    home = tmp_path / "python"
    python = _python(home / "python.exe")
    _python(home / "Lib/os.py")
    _python(home / "DLLs/_ssl.pyd")
    for name in ("python314.dll", "vcruntime140.dll"):
        _python(home / name)
    monkeypatch.setattr(python_environment, "os", SimpleNamespace(name="nt", fspath=os.fspath))
    facts = _facts(python, prefix=home)
    assert python_environment.python_image_source_capable(python, facts)
    if fault == "missing-dlls":
        shutil.rmtree(home / "DLLs")
    elif fault.startswith("linked"):
        target = {
            "linked-home": home,
            "linked-python": python,
            "linked-stdlib": home / "Lib",
            "linked-dlls": home / "DLLs",
        }[fault]
        saved = target.with_name(target.name + "-saved")
        target.rename(saved)
        target.symlink_to(saved, target_is_directory=saved.is_dir())
    assert python_environment.python_image_source_capable(python, facts) is (
        fault in {"none", "missing-dlls"}
    )
