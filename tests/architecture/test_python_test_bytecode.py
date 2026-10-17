"""Shared test bytecode reaches every test process without stale code or new writes."""

from __future__ import annotations

import os
import sys
from types import SimpleNamespace
from typing import TYPE_CHECKING
from typing import cast

import tools.ci.python_test_gate as python_test_gate
from ethos.adapters.process import run_command
from tools.ci import python_test_bytecode

if TYPE_CHECKING:
    from pathlib import Path

    import nox


def test_test_processes_reuse_gate_bytecode_without_stale_or_new_writes(
    tmp_path: Path, monkeypatch
) -> None:
    """Gate bytecode serves test processes, follows edits by content and stays read-only."""
    for inherited in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX"):
        monkeypatch.delenv(inherited, raising=False)
    source = tmp_path / "src"
    source.mkdir()
    for name in ("cached_value", "edited_value"):
        (source / f"{name}.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(python_test_gate, "ROOT", tmp_path)
    monkeypatch.setattr(python_test_bytecode, "sources", lambda _root: (source,))
    gate = python_test_gate.PythonTestGate(
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
    monkeypatch.setattr(python_test_gate, "_head", lambda: gate.s.head)
    gate.compile_bytecode()
    cache = tmp_path / python_test_bytecode.CACHE
    tag = sys.implementation.cache_tag
    (cached_pyc,) = cache.rglob(f"cached_value.{tag}.pyc")
    (edited_pyc,) = cache.rglob(f"edited_value.{tag}.pyc")
    compiled = edited_pyc.read_bytes()
    edited = source / "edited_value.py"
    unchanged = edited.stat()
    edited.write_text("VALUE = 2\n", encoding="utf-8")
    os.utime(edited, ns=(unchanged.st_atime_ns, unchanged.st_mtime_ns))
    (source / "generated_value.py").write_text("VALUE = 3\n", encoding="utf-8")
    probe = (
        "import cached_value, edited_value, generated_value; "
        "print(cached_value.VALUE, edited_value.VALUE, generated_value.VALUE)"
    )
    observed = []

    def execute(*_pytest: str, env, **_kwargs) -> None:
        variables = {key: value for key, value in env.items() if value is not None}
        observed.append(
            run_command(
                tmp_path,
                (str(python_test_gate.PYTHON), "-v", "-c", probe),
                timeout=60,
                env={**variables, "PYTHONPATH": str(source)},
                remove_env=tuple(key for key, value in env.items() if value is None),
            )
        )

    gate.run_tests(cast("nox.Session", SimpleNamespace(run=execute)))

    (child,) = observed
    assert child.stdout.split() == ["1", "2", "3"], child.stderr
    origins = {
        name: line.removeprefix("# code object from ").strip("'")
        for line in child.stderr.splitlines()
        if line.startswith("# code object from ")
        for name in ("cached_value", "edited_value", "generated_value")
        if f"{name}." in line
    }
    assert origins == {
        "cached_value": str(cached_pyc),
        "edited_value": str(edited),
        "generated_value": str(source / "generated_value.py"),
    }
    assert sorted(path.name for path in cache.rglob("*.pyc")) == [
        f"cached_value.{tag}.pyc",
        f"edited_value.{tag}.pyc",
    ]
    assert edited_pyc.read_bytes() == compiled
    assert not any(source.rglob("__pycache__"))
