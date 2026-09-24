"""Generation lifetime follows operational dependencies, not historical text."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

import ethos.adapters.repo.runtime.retirement as retirement
import ethos.adapters.repo.runtime.selection as selection
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.activation import materialize_hook_launchers
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import fixture_runtime_generation


def _tree(tmp_path: Path) -> tuple[Path, Path, Path]:
    repo = init_git_repo(tmp_path / "repo")
    common = Path(git_common_dir(repo))
    hooks, runtime = common / "ethos/hooks" / ("a" * 64), common / "ethos/runtime" / ("a" * 64)
    for path in (hooks, runtime):
        path.mkdir(parents=True)
        (path / "selected").write_bytes(b"selected immutable payload")
    (runtime.parent / "CURRENT").write_text(runtime.name + "\n", encoding="ascii")
    return repo, hooks, runtime


@pytest.mark.parametrize("relation", ["process", "config", "environment", "interpreter"])
def test_current_operational_dependency_retains_exact_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relation: str
) -> None:
    """All actual reference sources preserve the referenced generation bytes."""
    repo, hooks, runtime = _tree(tmp_path)
    needed = fixture_runtime_generation(runtime, "b" * 64)
    if relation == "process":
        monkeypatch.setattr(retirement, "process_commands", lambda _root: needed.as_posix())
    elif relation == "config":
        git(repo, "config", "alias.runtime", f"!{needed}/python --version")
    else:
        environment = repo / ".venv"
        environment.mkdir()
        if relation == "environment":
            (environment / "pyvenv.cfg").write_text(f"home = {needed}/python\n")
        else:
            (environment / "bin").mkdir()
            (environment / "bin/python").symlink_to(needed / "payload")
    original = (needed / "payload").read_bytes()

    for _ in range(2):
        result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)
        assert result["state"] == "complete", result
        assert needed.as_posix() in result["retained"]
        assert needed.as_posix() not in result["removed"]
        assert (needed / "payload").read_bytes() == original
        assert (runtime / "selected").read_bytes() == b"selected immutable payload"


def test_source_cleanup_preserves_another_repositorys_selected_runtime(tmp_path: Path) -> None:
    """A foreign CURRENT is a live consumer even when no source process uses it."""
    source, hooks, runtime = _tree(tmp_path / "source")
    old = fixture_runtime_generation(runtime, "foreign-legacy", repository_private=False)
    adopter = init_git_repo(tmp_path / "adopter")
    adopter_common = Path(git_common_dir(adopter))
    assert selection.activate_runtime(adopter_common, old).root == old
    result = retirement.retire_generations(source, hooks=hooks, runtime=runtime)

    assert selection.current_runtime(adopter_common).root == old
    assert old.as_posix() in result["retained"]
    assert result["unproven_removals"] == [old.as_posix()]


def test_a_later_generation_gets_a_fresh_consumer_observation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The first effect cannot authorize deletion after a new dependency appears."""
    repo, hooks, runtime = _tree(tmp_path)
    first, second = sorted(fixture_runtime_generation(runtime, letter * 64) for letter in "bc")
    active = ""
    remove = retirement.remove_generated_tree

    def remove_first(path: Path) -> None:
        nonlocal active
        assert path == first, "the newly referenced second generation was deleted"
        remove(path)
        active = second.as_posix()

    monkeypatch.setattr(retirement, "process_commands", lambda _root: active)
    monkeypatch.setattr(retirement, "remove_generated_tree", remove_first)

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["removed"] == [first.as_posix()]
    assert second.as_posix() in result["retained"]
    assert (second / "payload").read_text() in {"b" * 64, "c" * 64}


