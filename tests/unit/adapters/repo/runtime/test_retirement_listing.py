"""Process listings retain generations through native path identity, not command text."""

from __future__ import annotations

import errno
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import ethos.adapters.process as process_adapter
import ethos.adapters.repo.runtime.retirement as retirement
from tests.support.closed_directory import NEEDS_A_CLOSED_DIRECTORY
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
    deleted = listing == "deleted"
    if deleted:
        listed.mkdir()
    else:
        listed.symlink_to(tmp_path / "absent")
    ask = os.lstat

    def deleted_after_check(path: str | Path, **options: object) -> os.stat_result:
        found = ask(path, **options)
        if deleted and Path(path) == listed and listed.is_dir():
            listed.rmdir()
        return found

    monkeypatch.setattr(os, "lstat", deleted_after_check)
    monkeypatch.setattr(retirement, "process_commands", lambda _root: f"git -C {listed} status")

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == ("complete" if deleted else "deferred"), result
    assert obsolete.exists() is not deleted
    assert os.path.lexists(listed) is not deleted


@NEEDS_A_CLOSED_DIRECTORY
@pytest.mark.parametrize("listing", ["below", "alias", "link", "generation"])
def test_a_listed_path_that_cannot_be_looked_at_is_an_observed_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, listing: str
) -> None:
    """A name below a closed directory is absent, an alias of a generation too; a link is unknown.

    A generation that is closed itself is still retained: the walk records it before its inside.
    """
    repo, hooks, runtime = generation_tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    closed = candidate if listing == "generation" else tmp_path / "closed"
    (closed / "bin").mkdir(parents=True)
    (closed / "alias").symlink_to(candidate)
    link = tmp_path / "link"
    link.symlink_to(closed / "bin")
    listed = {"link": link, "alias": closed / "alias/payload"}.get(listing, closed / "bin/tool")
    monkeypatch.setattr(retirement, "process_commands", lambda _root: f"{listed} status")
    closed.chmod(0)
    try:
        result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)
    finally:
        closed.chmod(0o755)

    assert result["state"] == ("deferred" if listing == "link" else "complete"), result
    assert candidate.exists() is (listing in {"link", "generation"})
    assert (candidate.as_posix() in result["retained"]) is (listing == "generation")
    assert result["unproven_removals"] == []


def test_a_host_failure_at_a_listed_name_leaves_the_observation_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only no entry and no permission mean absent: an input error defers the reclamation."""
    repo, hooks, runtime = generation_tree(tmp_path)
    obsolete = fixture_runtime_generation(runtime, "history")
    listed = tmp_path / "listed"
    listed.mkdir()
    ask = os.lstat

    def failing(path: str | Path, **options: object) -> os.stat_result:
        if Path(path) == listed:
            raise OSError(errno.EIO, os.strerror(errno.EIO))
        return ask(path, **options)

    monkeypatch.setattr(os, "lstat", failing)
    monkeypatch.setattr(retirement, "process_commands", lambda _root: f"git -C {listed} status")

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "deferred", result
    assert obsolete.exists()


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


def _replace_process_lister(monkeypatch: pytest.MonkeyPatch, found: str | None) -> None:
    """Answer the lookup of `ps` alone; every other program resolves as the host resolves it."""
    native = process_adapter.shutil.which

    def resolve(name: str, **options: object) -> str | None:
        return found if name == "ps" else native(name, **options)

    monkeypatch.setattr(process_adapter.shutil, "which", resolve)


@pytest.mark.parametrize(
    "lister", ["exit 3", "echo unreadable >&2"], ids=["fails", "writes-errors"]
)
def test_a_failing_process_lister_leaves_consumers_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lister: str
) -> None:
    """A lister that fails or reports an error proves no generation unused, so none is removed."""
    repo, hooks, runtime = generation_tree(tmp_path / "repo")
    unused = fixture_runtime_generation(runtime, "b" * 64)
    native = tmp_path / "bin/ps"
    native.parent.mkdir()
    native.write_text(f"#!/bin/sh\n{lister}\n")
    native.chmod(0o700)
    _replace_process_lister(monkeypatch, native.as_posix())

    with pytest.raises(ValueError, match="hook_runtime_consumers_unknown"):
        retirement.process_commands(tmp_path)
    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert (result["state"], result["error"]) == ("deferred", "hook_runtime_consumers_unknown")
    assert result["removed"] == []
    assert unused.is_dir()


def test_a_host_without_a_process_lister_removes_no_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a lister on the host's default path the observation is refused, not read as empty."""
    repo, hooks, runtime = generation_tree(tmp_path / "repo")
    unused = fixture_runtime_generation(runtime, "b" * 64)
    _replace_process_lister(monkeypatch, None)

    with pytest.raises(ValueError, match="native_process_observer_unavailable"):
        retirement.process_commands(tmp_path)
    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert (result["state"], result["removed"]) == ("deferred", [])
    assert result["error"] == "native_process_observer_unavailable"
    assert unused.is_dir()
