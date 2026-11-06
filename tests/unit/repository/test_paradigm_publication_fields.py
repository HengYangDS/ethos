"""Retired publication fields are reported and removed from carrier text alone."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.repair import paradigm_repair_plan
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

_BINDING = ".ethos/release.toml"
_WEB = "https://forge.test:8443/team/repo"
_FORGE = f'forge_repository = "{_WEB}"\n'
_PEERS = (
    '[[publication.peers]]\nid = "gitlab"\nprovider = "gitlab"\ngit_remote = "gitlab"\n'
    f'{_FORGE}capabilities = ["repository"]\n\n'
    '[[publication.peers]]\nid = "github"\nprovider = "github"\ngit_remote = "github"\n'
)
_RELEASE = (
    '[protected_refs]\ntags = ["v*"]\n\n# Publication peers.\n[publication]\n'
    'local_verification_command = "uv run nox -s check"\n'
    'local_installation_command = "uv run nox -s install"\n\n'
    f"{_PEERS}"
)
_REPAIRED = '[protected_refs]\ntags = ["v*"]\n\n# Publication peers.\n' + _PEERS.replace(_FORGE, "")
_FIELDS = (
    "publication.local_verification_command",
    "publication.local_installation_command",
    "publication.peers.gitlab.forge_repository",
)


def _gaps(root: Path, release: str) -> list[ParadigmGap]:
    """Report the conforming tree with one release binding and keep this obligation's gaps."""
    report = paradigm_report(root, {**CONFORMING, _BINDING: release})
    gaps = [ParadigmGap(**gap) for gap in report["gaps"]]
    return [gap for gap in gaps if gap.obligation == "publication-declaration"]


def test_each_retired_field_is_a_gap_naming_the_repair(tmp_path: Path) -> None:
    """Each field is its own carrier; the repair names the command and never the value."""
    gaps = _gaps(tmp_path, _RELEASE)
    assert [gap.carrier for gap in gaps] == [f"{_BINDING}:{field}" for field in _FIELDS]
    assert [gap.required_gap.split(":")[0] for gap in gaps] == [
        "repository_paradigm_publication_declaration"
    ] * 3
    assert all("ethos lane repair-paradigm --apply" in gap.repair for gap in gaps)
    assert _WEB not in repr(gaps)


def test_the_repair_is_pure_exact_and_idempotent(tmp_path: Path) -> None:
    """The plan reads only the carrier, keeps comments and peers, and repairs once."""
    plan = paradigm_repair_plan(tmp_path, _gaps(tmp_path, _RELEASE))
    assert [(edit.path, edit.before, edit.after) for edit in plan.edits] == [
        (_BINDING, _RELEASE, _REPAIRED)
    ]
    assert len(plan.repaired) == 3
    assert plan.actions == plan.report_only == ()
    assert _gaps(tmp_path, _REPAIRED) == []
    assert paradigm_repair_plan(tmp_path, _gaps(tmp_path, _REPAIRED)).edits == ()


def test_a_table_holding_only_commands_goes_with_its_comments(tmp_path: Path) -> None:
    """Without peers the emptied `[publication]` table goes, leaving zero peers."""
    release = (
        '[protected_refs]\ntags = ["v*"]\n\n# Local commands.\n[publication]\n'
        'local_verification_command = "check"\n'
    )
    plan = paradigm_repair_plan(tmp_path, _gaps(tmp_path, release))
    assert [edit.after for edit in plan.edits] == ['[protected_refs]\ntags = ["v*"]\n']