@pytest.mark.parametrize("failure", ["observation", "deletion", "after-deletion"])
def test_partial_cleanup_preserves_observed_effects_and_retries_freshly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str
) -> None:
    """A failure after one removal neither erases that effect nor repeats it."""
    repo, hooks, runtime = _tree(tmp_path)
    first, second = sorted(fixture_runtime_generation(runtime, letter * 64) for letter in "bc")
    remove = retirement.remove_generated_tree

    def observe(_root: Path) -> str:
        if failure == "observation" and not first.exists():
            message = "consumer observation unavailable"
            raise ValueError(message)
        return ""

    def remove_one(path: Path) -> None:
        if path == second and failure != "observation":
            if failure == "after-deletion":
                remove(path)
            message = "removal failed"
            raise OSError(message)
        remove(path)

    with monkeypatch.context() as patch:
        patch.setattr(retirement, "process_commands", observe)
        patch.setattr(retirement, "remove_generated_tree", remove_one)
        result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)
    gone = [first, second] if failure == "after-deletion" else [first]
    assert result["state"] == "deferred"
    assert result["removed"] == [str(path) for path in gone]
    assert result["deferred"] == ([] if failure == "after-deletion" else [str(second)])

    retried = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert retried["state"] == "complete"
    assert retried["removed"] == ([] if failure == "after-deletion" else [str(second)])
    assert not first.exists()
    assert not second.exists()


@pytest.mark.parametrize("drift", ["selector", "replacement"])
def test_cleanup_refuses_a_replaced_selection_or_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    """A fresh name is not the directory selected by an earlier admission."""
    repo, hooks, runtime = _tree(tmp_path)
    first, second = sorted(fixture_runtime_generation(runtime, letter * 64) for letter in "bc")
    remove = retirement.remove_generated_tree

    def first_effect(path: Path) -> None:
        assert path == first
        remove(path)
        if drift == "selector":
            (runtime.parent / "CURRENT").write_text(second.name + "\n")
        else:
            second.rename(tmp_path / "preserved-preimage")
            second.mkdir()
            (second / "payload").write_bytes(b"replacement")

    monkeypatch.setattr(retirement, "remove_generated_tree", first_effect)
    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "deferred"
    assert result["removed"] == [str(first)]
    assert second.is_dir()
    assert result["error"] == (
        "hook_runtime_current_stale"
        if drift == "selector"
        else "hook_runtime_generation_identity_stale"
    )


@pytest.mark.parametrize("invalidity", ["file", "symlink", "junction"])
def test_cleanup_rejects_unsafe_generation_roots_without_touching_referents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, invalidity: str
) -> None:
    repo, hooks, runtime = _tree(tmp_path)
    candidate = runtime.parent / ("b" * 64)
    if invalidity == "file":
        candidate.write_bytes(b"not an owned directory")
        sentinel = candidate
    else:
        external = tmp_path / "external"
        external.mkdir()
        sentinel = external / "payload"
        sentinel.write_bytes(b"external bytes")
        if invalidity == "symlink":
            candidate.symlink_to(external, target_is_directory=True)
        else:
            candidate.mkdir()
            monkeypatch.setattr(retirement, "is_junction", lambda path: path == candidate)
    before = sentinel.read_bytes()

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "deferred"
    assert result["error"] == "hook_runtime_generation_root_invalid"
    assert result["removed"] == []
    assert sentinel.read_bytes() == before


def test_missing_selected_hooks_cannot_authorize_any_reclamation(tmp_path: Path) -> None:
    """A lost selected resource fails before an unrelated generation is removed."""
    repo, hooks, runtime = _tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    (hooks / "selected").unlink()
    hooks.rmdir()
    hooks.parent.rmdir()

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "deferred", result
    assert result["removed"] == []
    assert (candidate / "payload").read_text() == "b" * 64


@pytest.mark.parametrize("fault", ["environment-file", "metadata-directory", "missing-worktree"])
def test_unreadable_binding_shape_does_not_become_an_absent_consumer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """Native shape failures defer deletion rather than silently discarding a binding."""
    repo, hooks, runtime = _tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    if fault == "environment-file":
        (repo / ".venv").write_bytes(b"not a readable environment")
    elif fault == "metadata-directory":
        (repo / ".venv/pyvenv.cfg").mkdir(parents=True)
    else:
        monkeypatch.setattr(
            retirement,
            "run_git",
            lambda _root, *args, **_kwargs: subprocess.CompletedProcess(
                args, 0, f"worktree {tmp_path / 'missing'}\0", ""
            ),
        )

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "deferred", result
    assert result["removed"] == []
    assert result["deferred"] == [candidate.as_posix()]
    assert (candidate / "payload").read_text() == "b" * 64


