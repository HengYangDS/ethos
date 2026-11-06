"""A rollback cannot select a runtime that refuses the root's repaired declaration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.repo.hook.activation as activation
import ethos.adapters.repo.hook.rollback as rollback
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.runtime.authority import RuntimeBuild
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

_TARGET = SimpleNamespace(build="predecessor", python=Path("/runtime/python/bin/python"))


def _probe(monkeypatch: pytest.MonkeyPatch, outcome: object) -> list[tuple[str, ...]]:
    """Replace only the target runtime's process; record each probe it was asked to run."""
    calls: list[tuple[str, ...]] = []
    native = rollback.process.run_command

    def run(root, command, **kwargs):
        if command[0] != str(_TARGET.python):
            return native(root, command, **kwargs)
        calls.append(tuple(command))
        assert (kwargs["stdin"], kwargs["check"]) == ("", False)
        if isinstance(outcome, BaseException):
            raise outcome
        return subprocess.CompletedProcess(command, 1, str(outcome), "")

    monkeypatch.setattr(rollback.process, "run_command", run)
    return calls


def _refusal(repo: Path) -> rollback.RollbackRefusalError:
    with pytest.raises(rollback.RollbackRefusalError) as refused:
        rollback.rollback_preflight(repo, _TARGET, invoking="successor")
    return refused.value


def test_a_rollback_onto_a_repaired_declaration_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The target's own publish names the refusal; activation gets the exact gap and restore."""
    repo = init_git_repo(tmp_path / "repo")
    payload = {"required_gaps": ["publication_topology_declaration_invalid"]}
    calls = _probe(monkeypatch, json.dumps(payload))
    refusal = _refusal(repo)
    assert (refusal.gap, refusal.next_action) == (
        "runtime_rollback_declaration_repaired",
        rollback.RESTORE_ACTION,
    )
    command = (str(_TARGET.python), "-B", "-I", "-m", "ethos.cli", "publish", "--root", str(repo))
    assert calls == [(*command, "--json")]


def test_a_restored_declaration_admits_the_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Any other refusal of the target's publish is its own concern, not a declaration mismatch."""
    repo = init_git_repo(tmp_path / "repo")
    _probe(monkeypatch, json.dumps({"required_gaps": ["proof_not_proven"]}))
    rollback.rollback_preflight(repo, _TARGET, invoking="successor")


def test_the_invoking_build_is_never_probed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reselecting the running build cannot change which declaration format it reads."""
    calls = _probe(monkeypatch, "")
    rollback.rollback_preflight(tmp_path, _TARGET, invoking="predecessor")
    assert calls == []


def test_a_root_behind_the_accepted_tip_refuses_before_probing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale lane's tree cannot stand for the declaration the accepted branch now holds."""
    repo = init_git_repo(tmp_path / "repo")
    stale = git(repo, "rev-parse", "HEAD")
    commit_fixture_file(repo, "accepted.txt", "accepted\n", "test: advance the accepted tip")
    git(repo, "checkout", "-q", "-b", "work/stale", stale)
    calls = _probe(monkeypatch, "")
    assert _refusal(repo).gap == "runtime_rollback_root_behind_accepted"
    assert calls == []


@pytest.mark.parametrize(
    "outcome",
    [
        "not json",
        json.dumps(["no", "result"]),
        json.dumps({"verdict": "block"}),
        OSError("gone"),
        subprocess.TimeoutExpired(("python",), 60),
    ],
    ids=["unparseable", "not-an-object", "no-gaps", "unstartable", "timeout"],
)
def test_a_probe_that_cannot_answer_blocks_with_its_own_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: object
) -> None:
    """An unknown answer never admits the rollback and never reads as a repaired declaration."""
    repo = init_git_repo(tmp_path / "repo")
    _probe(monkeypatch, outcome)
    assert _refusal(repo).gap == "runtime_rollback_probe_failed"


def test_a_refused_rollback_leaves_no_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Activation refuses before it materializes, pins or selects anything."""
    repo = init_git_repo(tmp_path / "repo")
    state = Path(git_common_dir(repo)) / "ethos"
    before = sorted(state.rglob("*")) if state.exists() else []
    monkeypatch.setattr(
        activation, "expected_runtime_build", lambda *_a, **_k: RuntimeBuild("predecessor", None)
    )
    monkeypatch.setattr(activation, "require_installed_runtime", lambda _runtime: _TARGET)
    monkeypatch.setattr(activation, "invoking_build_identity", lambda: "successor")
    monkeypatch.setattr(
        activation.runtime_materialization,
        "materialize_runtime",
        lambda *_a, **_k: pytest.fail("a refused rollback materialized its runtime"),
    )
    _probe(monkeypatch, json.dumps({"required_gaps": ["publication_topology_declaration_invalid"]}))
    with pytest.raises(rollback.RollbackRefusalError):
        activation.install_hook_launchers(repo, installed_runtime=tmp_path / "rollback")
    assert (sorted(state.rglob("*")) if state.exists() else []) == before
