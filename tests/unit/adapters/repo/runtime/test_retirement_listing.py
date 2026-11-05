"""Process listings retain generations through native path identity, not command text."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.process as process
import ethos.adapters.repo.runtime.retirement as retirement
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.unit.adapters.repo.runtime.support import generation_tree


@pytest.mark.parametrize("layout", ["plain", "with spaces", "O'Brien (native); owner"])
@pytest.mark.parametrize(
    "reference", ["exact", "launcher", "alias", "direct-alias", "foreign-root", "longer-name"]
)
def test_generation_reference_preserves_repository_and_path_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reference: str, layout: str
) -> None:
    """Equal digest spelling in another repository is not this runtime dependency."""
    repo, hooks, runtime = generation_tree(tmp_path / layout)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    alias = tmp_path / "runtime-alias"
    alias.symlink_to(candidate.parent, target_is_directory=True)
    direct = tmp_path / "selected-runtime"
    direct.symlink_to(candidate, target_is_directory=True)
    command = {
        "exact": f"{candidate}/python/bin/python -m ethos.cli",
        "launcher": f"{hooks}/../../runtime/{candidate.name}/python/bin/python -m ethos.cli",
        "alias": f"{alias}/{candidate.name}/python/bin/python -m ethos.cli",
        "direct-alias": f"{direct}/python/bin/python -m ethos.cli",
        "foreign-root": f"{tmp_path}/other/.git/ethos/runtime/{candidate.name}/python/bin/python",
        "longer-name": f"{candidate}-unrelated/python/bin/python",
    }[reference]
    monkeypatch.setattr(retirement, "process_commands", lambda _root: command)

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    needed = reference in {"exact", "launcher", "alias", "direct-alias"}
    assert result["state"] == "complete", result
    assert candidate.exists() is needed
    assert (candidate.as_posix() in result["retained"]) is needed
    assert (candidate.as_posix() in result["removed"]) is not needed


@pytest.mark.parametrize("arguments", ["absent-paths", "native-service-tail"])
def test_unrelated_command_arguments_do_not_amplify_path_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, arguments: str
) -> None:
    """Resolver work follows native path components, not unbounded command arguments."""
    repo, hooks, runtime = generation_tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    tail = (
        " ".join(f"/not-present-{i}/arg" for i in range(200))
        if arguments == "absent-paths"
        else "-BSServiceDomains " + json.dumps({"LaunchArguments": ["service" * 80]})
    )
    command = f"{candidate}/payload {tail}"
    monkeypatch.setattr(retirement, "process_commands", lambda _root: command)
    resolve = Path.resolve
    calls = 0

    def measured(path: Path, *args, **kwargs):
        nonlocal calls
        calls += 1
        assert calls < 1500, "command suffix combinations amplify native resolution work"
        return resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", measured)

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "complete", result
    assert candidate.as_posix() in result["retained"]
    assert (candidate / "payload").read_text() == "b" * 64


@pytest.mark.parametrize("listing", ["deleted", "dangling"])
def test_listed_path_deleted_while_observed_is_an_observed_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, listing: str
) -> None:
    """A path deleted after its existence check protects nothing; a dangling link stays unknown."""
    repo, hooks, runtime = generation_tree(tmp_path)
    obsolete = fixture_runtime_generation(runtime, "history")
    listed = tmp_path / "listed"
    if listing == "deleted":
        listed.mkdir()
    else:
        listed.symlink_to(tmp_path / "absent")
    exists = Path.exists

    def deleted_after_check(path: Path, *args, **kwargs) -> bool:
        found = exists(path, *args, **kwargs)
        if found and path == listed:
            listed.rmdir()
        return found

    monkeypatch.setattr(Path, "exists", deleted_after_check)
    monkeypatch.setattr(retirement, "process_commands", lambda _root: f"git -C {listed} status")

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    deleted = listing == "deleted"
    assert result["state"] == ("complete" if deleted else "deferred"), result
    assert obsolete.exists() is not deleted


def test_process_references_read_windows_separators(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Windows command line names the runtime with backslashes, which still identify it."""
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    command = "python " + runtime.as_posix().replace("/", "\\")
    monkeypatch.setattr(retirement, "process_commands", lambda *_a, **_k: command)

    assert runtime.resolve() in retirement.process_reference_paths(tmp_path)


@pytest.mark.skipif(os.name == "nt", reason="POSIX process listing")
def test_a_listing_can_leave_out_one_process(tmp_path: Path) -> None:
    """The exit reads every process but its own; the excluded one is absent, the rest remain."""
    marker = tmp_path / "marker"
    marker.mkdir()
    child = subprocess.Popen((sys.executable, "-c", "import time; time.sleep(60)", str(marker)))
    try:
        included = retirement.process_commands(tmp_path)
        excluded = retirement.process_commands(tmp_path, exclude_pid=child.pid)
    finally:
        child.kill()
        child.wait()

    assert str(marker) in included
    assert str(marker) not in excluded
    assert excluded.strip()


def _windows_rows(monkeypatch: pytest.MonkeyPatch, rows: list[SimpleNamespace]) -> None:
    """Answer the management query with exact rows, as WMI would on Windows."""
    query = SimpleNamespace(ExecQuery=lambda _text: rows)
    modules = {
        "pythoncom": SimpleNamespace(
            CoInitialize=lambda: None, CoUninitialize=lambda: None, com_error=OSError
        ),
        "win32com.client": SimpleNamespace(GetObject=lambda _moniker: query),
    }
    monkeypatch.setattr(process, "import_module", modules.__getitem__)


def test_windows_reads_an_unreadable_process_as_unknown_when_strict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A process whose command line Windows withholds may be using the runtime."""
    _windows_rows(
        monkeypatch,
        [
            SimpleNamespace(ProcessId=0, CommandLine=None),
            SimpleNamespace(ProcessId=4, CommandLine=None),
            SimpleNamespace(ProcessId=10, CommandLine="python run.py"),
            SimpleNamespace(ProcessId=11, CommandLine="self"),
            SimpleNamespace(ProcessId=12, CommandLine=None),
        ],
    )

    assert process.windows_command_lines(timeout=5) == ("python run.py", "self")
    assert process.windows_command_lines(timeout=5, exclude_pid=11) == ("python run.py",)
    with pytest.raises(process.ProcessExecutionError):
        process.windows_command_lines(timeout=5, strict=True)
