"""Observed Python identity contracts for runtime materialization."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

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
    invoked_relative: str = "venv/bin/python",
    source_name: str = "base",
    framework: str = "",
) -> tuple[Path, Path, Path, dict[Path, dict[str, str]]]:
    """Create one invocation-to-image relation and its observed facts."""
    invoked = _python(tmp_path / invoked_relative)
    source_root = tmp_path / source_name
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


def test_python_path_identity_prefers_native_object_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Filesystem aliases identify one Python path despite different spellings."""
    observed: list[tuple[str, str]] = []

    def samefile(first: Path, second: str) -> bool:
        observed.append((str(first), second))
        return True

    monkeypatch.setattr(Path, "samefile", samefile)

    assert python_environment.same_python_path("/native/first", "/native/alias")
    assert observed == [("/native/first", "/native/alias")]


def test_virtual_environment_selects_a_congruent_relocatable_image() -> None:
    """A venv supplies identity without forcing its base to supply the image."""
    invoked = Path(sys.executable)

    source_facts = require_python_image_source(invoked)

    assert Path(source_facts["executable"]).is_file()
    assert source_facts["prefix"] == source_facts["base_prefix"]
    assert source_facts.get("python_framework", "") == ""
    assert {
        key: source_facts[key]
        for key in ("python_abi", "python_version", "python_implementation", "architecture")
    } == {
        key: observe_python_facts(invoked)[key]
        for key in ("python_abi", "python_version", "python_implementation", "architecture")
    }


def test_direct_relocatable_interpreter_admits_itself_without_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A directly invoked image is selected without fallback discovery."""
    invoked = Path(require_python_image_source(Path(sys.executable))["executable"])
    monkeypatch.setattr(
        python_environment,
        "_installed_python_candidates",
        lambda *_args: pytest.fail("direct image triggered candidate discovery"),
    )

    source_facts = require_python_image_source(invoked)

    assert Path(source_facts["executable"]).resolve() == invoked.resolve()
    assert source_facts["prefix"] == source_facts["base_prefix"]


def test_non_relocatable_base_selects_an_installed_congruent_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Invocation ancestry does not override native image capability."""
    invoked, _framework, _root, observations = _observed_pair(
        tmp_path,
        source_name="framework",
        framework="Python",
    )
    standalone_root = tmp_path / "standalone"
    standalone = _image(standalone_root)
    observations[standalone.resolve()] = _facts(standalone, prefix=standalone_root)
    _observe(monkeypatch, observations)
    monkeypatch.setattr(
        python_environment,
        "_installed_python_candidates",
        lambda _python, _facts: (standalone,),
    )

    source_facts = require_python_image_source(invoked)

    assert Path(source_facts["executable"]).resolve() == standalone.resolve()


def test_noncopyable_base_selects_an_installed_copyable_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Runtime identity alone cannot admit a source without a native image."""
    invoked, _base, base_root, observations = _observed_pair(tmp_path)
    shutil.rmtree(base_root / "lib")
    standalone_root = tmp_path / "standalone"
    standalone = _image(standalone_root)
    observations[standalone.resolve()] = _facts(standalone, prefix=standalone_root)
    _observe(monkeypatch, observations)
    monkeypatch.setattr(
        python_environment,
        "_installed_python_candidates",
        lambda _python, _facts: (standalone,),
    )

    source_facts = require_python_image_source(invoked)

    assert Path(source_facts["executable"]).resolve() == standalone.resolve()


def test_image_source_discovery_is_read_only_and_uses_the_invoking_python(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Fallback discovery enumerates installed candidates without provisioning Python."""
    invoked, _framework, _root, observations = _observed_pair(
        tmp_path,
        source_name="framework",
        framework="Python",
    )
    standalone_root = tmp_path / "standalone"
    standalone = _image(standalone_root)
    observations[standalone.resolve()] = _facts(standalone, prefix=standalone_root)
    _observe(monkeypatch, observations)
    commands: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps([{"path": standalone.as_posix()}]),
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


def test_non_relocatable_base_without_an_installed_image_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An unusable base never becomes a runtime merely because it is ancestral."""
    invoked, _framework, _root, observations = _observed_pair(
        tmp_path,
        source_name="framework",
        framework="Python",
    )

    _reject_without_candidates(invoked, observations, monkeypatch)


@pytest.mark.parametrize("contradiction", ["invoked_executable", "source_base_executable"])
def test_python_image_source_rejects_contradictory_executable_identity(
    contradiction: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Executable self-observation must agree at both ends of the relation."""
    invoked, source, _root, observations = _observed_pair(tmp_path)
    other = _python(source.parent / "other-python")
    key = invoked.resolve() if contradiction == "invoked_executable" else source.resolve()
    field = "executable" if contradiction == "invoked_executable" else "base_executable"
    observations[key][field] = str(other)

    _reject_without_candidates(invoked, observations, monkeypatch)


def test_python_image_source_rejects_invocation_outside_its_prefix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """An invocation cannot borrow an unrelated environment's prefix identity."""
    invoked, _source, _root, observations = _observed_pair(
        tmp_path,
        invoked_relative="outside/bin/python",
    )
    observations[invoked.resolve()]["prefix"] = str(tmp_path / "venv")

    _reject_without_candidates(invoked, observations, monkeypatch)


def test_python_image_source_delegates_every_containment_decision_to_one_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Both invocation and source closure use the native path relation owner."""
    invoked, source, source_root, observations = _observed_pair(tmp_path)
    _observe(monkeypatch, observations)
    native_path_within = python_environment.python_path_within
    observed_relations: list[tuple[Path, Path]] = []

    def observe_relation(path: str | Path, root: str | Path) -> bool:
        observed_relations.append((Path(path).resolve(), Path(root).resolve()))
        return native_path_within(path, root)

    monkeypatch.setattr(python_environment, "python_path_within", observe_relation)

    require_python_image_source(invoked)

    assert observed_relations == [
        (invoked.resolve(), invoked.parent.parent.resolve()),
        (source.resolve(), source_root.resolve()),
    ]


@pytest.mark.parametrize(
    "invalidity",
    ["missing", "outside_base_prefix", "virtual_source", "identity_mismatch"],
)
def test_python_image_source_rejects_invalid_base_relations(
    invalidity: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Only one present, independent, congruent base interpreter is admissible."""
    invoked, source, base, observations = _observed_pair(tmp_path)
    outside = _python(tmp_path / "outside/bin/python")
    candidate = {"missing": base / "bin/missing-python", "outside_base_prefix": outside}.get(
        invalidity,
        source,
    )
    observations[invoked.resolve()]["base_executable"] = str(candidate)
    observations[candidate.resolve()] = _facts(
        candidate,
        prefix=base / "virtual" if invalidity == "virtual_source" else base,
        base_prefix=base,
        identity=_IDENTITY
        | ({"python_version": "3.14.8"} if invalidity == "identity_mismatch" else {}),
    )

    _reject_without_candidates(invoked, observations, monkeypatch)


def test_python_image_source_rejects_relative_observed_coordinates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Interpreter identity never depends on the observer's current directory."""
    invoked, source, _root, observations = _observed_pair(tmp_path)
    observations[invoked.resolve()] |= {
        "base_executable": "base/bin/python",
        "base_prefix": "base",
    }
    observations[source.resolve()] = _facts(
        "base/bin/python",
        prefix="base",
        base_prefix="base",
    )
    monkeypatch.chdir(tmp_path)

    _reject_without_candidates(invoked, observations, monkeypatch)