@pytest.mark.parametrize(
    "fault", ["exit", "stderr", "timeout", "common", "config", "worktrees", "binding"]
)
def test_unknown_operational_observation_defers_cleanup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    repo, hooks, runtime = _tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    if fault in {"exit", "stderr", "timeout"}:

        def observe(root, command, **kwargs):
            assert root == repo
            assert kwargs["timeout"] == 10
            if fault == "timeout":
                raise subprocess.TimeoutExpired(command, 10)
            return subprocess.CompletedProcess(
                command,
                1 if fault == "exit" else 0,
                "current process\n",
                "partial observation" if fault == "stderr" else "",
            )

        monkeypatch.setattr(retirement, "run_command", observe)
    elif fault == "common":

        def unavailable(_root):
            message = "common directory observation unavailable"
            raise ValueError(message)

        monkeypatch.setattr(retirement, "git_common_dir", unavailable)
    elif fault in {"config", "worktrees"}:
        native = retirement.run_git

        def read(root, *args, **kwargs):
            if args[0] == ("config" if fault == "config" else "worktree"):
                return subprocess.CompletedProcess(args, 2, "", "unavailable")
            return native(root, *args, **kwargs)

        monkeypatch.setattr(retirement, "run_git", read)
    else:
        (repo / ".venv").mkdir()
        (repo / ".venv/pyvenv.cfg").write_bytes(b"\xff")

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "deferred"
    assert result["removed"] == []
    if fault != "common":
        assert candidate.as_posix() in result["deferred"]
    assert (candidate / "payload").read_text() == "b" * 64


def test_retirement_waits_boundedly_for_a_real_native_selector_lock(tmp_path: Path) -> None:
    """Native contention defers deletion and a fresh retry uses the same lock inode."""
    repo, hooks, runtime = _tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    lock_path = runtime.parent.parent / "runtime-selection.lock"
    with selection.FileLock(lock_path, fallback_to_soft=False, preserve_lock_file=True):
        inode = lock_path.stat().st_ino
        started = time.monotonic()
        result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)
        elapsed = time.monotonic() - started
        assert result["state"] == "deferred", result
        assert result["error"] == "hook_runtime_selection_busy"
        assert result["removed"] == []
        assert (candidate / "payload").read_text() == "b" * 64
        assert 0 < elapsed < 20, elapsed
    assert lock_path.stat().st_ino == inode

    retried = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert retried["state"] == "complete", retried
    assert retried["removed"] == [candidate.as_posix()]
    assert lock_path.stat().st_ino == inode


@pytest.mark.parametrize("columns", ["32", "80"])
def test_live_native_process_keeps_generation_until_exit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, columns: str
) -> None:
    """Display width cannot hide a live dependency or keep it after process exit."""
    monkeypatch.setenv("COLUMNS", columns)
    repo, hooks, runtime = _tree(tmp_path)
    needed = fixture_runtime_generation(runtime, "b" * 64)
    ready = tmp_path / "process-ready"
    script = "import pathlib,sys; pathlib.Path(sys.argv[3]).write_text('ready'); sys.stdin.read(1)"
    with subprocess.Popen(
        [sys.executable, "-B", "-I", "-c", script, "padding" * 80, str(needed), str(ready)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as child:
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and child.poll() is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert ready.exists(), "owned process did not become ready"
            assert child.poll() is None
            result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)
            assert needed.as_posix() in result["retained"], result
            assert (needed / "payload").read_text() == "b" * 64
        finally:
            try:
                child.communicate("x", timeout=5)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate(timeout=5)
    assert child.returncode == 0
    released = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)
    assert released["state"] == "complete"
    assert released["removed"] == [needed.as_posix()]


