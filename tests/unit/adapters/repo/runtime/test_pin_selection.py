"""A transition follows the accepted pin forward only; a lane's receipt holds a departure."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.application.hook.installation as installation
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.repo.hook.rollback import RollbackRefusalError
from ethos.adapters.repo.runtime.pin_selection import follow_accepted_pin
from ethos.adapters.repo.runtime.pin_selection import receipt_departure
from ethos.adapters.repo.runtime.selection import activate_runtime
from ethos.adapters.repo.runtime.selection import require_selected_runtime
from ethos.application.adoption import adopt_repository
from ethos.application.catalog import invoke
from ethos.repository.release.identity import build_identity
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_tree
from tests.support.runtime_scenarios import fixture_runtime_generation
from tests.support.runtime_scenarios import mise_installs
from tests.support.runtime_scenarios import pinned_release_files

_RECEIPTED = "ethos hook install --runtime {} --reason <text> --root <lane> --json"
_INSTALL = "mise --cd {} install --locked"
_REPAIR = (
    "in a lane, declare one exact pin, lock it with its attestation (mise lock) and land both; "
    "a clone with nothing selected first binds a runtime: ethos hook install --runtime <runtime>"
)
_HTTP = '[tools."http:ethos"]\nversion = "9.3.0"\n'
_BARE = pinned_release_files("9.3.0", attested=False)
_BOTH = {path: text + _HTTP for path, text in pinned_release_files("9.3.0").items()}
CASES = [
    ("no-pin", "9.2.0", {}, "", "runtime_pin_absent", "invoking", ""),
    (
        "legacy-table",
        "9.2.0",
        {".config/mise/config.toml": _HTTP},
        "",
        "runtime_pin_absent",
        "invoking",
        "",
    ),
    ("newer", "9.2.0", pinned_release_files("9.3.0"), "9.3.0", "followed", "pinned", ""),
    (
        "its-dev-build",
        "9.3.0-dev",
        pinned_release_files("9.3.0"),
        "9.3.0",
        "followed",
        "pinned",
        "",
    ),
    (
        "older",
        "9.2.0",
        pinned_release_files("9.1.0"),
        "",
        "runtime_pin_behind_current",
        "kept",
        _RECEIPTED,
    ),
    (
        "same-unattested",
        "9.2.0",
        pinned_release_files("9.2.0", attested=False),
        "",
        "followed",
        "kept",
        "",
    ),
    (
        "checksum-class",
        "",
        pinned_release_files("0.1.0", attested=False),
        "0.1.0",
        "followed",
        "pinned",
        "",
    ),
    (
        "not-installed",
        "9.2.0",
        pinned_release_files("9.3.0"),
        "",
        "runtime_pin_not_installed",
        "kept",
        _INSTALL,
    ),
    (
        "not-installed-unselected",
        "",
        pinned_release_files("9.3.0"),
        "",
        "runtime_pin_not_installed",
        "refused",
        _INSTALL,
    ),
    ("no-provenance", "9.2.0", _BARE, "9.3.0", "runtime_pin_unattested", "kept", _REPAIR),
    ("no-provenance-unselected", "", _BARE, "9.3.0", "runtime_pin_unattested", "refused", _REPAIR),
    (
        "no-platform-entry",
        "9.2.0",
        pinned_release_files("9.3.0", platform="other-x64"),
        "9.3.0",
        "runtime_pin_unattested",
        "kept",
        _REPAIR,
    ),
    ("both-keys", "9.2.0", _BOTH, "9.3.0", "runtime_pin_ambiguous", "kept", _REPAIR),
]


def _release(store: Path, version: str) -> Path:
    """Create one release's runtime generation in a store: Mise's install or the repository's.

    A version that ends in `-dev` names a development build of it, which precedes the release.
    """
    store.mkdir(parents=True, exist_ok=True)
    product, source = (
        version.removesuffix("-dev"),
        {"source_commit": "a" * 40, "source_tree": "b" * 40},
    )
    build = build_identity(product=product, release=product == version, **source)
    return fixture_runtime_generation(store / "new", version, repository_private=False, build=build)


def _adopter(tmp_path: Path, current: str, files: dict[str, str]) -> tuple[Path, Path | None]:
    """A fixture adopter whose accepted branch holds `files` and whose `CURRENT` is one release."""
    repo = init_git_repo(tmp_path / "repo")
    write_tree(repo, {"fixture.txt": "", **files})
    commit_fixture(repo, "chore: declare the toolchain")
    git(repo, "worktree", "add", "-b", "work/depart", (tmp_path / "lane").as_posix(), "dev")
    common = Path(git_common_dir(repo)).resolve()
    selected = _release(common / "ethos/runtime", current) if current else None
    if selected is not None:
        activate_runtime(common, selected)
    return repo, selected


@pytest.mark.parametrize("case", CASES, ids=[case[0] for case in CASES])
def test_a_transition_follows_the_accepted_pin_forward_only(tmp_path, monkeypatch, case) -> None:
    """Each pin state names itself exactly, and only a newer installed pin moves the selection."""
    _name, current, files, installed, state, selects, action = case
    repo, selected = _adopter(tmp_path, current, files)
    release = _release(tmp_path / "mise/runtime", installed) if installed else None
    asked = mise_installs(monkeypatch, {installed: tmp_path / "mise"})
    action = action.format(selected if state == "runtime_pin_behind_current" else repo.as_posix())
    if selects == "refused":
        with pytest.raises(RollbackRefusalError) as refused:
            follow_accepted_pin(repo)
        assert (refused.value.gap, refused.value.next_action) == (state, action)
        return
    kept = selected if selects == "kept" else None
    selection = follow_accepted_pin(repo)
    assert selection == (state, release if selects == "pinned" else None, kept, action)
    assert selection.report() == {"state": state, "next_action": action}
    # ETHOS asks Mise only where it would select the pin; it installs and fetches nothing.
    assert bool(asked) is (selects == "pinned" or state == "runtime_pin_not_installed")


@pytest.mark.parametrize(
    ("chosen", "kind", "closure", "state"),
    [
        ("9.3.0", "successor", "retire", "runtime_pin_behind_current"),
        ("9.1.0", "rollback", "pin", "followed"),
    ],
)
def test_a_lane_receipt_holds_a_departure_until_the_pin_changes_or_the_lane_retires(
    tmp_path, monkeypatch, chosen, kind, closure, state
) -> None:
    """The receipt is read back as written, holds its runtime, and closes with its pin or lane."""
    repo, pinned = _adopter(tmp_path, "9.2.0", pinned_release_files("9.2.0"))
    common, lane = Path(git_common_dir(repo)).resolve(), tmp_path / "lane"
    target = require_selected_runtime(_release(common / "ethos/runtime", chosen))
    receipt = common / "ethos/receipts/runtime-selection/9.2.0.json"

    recorded = receipt_departure(lane, target, "a reason")

    assert recorded == json.loads(receipt.read_bytes())
    assert recorded == {
        "kind": kind,
        "pin": "9.2.0",
        "selected": chosen,
        "runtime_digest": target.digest,
        "lane": "work/depart",
        "reason": "a reason",
    }
    # A receipt holds only the runtime it names: until that is selected, the pin still decides.
    # Only a transition deletes a closed receipt; a preview reads it and leaves it. The pin is
    # the accepted branch's, whatever a lane's own tree declares.
    write_tree(lane, pinned_release_files("9.9.0"))
    assert (follow_accepted_pin(lane).kept, receipt.exists()) == (pinned, True)
    assert (follow_accepted_pin(repo, settle=True).kept, receipt.exists()) == (pinned, False)
    receipt_departure(lane, target, "a reason")
    activate_runtime(common, target.root)
    assert follow_accepted_pin(repo)[::2] == ("runtime_selection_open", target.root)
    if closure == "retire":
        git(repo, "worktree", "remove", "--force", lane.as_posix())
        git(repo, "branch", "-D", "work/depart")
    else:
        write_tree(repo, pinned_release_files("9.3.0"))
        commit_fixture(repo, "chore: bump the pin")
        _release(tmp_path / "mise/runtime", "9.3.0")
    mise_installs(monkeypatch, {"9.3.0": tmp_path / "mise"})
    assert (follow_accepted_pin(repo, settle=True).state, receipt.exists()) == (state, False)


@pytest.mark.parametrize(
    ("files", "root", "reason", "refused"),
    [
        (pinned_release_files("9.2.0"), "repo", "a reason", True),
        (pinned_release_files("9.3.0"), "repo", "", False),
        ({}, "repo", "", False),
    ],
    ids=["not-a-lane", "the-pinned-release", "no-pin"],
)
def test_only_a_departure_needs_a_reason_from_a_lane(
    tmp_path, files, root, reason, refused
) -> None:
    """Selecting the pinned release, or any release without a pin, departs from nothing."""
    repo, _selected = _adopter(tmp_path, "", files)
    target = require_selected_runtime(_release(tmp_path / "mise/runtime", "9.3.0"))
    if refused:
        with pytest.raises(RollbackRefusalError, match="runtime_selection_receipt_required") as no:
            receipt_departure(tmp_path / root, target, reason)
        assert no.value.next_action == _RECEIPTED.format(target.root)
    else:
        assert receipt_departure(tmp_path / root, target, reason) == {}
    assert not (Path(git_common_dir(repo)) / "ethos/receipts").exists()


def test_adoption_and_the_install_command_read_the_same_pin(tmp_path, monkeypatch) -> None:
    """`adopt --select-runtime` plans no unattested selection; `hook install` carries `--reason`."""
    repo, _selected = _adopter(tmp_path, "", _BARE)
    plan = adopt_repository(repo, select_runtime=True)
    assert "runtime_pin_unattested" in plan.required_gaps
    assert plan.data["runtime_selection"]["next_action"] == _REPAIR
    assert not (Path(git_common_dir(repo)) / "ethos/runtime/CURRENT").exists()
    # With the pin attested and installed, the plan binds the pinned install's build.
    write_tree(repo, pinned_release_files("9.3.0"))
    commit_fixture(repo, "chore: lock the pin")
    _release(tmp_path / "mise/runtime", "9.3.0")
    mise_installs(monkeypatch, {"9.3.0": tmp_path / "mise"})
    bound = adopt_repository(repo, select_runtime=True).data["runtime_selection"]
    assert (bound["runtime_pin"]["state"], bound["source_commit"]) == ("followed", "a" * 40)
    seen: dict[str, object] = {}
    binding = {"hooks_path": "", "python": "", "current": True, "required_gaps": []}
    monkeypatch.setattr(
        installation, "install_hook_launchers", lambda _root, **named: seen.update(named) or binding
    )
    result = invoke("hook install", repo, {"installed_runtime": "/runtime", "reason": "defect"})
    assert (seen["reason"], result.verdict, result.next_action) == ("defect", "pass", "")
    # An installation that leaves the accepted pin unselected names what settles the pin.
    binding["runtime_pin"] = {"state": "runtime_pin_unattested", "next_action": _REPAIR}
    kept = invoke("hook install", repo, {"installed_runtime": "/runtime", "reason": "defect"})
    assert (kept.verdict, kept.next_action) == ("pass", _REPAIR)
    assert kept.to_dict()["next"]["kind"] != "done"
