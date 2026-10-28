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

GUARD = 'case "$1" in prepared) ;; *) exit 0 ;; esac\n'


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
    subprocess.run(["git", "init", "--quiet", str(repo)], check=True, timeout=30)
    digest = "a" * 64
    stub = repo / f".git/ethos/runtime/{digest}/python/bin/python"
    stub.parent.mkdir(parents=True)
    stub.write_text(f'#!/bin/sh\ncat >/dev/null\nprintf "%s\\n" "$6" >> "{log}"\n')
    stub.chmod(0o755)
    (repo / ".git/ethos/runtime/CURRENT").write_text(digest + "\n")
    hooks = repo / ".git/ethos/hooks/generation"
    hooks.mkdir(parents=True)
    launcher = hook_contract.load_hook_contract(platform_name="posix")["launchers"]
    (hooks / "reference-transaction").write_text(launcher["reference-transaction"])
    (hooks / "reference-transaction").chmod(0o755)
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


def test_declaration_without_states_keeps_its_launchers(tmp_path: Path) -> None:
    """An earlier runtime's declaration renders the launchers it always rendered."""
    declaration = Path(hook_contract.__file__).with_suffix(".toml")
    values = tomllib.loads(declaration.read_text(encoding="utf-8"))
    current = hook_contract.load_hook_contract(platform_name="posix")["launchers"]
    values.pop("phases", None)
    values["launcher"] = values["launcher"].replace("@GUARD@\n", "")
    earlier = tmp_path / "binding.toml"
    earlier.write_text(tomli_w.dumps(values), encoding="utf-8")
    rendered = hook_contract.load_hook_contract(earlier, platform_name="posix")["launchers"]
    assert GUARD in current["reference-transaction"]
    assert rendered["reference-transaction"] == current["reference-transaction"].replace(GUARD, "")
    assert current["reference-transaction"].index(GUARD) < current["reference-transaction"].index(
        "CURRENT="
    )
    assert {name: text for name, text in rendered.items() if name != "reference-transaction"} == {
        name: text for name, text in current.items() if name != "reference-transaction"
    }


@pytest.mark.parametrize(
    "defect", ["unknown-hook", "no-state", "state-name", "no-guard", "guard-only"]
)
def test_declared_states_follow_the_closed_grammar(tmp_path: Path, defect: str) -> None:
    """States name declared hooks, and the guard placeholder exists exactly when states do."""
    values = tomllib.loads(
        Path(hook_contract.__file__).with_suffix(".toml").read_text(encoding="utf-8")
    )
    if defect == "unknown-hook":
        values["phases"] = {"post-merge": ["prepared"]}
    elif defect == "no-state":
        values["phases"] = {"reference-transaction": []}
    elif defect == "state-name":
        values["phases"] = {"reference-transaction": ["prepared; exit 0"]}
    elif defect == "no-guard":
        values["launcher"] = values["launcher"].replace("@GUARD@\n", "")
    else:
        values.pop("phases", None)
    declaration = tmp_path / "binding.toml"
    declaration.write_text(tomli_w.dumps(values), encoding="utf-8")
    with pytest.raises(ValueError, match="hook_launcher_declaration_invalid"):
        hook_contract.load_hook_contract(declaration)


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