def test_unowned_digest_directory_survives_unrelated_historical_carriers(
    tmp_path: Path,
) -> None:
    """Digest spelling grants no deletion ownership over a user's directory."""
    repo, hooks, runtime = _tree(tmp_path)
    unowned = runtime.parent / ("b" * 64)
    unowned.mkdir()
    (unowned / "payload").write_bytes(b"user content")
    history = runtime.parent.parent / "operations"
    history.mkdir()
    invalid = history / "unknown.bin"
    invalid.write_bytes(b"\xff\xfe" + unowned.as_posix().encode())
    preserved = tmp_path / "external-history"
    preserved.write_bytes(b"user history")
    (history / "external").symlink_to(preserved)

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "complete"
    assert result["removed"] == []
    assert unowned.is_dir()
    assert unowned.as_posix() in result["unproven_removals"]
    assert invalid.read_bytes() == b"\xff\xfe" + unowned.as_posix().encode()
    assert preserved.read_bytes() == b"user history"
    assert (history / "external").is_symlink()


@pytest.mark.parametrize("drift", ["content", "mode"])
def test_unowned_digest_hook_directory_survives_retirement(tmp_path: Path, drift: str) -> None:
    """A damaged or user-authored hook directory is not safe to reclaim."""
    repo, hooks, runtime = _tree(tmp_path)
    generated = materialize_hook_launchers(hooks.parent)
    unknown = hooks.parent / ("b" * 64) if drift == "content" else generated
    if drift == "content":
        unknown.mkdir()
        marker = unknown / "user-content"
        marker.write_bytes(b"preserve")
    else:
        marker = unknown / "pre-push"
        marker.chmod(0o644)
    original = marker.read_bytes()

    result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

    assert result["state"] == "complete", result
    assert marker.read_bytes() == original
    assert unknown.as_posix() in result["unproven_removals"]


@pytest.mark.parametrize("layout", ["plain", "with spaces", "O'Brien (native); owner"])
@pytest.mark.parametrize(
    "reference", ["exact", "launcher", "alias", "direct-alias", "foreign-root", "longer-name"]
)
def test_generation_reference_preserves_repository_and_path_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reference: str, layout: str
) -> None:
    """Equal digest spelling in another repository is not this runtime dependency."""
    repo, hooks, runtime = _tree(tmp_path / layout)
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


def test_unrelated_command_arguments_do_not_amplify_path_resolution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resolver work follows native path components, not all command suffix pairs."""
    repo, hooks, runtime = _tree(tmp_path)
    candidate = fixture_runtime_generation(runtime, "b" * 64)
    command = f"{candidate}/payload " + " ".join(f"/not-present-{i}/arg" for i in range(200))
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


def test_historical_runtime_observation_does_not_pin_an_executable_generation(
    tmp_path: Path,
) -> None:
    """Repeated history stays byte-exact without accumulating idle generations."""
    repo, hooks, runtime = _tree(tmp_path / "source")
    common = Path(git_common_dir(repo))
    records: dict[Path, bytes] = {}
    for ordinal, carrier in enumerate(("operations", "transactions", "ref-intent")):
        obsolete = fixture_runtime_generation(runtime, f"history-{ordinal}")
        history = common / "ethos" / carrier / f"{ordinal}.json"
        history.parent.mkdir(parents=True, exist_ok=True)
        records[history] = json.dumps({"runtime": str(obsolete), "ordinal": ordinal}).encode()
        history.write_bytes(records[history])

        result = retirement.retire_generations(repo, hooks=hooks, runtime=runtime)

        assert result["removed"] == [obsolete.as_posix()]
        assert not obsolete.exists(), "descriptive history kept an unused runtime alive"
        assert all(path.read_bytes() == content for path, content in records.items())
        assert {path.name for path in runtime.parent.iterdir() if path.is_dir()} == {runtime.name}
    assert retirement.retire_generations(repo, hooks=hooks, runtime=runtime)["removed"] == []


def test_repository_cleanup_preserves_external_supply(tmp_path):
    """Retire local copies without claiming deletion authority over installed bytes."""
    repo, hooks, runtime = _tree(tmp_path)
    external = tmp_path / "installed" / runtime.name
    external.parent.mkdir()
    runtime.rename(external)
    common = Path(git_common_dir(repo))
    (common / "ethos/runtime/CURRENT").write_text(f"{external.name}\n{external}\n")
    original = (external / "selected").read_bytes()
    result = retirement.retire_generations(repo, hooks=hooks, runtime=external)
    assert result["state"] == "complete", result
    assert str(external) in result["retained"]
    assert result["removed"] == []
    assert (external / "selected").read_bytes() == original
