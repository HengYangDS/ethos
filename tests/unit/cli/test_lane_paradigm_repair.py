"""Preview and apply paradigm repairs through the public lane command."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.carrier_edit as carrier_edit
import ethos.adapters.mutation.paradigm_repair as paradigm_repair
import ethos.application.lane.repair as lane_repair
from ethos.adapters.admission.current.authority import observe_current_authority
from ethos.adapters.repo.git import run_git
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.repository.paradigm.openspec import CONFIGURATION
from ethos.repository.release.identity import build_identity
from ethos.repository.release.pin import PIN_KEY
from ethos.repository.release.pin import bare_entry
from ethos.repository.release.pin import pin_line
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import write_tree
from tests.support.paradigm import CONFORMING

if TYPE_CHECKING:
    from pathlib import Path

_WRAPPED = "<!--\n---\nsubject: sample:guide\n---\n-->\n\n# Guide\n"
_RELEASE = (
    '[[publication.peers]]\nid = "gitlab"\ngit_remote = "origin"\n\n'
    '[[publication.peers]]\nid = "github"\ngit_remote = "github"\n'
)
_OLD, _NEW, _AHEAD = "0.2.0-beta.10", "0.2.0-beta.11", "0.2.0-beta.12"
_PROJECTION = ".config/checks/architecture-projection/policy.toml"
_MISE = CONFORMING[MISE_CONFIG]
# The table that a release published for adopters to paste, and the bare entry that replaces it.
_TABLE = (
    '[tools."http:ethos"]\nversion = "{}"\n\n[tools."http:ethos".platforms]\n'
    'linux-x64 = {{ url = "https://example.invalid/a", checksum = "sha256:aa" }}\n\n' + _MISE
)
_BARE = f'[tools]\n"{PIN_KEY}" = "{{}}"\n\n' + _MISE
_VERIFIED = "locked = true\nlocked_verify_provenance = true\n"
_MERGED = _MISE.replace("locked = true\n", _VERIFIED) + f"\n[tools]\n{pin_line(_NEW)}\n"
# The build that runs the command, the Mise configuration (None when the tree tracks none), its
# text after an apply (None when the apply leaves it), and the obligation that stays reported
# with words of its repair.
_PIN_TREES = {
    "older-form": (
        "release",
        _TABLE.format(_OLD),
        _MERGED,
        None,
    ),
    "older-bare-pin": (
        "release",
        _BARE.format(_OLD),
        _BARE.format(_NEW).replace("locked = true\n", _VERIFIED),
        None,
    ),
    "single-quoted-pin": (
        "release",
        _BARE.format(_OLD).replace('"', "'", 4),
        _BARE.format(_NEW).replace("locked = true\n", _VERIFIED),
        None,
    ),
    "no-pin": ("release", _MISE, _MERGED, None),
    "no-configuration": ("release", None, bare_entry(_NEW), None),
    "options-form": (
        "release",
        _BARE.format(_OLD).replace(f'"{_OLD}"', f"{{ version = '{_OLD}' }}"),
        None,
        ("runtime-pin", f"{_NEW}'s bare entry"),
    ),
    "two-forms": (
        "release",
        _TABLE.format(_OLD) + f"\n[tools]\n{pin_line(_OLD)}\n",
        None,
        ("runtime-pin", "one exact ETHOS pin"),
    ),
    "development-build": ("development", _BARE.format(_OLD), None, ("runtime-pin", "released")),
}


def _repository(tmp_path: Path, changes: dict[str, str | None]) -> Path:
    """Track the conforming tree with changes in a fresh Git index."""
    repo = tmp_path / "repo"
    files = {**CONFORMING, **{path: text for path, text in changes.items() if text is not None}}
    for path in (path for path, text in changes.items() if text is None):
        files.pop(path)
    write_tree(repo, files)
    subprocess.run(["git", "init", "-q", repo.as_posix()], check=True)
    subprocess.run(["git", "-C", repo.as_posix(), "add", "-A"], check=True)
    return repo


def _admission(verdict: str, calls: list[list[str]]) -> object:
    def guard(*, root: Path, paths: list[Path], **_options: object) -> dict[str, object]:
        calls.append(sorted(path.relative_to(root).as_posix() for path in paths))
        if verdict == "pass":
            branch = run_git(
                root, "symbolic-ref", "--short", "HEAD", observation=True
            ).stdout.strip()
            authority = observe_current_authority(
                root=root, branch=branch, actor="", required=False
            )
            return {
                "verdict": "pass",
                "required_gaps": [],
                "mutation_authority": authority.projection(),
            }
        return {
            "verdict": "block",
            "required_gaps": ["work_lane_required"],
            "next_action": "ethos lane start <name> --apply --json",
        }

    return guard


def test_preview_names_each_repair_and_writes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview shows each carrier's diff and the apply command, without admission."""
    repo = _repository(tmp_path, {".editorconfig": None, "docs/guide.md": _WRAPPED})
    calls: list[list[str]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", calls))
    data = run_ethos("lane", "repair-paradigm", "--root", repo.as_posix(), "--json")["data"]
    assert data["state"] == "planned"
    assert data["applied"] is False
    assert {edit["path"]: edit["created"] for edit in data["edits"]} == {
        ".editorconfig": True,
        "docs/guide.md": False,
    }
    assert "+root = true" in data["edits"][0]["diff"]
    assert data["next_action"] == "ethos lane repair-paradigm --apply --json"
    assert calls == []
    assert not (repo / ".editorconfig").exists()
    assert (repo / "docs/guide.md").read_text(encoding="utf-8") == _WRAPPED


def test_apply_writes_admitted_repairs_and_reports_what_remains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Apply admits the exact carriers, writes them and names the follow-up rename."""
    repo = _repository(
        tmp_path,
        {
            ".editorconfig": None,
            "docs/guide.md": _WRAPPED,
            ".ethos/release.toml": _RELEASE,
            "VERSION": "1.0.0\n",
        },
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", calls))
    data = run_ethos("lane", "repair-paradigm", "--apply", "--root", repo.as_posix(), "--json")[
        "data"
    ]
    assert calls == [[".editorconfig", ".ethos/release.toml", "docs/guide.md"]]
    assert data["state"] == "repaired"
    assert data["applied"] is True
    assert (repo / "docs/guide.md").read_text(encoding="utf-8").startswith("---\n")
    assert 'git_remote = "gitlab"' in (repo / ".ethos/release.toml").read_text(encoding="utf-8")
    assert not [
        gap
        for gap in data["remaining_gaps"]
        if gap.split(":")[0].endswith(("normalization", "front_matter", "peer_remote"))
    ]
    assert data["next_action"] == "git remote rename origin gitlab"


def test_refused_admission_writes_nothing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Outside an admitting Work Lane, apply blocks with the admission gaps."""
    repo = _repository(tmp_path, {".gitattributes": None})
    calls: list[list[str]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("block", calls))
    result = run_ethos_blocked(
        "lane", "repair-paradigm", "--apply", "--root", repo.as_posix(), "--json"
    )
    assert result["verdict"] == "block"
    assert result["required_gaps"] == ["work_lane_required"]
    assert result["data"]["state"] == "blocked"
    assert calls == [[".gitattributes"]]
    assert not (repo / ".gitattributes").exists()


def test_a_conforming_repository_needs_no_repair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without gaps, apply does nothing and asks for no admission."""
    repo = _repository(tmp_path, {})
    calls: list[list[str]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", calls))
    data = run_ethos("lane", "repair-paradigm", "--apply", "--root", repo.as_posix(), "--json")[
        "data"
    ]
    assert data["state"] == "conforming"
    assert data["next_action"] == ""
    assert calls == []


def test_a_gap_that_needs_judgment_leads_the_next_action(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A report-only gap plans no edit and its canonical repair becomes the next action."""
    repo = _repository(tmp_path, {"src/sample/module.py": "value = 1\n" * 600})
    calls: list[list[str]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", calls))
    data = run_ethos("lane", "repair-paradigm", "--root", repo.as_posix(), "--json")["data"]
    assert data["state"] == "report_only"
    assert data["edits"] == []
    assert [gap["obligation"] for gap in data["report_only"]] == ["code-size"]
    assert data["next_action"] == data["report_only"][0]["repair"]


def test_apply_removes_a_binding_left_with_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A workspace binding that held only a default mirror is previewed and applied as removed."""
    workspace = '[branch_roles]\nrelease_mirror = "independent"\n'
    repo = _repository(tmp_path, {".ethos/workspace.toml": workspace})
    calls: list[list[str]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", calls))
    preview = run_ethos("lane", "repair-paradigm", "--root", repo.as_posix(), "--json")["data"]
    assert [(edit["path"], edit["created"], edit["removed"]) for edit in preview["edits"]] == [
        (".ethos/workspace.toml", False, True)
    ]
    assert "+++ /dev/null" in preview["edits"][0]["diff"]
    data = run_ethos("lane", "repair-paradigm", "--apply", "--root", repo.as_posix(), "--json")[
        "data"
    ]
    assert calls == [[".ethos/workspace.toml"]]
    assert data["state"] == "repaired"
    assert not (repo / ".ethos/workspace.toml").exists()
    assert data["remaining_gaps"] == []


def test_apply_preserves_a_preimage_changed_during_admission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A passing admission cannot authorize overwriting intervening authoring bytes."""
    repo = _repository(tmp_path, {"docs/guide.md": _WRAPPED})
    guide = repo / "docs/guide.md"
    intervening = b"# Intervening author\n"

    def guard(**_options: object) -> dict[str, object]:
        guide.write_bytes(intervening)
        return _admission("pass", [])(**_options)

    monkeypatch.setattr(carrier_edit, "prewrite_guard", guard)
    result = paradigm_repair.repair_paradigm(root=repo, apply=True)

    assert result["verdict"] == "block", result
    assert guide.read_bytes() == intervening


def test_a_retired_forge_repository_goes_without_echoing_its_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Neither the preview nor the applied result repeats the removed web address."""
    web = "https://forge.test:8443/team/repo"
    release = (
        f'[[publication.peers]]\nid = "gitlab"\ngit_remote = "gitlab"\nforge_repository = "{web}"\n'
    )
    repo = _repository(tmp_path, {".ethos/release.toml": release})
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", []))
    preview = run_ethos("lane", "repair-paradigm", "--root", repo.as_posix(), "--json")
    applied = run_ethos("lane", "repair-paradigm", "--apply", "--root", repo.as_posix(), "--json")
    for result in (preview, applied):
        assert web not in json.dumps(result)
        assert "patch" not in result["data"]
    assert "-forge_repository = <withheld>" in preview["data"]["edits"][0]["diff"]
    carrier = ".ethos/release.toml:publication.peers.gitlab.forge_repository"
    assert applied["data"]["repaired_gaps"] == [
        f"repository_paradigm_publication_declaration:{carrier}"
    ]
    assert "forge_repository" not in (repo / ".ethos/release.toml").read_text(encoding="utf-8")
    again = run_ethos("lane", "repair-paradigm", "--root", repo.as_posix(), "--json")["data"]
    assert (again["state"], again["edits"]) == ("conforming", [])


def _upgrade(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, str | None],
    *,
    release: bool,
) -> tuple[Path, list[list[str]], tuple[str, ...]]:
    """Track a tree, run the command as one build of the new version and admit every path."""
    repo = _repository(tmp_path, changes)
    build = build_identity(
        product=_NEW, source_commit="a" * 40, source_tree="b" * 40, release=release
    )
    calls: list[list[str]] = []
    monkeypatch.setattr(lane_repair, "invoking_build_identity", lambda: build)
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _admission("pass", calls))
    return repo, calls, ("lane", "repair-paradigm", "--pin", "--root", repo.as_posix(), "--json")


@pytest.mark.parametrize(
    ("build", "before", "after", "reported"), _PIN_TREES.values(), ids=_PIN_TREES
)
def test_an_upgrade_declares_the_bare_entry_or_reports_the_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    build: str,
    before: str | None,
    after: str | None,
    reported: tuple[str, str] | None,
) -> None:
    """An older selection or none becomes the release's bare entry; any other stays as it is."""
    repo, _calls, arguments = _upgrade(
        tmp_path, monkeypatch, {MISE_CONFIG: before}, release=build == "release"
    )
    data = run_ethos(*arguments, "--apply")["data"]
    assert (repo / MISE_CONFIG).read_text(encoding="utf-8") == (after or before)
    obligation, repair = reported or ("", f"mise --cd {repo} lock")
    gaps = [gap["obligation"] for gap in data["report_only"] if gap["carrier"] == MISE_CONFIG]
    assert gaps == ([obligation] if reported else [])
    assert repair in data["next_action"]
    again = run_ethos(*arguments)["data"]
    assert (again["edits"], again["actions"]) == ([], [])


def test_an_upgrade_is_one_admitted_patch_and_names_the_steps_it_leaves(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The pin moves beside a common-rule repair; the relock and the projection stay named."""
    changes = {MISE_CONFIG: _TABLE.format(_OLD), CONFIGURATION: "schema: spec-driven\nrules:\n"}
    repo, calls, arguments = _upgrade(tmp_path, monkeypatch, changes, release=True)
    steps = [f"mise --cd {repo} lock", f"ethos lane project --root {repo} --json"]
    preview = run_ethos(*arguments)["data"]
    assert [edit["path"] for edit in preview["edits"]] == [MISE_CONFIG, CONFIGURATION]
    assert f"+{pin_line(_NEW)}" in preview["edits"][0]["diff"]
    assert (preview["next_action"], preview["actions"]) == (
        "ethos lane repair-paradigm --pin --apply --json",
        steps,
    )
    assert (calls, (repo / MISE_CONFIG).read_text(encoding="utf-8")) == ([], changes[MISE_CONFIG])
    applied = run_ethos(*arguments, "--apply")["data"]
    assert calls == [[MISE_CONFIG, CONFIGURATION]]
    assert applied["repaired_gaps"][0] == f"repository_paradigm_runtime_pin:{MISE_CONFIG}"
    assert (applied["state"], applied["next_action"], applied["actions"]) == (
        "repaired",
        steps[0],
        steps,
    )
    again = run_ethos(*arguments)["data"]
    assert (again["state"], again["edits"], again["actions"]) == ("conforming", [], [])
    undeclared = {MISE_CONFIG: _BARE.format(_OLD), _PROJECTION: None}
    plain, _calls, arguments = _upgrade(tmp_path / "plain", monkeypatch, undeclared, release=True)
    assert run_ethos(*arguments)["data"]["actions"] == [f"mise --cd {plain} lock"]


@pytest.mark.parametrize(
    "before", [_BARE.format(_AHEAD), _TABLE.format(_AHEAD)], ids=["bare-pin", "older-form"]
)
def test_an_upgrade_blocks_on_a_selection_of_a_newer_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, before: str
) -> None:
    """A pin moves up only: the request blocks by name, plans nothing and names its rerun."""
    changes = {MISE_CONFIG: before, ".editorconfig": None}
    repo, calls, arguments = _upgrade(tmp_path, monkeypatch, changes, release=True)
    rerun = f"mise --cd {repo} exec --locked -- {' '.join(('ethos', *arguments))}"
    for result in (run_ethos(*arguments), run_ethos_blocked(*arguments, "--apply")):
        assert (result["verdict"], result["required_gaps"], result["next_action"]) == (
            "block",
            [f"runtime_pin_ahead:{_AHEAD}"],
            rerun,
        )
    assert (calls, (repo / MISE_CONFIG).read_text(encoding="utf-8")) == ([], before)
    plain = run_ethos("lane", "repair-paradigm", "--root", repo.as_posix(), "--json")["data"]
    assert (plain["state"], [edit["path"] for edit in plain["edits"]]) == (
        "planned",
        [".editorconfig"],
    )
