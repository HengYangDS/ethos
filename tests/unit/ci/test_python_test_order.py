"""Recorded test durations order the next parallel collection longest first."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import Mock

import tools.ci.python_test_gate as python_test_gate
from ethos.adapters.process import run_command
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.ci import python_test_order

if TYPE_CHECKING:
    import subprocess
    from pathlib import Path

_CASES = (
    "import time\n\n"
    "def test_short():\n    pass\n\n"
    "def test_long():\n    time.sleep(0.2)\n\n"
    "def test_middle():\n    pass\n"
)


def _pytest(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_command(
        tmp_path,
        (
            str(python_test_gate.PYTHON),
            "-m",
            "pytest",
            "-c",
            str(python_test_gate.PYTEST_CONFIG),
            f"--rootdir={tmp_path}",
            f"--basetemp={tmp_path / 'owned-temp'}",
            "-o",
            f"cache_dir={tmp_path / 'cache'}",
            "-p",
            "tools.ci.python_test_order",
            "--no-cov",
            *args,
            "test_cases.py",
        ),
        timeout=60,
        remove_env=("PYTEST_ADDOPTS", "PYTEST_XDIST_WORKER", "PYTHONPATH"),
    )


def _collected(tmp_path: Path) -> list[str]:
    result = _pytest(tmp_path, "--collect-only", "-q")
    assert result.returncode == 0, result.stdout + result.stderr
    return [line.split("::")[-1] for line in result.stdout.splitlines() if "::" in line]


def test_recorded_durations_start_longest_first_and_new_tests_ahead(tmp_path: Path) -> None:
    """A run records every test; the next collection follows the record, new tests first."""
    (tmp_path / "test_cases.py").write_text(_CASES, encoding="utf-8")
    assert _collected(tmp_path) == ["test_short", "test_long", "test_middle"]
    first = _pytest(tmp_path, "-q")
    assert first.returncode == 0, first.stdout + first.stderr
    record = tmp_path / "cache/v/ethos/test-durations"
    measured = json.loads(record.read_text(encoding="utf-8"))
    assert set(measured) == {f"test_cases.py::test_{name}" for name in ("short", "long", "middle")}
    assert measured["test_cases.py::test_long"] >= 0.2
    record.write_text(
        json.dumps({"test_cases.py::test_short": 1, "test_cases.py::test_middle": 2}),
        encoding="utf-8",
    )
    assert _collected(tmp_path) == ["test_long", "test_middle", "test_short"]
    with (tmp_path / "test_cases.py").open("a", encoding="utf-8") as cases:
        cases.write("\ndef test_new():\n    pass\n")
    assert _collected(tmp_path)[:2] == ["test_long", "test_new"]
    parallel = _pytest(tmp_path, "-q", "-n", "2")
    assert parallel.returncode == 0, parallel.stdout + parallel.stderr


def test_workers_order_by_the_controller_snapshot_and_never_write_it() -> None:
    """Each worker sorts with the snapshot it was handed and leaves the record alone."""
    record = Mock(get=Mock(return_value={"a": 1, "b": 2.5, "c": True}))
    controller = python_test_order.DurationOrder(SimpleNamespace(cache=record))
    node = SimpleNamespace(workerinput={})
    controller.pytest_configure_node(node)
    assert node.workerinput == {"ethos_test_durations": {"a": 1.0, "b": 2.5}}
    for phase in (0.25, 0.25):
        controller.pytest_runtest_logreport(SimpleNamespace(nodeid="b", duration=phase))
    controller.pytest_sessionfinish()
    record.set.assert_called_once_with("ethos/test-durations", {"a": 1.0, "b": 0.5})
    cache = Mock()
    worker = python_test_order.DurationOrder(
        SimpleNamespace(workerinput=node.workerinput, cache=cache)
    )
    items = [SimpleNamespace(nodeid=name) for name in ("a", "new", "b")]
    worker.pytest_collection_modifyitems(items)
    assert [item.nodeid for item in items] == ["new", "b", "a"]
    worker.pytest_runtest_logreport(SimpleNamespace(nodeid="a", duration=0.5))
    worker.pytest_sessionfinish()
    cache.get.assert_not_called()
    cache.set.assert_not_called()
    uncached = python_test_order.DurationOrder(SimpleNamespace(cache=None))
    items = [SimpleNamespace(nodeid=name) for name in ("y", "x")]
    uncached.pytest_collection_modifyitems(items)
    uncached.pytest_runtest_logreport(SimpleNamespace(nodeid="x", duration=0.5))
    uncached.pytest_sessionfinish()
    assert [item.nodeid for item in items] == ["y", "x"]


def test_every_worktree_of_a_repository_shares_one_duration_record(tmp_path: Path) -> None:
    """A landing proves in a new Work Lane, which inherits the record its repository kept."""
    repository = init_git_repo(tmp_path / "repository")
    lane = tmp_path / "lane"
    git(repository, "worktree", "add", "-q", "-b", "work/lane", str(lane))
    common = repository / ".git"

    shared = python_test_gate.shared_pytest_cache(lane)

    assert shared == common.resolve() / "ethos/tool-cache/pytest"
    assert python_test_gate.shared_pytest_cache(repository) == shared
    unversioned = tmp_path / "unversioned"
    unversioned.mkdir()
    assert python_test_gate.shared_pytest_cache(unversioned) is None
