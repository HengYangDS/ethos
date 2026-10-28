"""Only a reference transaction's prepared state starts the runtime or reaches ETHOS state."""

from __future__ import annotations

import hashlib
import os
import subprocess
import tomllib
from io import StringIO
from pathlib import Path

import pytest
import tomli_w

import ethos.adapters.repo.hook.binding as hook_contract
from ethos.adapters.repo.hook.protocol import execute_hook
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane

GUARD = '[ "@HOOK@" != reference-transaction ] || [ "$1" = prepared ] || exit 0\n'


def test_states_other_than_prepared_leave_no_ethos_trace(tmp_path: Path) -> None:
    """An ungoverned state succeeds and leaves state, journals and attestations alone."""
    root = prepared_work_lane(tmp_path).worktree
    common = Path(git(root, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    old = git(root, "rev-parse", "HEAD")
    new = git(root, "commit-tree", "HEAD^{tree}", "-p", old, "-m", "next")
    before = _snapshot(root, common)
    for phase in ("preparing", "committed", "aborted"):
        update = StringIO(f"{old} {new} refs/heads/work/feature\n")
        assert execute_hook(root, "reference-transaction", (phase,), stdin=update) == 0
        assert _snapshot(root, common) == before


@pytest.mark.skipif(os.name == "nt", reason="the stub runtime is a POSIX shell script")
def test_launcher_starts_the_runtime_only_for_prepared_states(tmp_path: Path) -> None:
    """One update-ref starts the runtime once, and a commit only for its prepared transactions."""
    repo, log = tmp_path / "repo", tmp_path / "starts.log"
    hooks = _repository(repo)
    digest = "a" * 64
    stub = repo / f".git/ethos/runtime/{digest}/python/bin/python"
    stub.parent.mkdir(parents=True)
    stub.write_text(f'#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" "$6" >> "{log}"\n')
    stub.chmod(0o755)
    (repo / ".git/ethos/runtime/CURRENT").write_text(digest + "\n")
    command = ["git", "-c", f"core.hooksPath={hooks}", "-c", "user.name=t", "-c", "user.email=t@t"]
    starts = []
    for operation in (
        ["commit", "--allow-empty", "--quiet", "-m", "one"],
        ["update-ref", "refs/heads/probe", "HEAD"],
    ):
        log.unlink(missing_ok=True)
        subprocess.run(
            [*command, *operation], cwd=repo, check=True, timeout=30, capture_output=True
        )
        starts.append(log.read_text().split())
    assert {phase for started in starts for phase in started} == {"prepared"}
    assert len(starts[1]) == 1


def test_guard_runs_through_gits_shell_before_the_runtime_selection(tmp_path: Path) -> None:
    """Git's own shell runs the guard on every platform, before any selector is read."""
    repo = tmp_path / "repo"
    hooks = _repository(repo)
    command = ["git", "-c", f"core.hooksPath={hooks}", "hook", "run", "reference-transaction"]
    for phase, succeeds in (("preparing", True), ("committed", True), ("prepared", False)):
        result = subprocess.run(
            [*command, "--", phase], cwd=repo, timeout=30, capture_output=True, check=False
        )
        assert (result.returncode == 0) == succeeds, (phase, result.stderr)


def test_earlier_template_without_the_guard_keeps_its_launchers(tmp_path: Path) -> None:
    """An earlier runtime's template renders the launchers it always rendered."""
    values = tomllib.loads(
        Path(hook_contract.__file__).with_suffix(".toml").read_text(encoding="utf-8")
    )
    current = hook_contract.load_hook_contract(platform_name="posix")["launchers"]
    assert values["launcher"].index(GUARD) < values["launcher"].index("CURRENT=")
    values["launcher"] = values["launcher"].replace(GUARD, "")
    earlier = tmp_path / "binding.toml"
    earlier.write_text(tomli_w.dumps(values), encoding="utf-8")
    rendered = hook_contract.load_hook_contract(earlier, platform_name="posix")["launchers"]
    assert rendered == {
        name: text.replace(GUARD.replace("@HOOK@", name), "") for name, text in current.items()
    }


def _repository(repo: Path) -> Path:
    """Create a repository whose only hook is the generated reference-transaction launcher."""
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=30)
    hooks = repo / ".git/ethos/hooks/generation"
    hooks.mkdir(parents=True)
    launcher = hooks / "reference-transaction"
    text = hook_contract.load_hook_contract()["launchers"]["reference-transaction"]
    launcher.write_text(text, encoding="utf-8", newline="\n")
    launcher.chmod(0o755)
    return hooks


def _snapshot(root: Path, common: Path) -> dict[str, str]:
    """Hash every file under the common ETHOS directory and every ref."""
    files = sorted(path for path in (common / "ethos").rglob("*") if path.is_file())
    refs = git(root, "for-each-ref", "--format=%(refname) %(objectname)")
    return {
        "refs": refs,
        **{
            path.relative_to(common).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        },
    }
