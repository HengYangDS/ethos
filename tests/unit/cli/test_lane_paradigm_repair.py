"""Preview and apply paradigm repairs through the public lane command."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import ethos.adapters.mutation.carrier_edit as carrier_edit
import ethos.adapters.mutation.paradigm_repair as paradigm_repair
from ethos.adapters.admission.current.authority import observe_current_authority
from ethos.adapters.repo.git import run_git
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.paradigm import CONFORMING

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

_WRAPPED = "<!--\n---\nsubject: sample:guide\n---\n-->\n\n# Guide\n"
_RELEASE = (
    '[release]\nversion_source = "VERSION"\ntag_pattern = "v{version}"\n\n'
    '[[publication.peers]]\nid = "gitlab"\ngit_remote = "origin"\n'
)


def _repository(tmp_path: Path, changes: dict[str, str | None]) -> Path:
    """Track the conforming tree with changes in a fresh Git index."""
    repo = tmp_path / "repo"
    files = {**CONFORMING, **{path: text for path, text in changes.items() if text is not None}}
    for path in (path for path, text in changes.items() if text is None):
        files.pop(path)
    for relative, content in files.items():
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
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
