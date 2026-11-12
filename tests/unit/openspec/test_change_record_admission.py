"""Prewrite admits a Change's declared `rebuild.toml` and refuses another Change's."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.gates.native.inputs import format_ownership
from ethos.adapters.openspec.lifecycle.scope import material_change_scope_report
from ethos.adapters.openspec.lifecycle.scope import official_change_bootstrap_scope_report
from ethos.adapters.openspec.lifecycle.scope import prospective_change_scope_report
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.normalization.coercion import string_sequence

if TYPE_CHECKING:
    from pathlib import Path

CHANGE = "history-rebuild-map"
RECORD = f"openspec/changes/{CHANGE}/rebuild.toml"


def _partial() -> dict[str, object]:
    """An official observation of one active Change whose design is ready and tasks are blocked."""
    artifacts = [
        {"id": "proposal", "outputPath": "proposal.md", "status": "done", "requires": []},
        {"id": "design", "outputPath": "design.md", "status": "ready", "requires": ["proposal"]},
        {"id": "tasks", "outputPath": "tasks.md", "status": "blocked", "requires": ["design"]},
    ]
    return {
        "official_cli": {"available": True},
        "commands": {"list": {"exit_code": 0, "json": {"changes": [{"name": CHANGE}]}}},
        "lifecycle": {"changes": [{"name": CHANGE, "artifacts": artifacts}]},
        "required_gaps": [f"openspec_status_incomplete:{CHANGE}"],
    }


def test_the_paradigm_declares_the_one_change_record() -> None:
    """The OpenSpec table names `rebuild.toml` as the record a Change holds beside its artifacts."""
    assert load_repository_paradigm().openspec.change_record == "rebuild.toml"


def test_partial_planning_admits_the_selected_changes_record(tmp_path: Path) -> None:
    """While planning is partial, the record joins the official outputs the Change may write."""
    scope = official_change_bootstrap_scope_report(
        root=tmp_path, official=_partial(), requested_paths=(RECORD,), requested_change=CHANGE
    )

    authorized = string_sequence(scope["authorized_paths"])
    assert (scope["verdict"], scope["required_gaps"]) == ("pass", [])
    assert {RECORD, f"openspec/changes/{CHANGE}/tasks.md"} <= set(authorized)


def test_complete_planning_attributes_the_record_to_its_change(tmp_path: Path) -> None:
    """Once planning is complete, the record is a material path of the selected Change."""
    (tmp_path / ".ethos").mkdir()
    profile = 'profile_id = "record"\n\n[openspec]\nmaterial_paths = ["**"]\n'
    (tmp_path / ".ethos/profile.toml").write_text(profile, encoding="utf-8")

    scope = material_change_scope_report(
        tmp_path, changed_paths=(RECORD,), active_change_names=(CHANGE,)
    )

    assert (scope["state"], scope["covered_paths"]) == (
        "attributed",
        [{"path": RECORD, "changes": [CHANGE]}],
    )


def test_another_changes_record_is_refused(tmp_path: Path) -> None:
    """A record in another Change's directory is that Change's, so the selection refuses it."""
    other = "openspec/changes/other-change/rebuild.toml"

    refused = prospective_change_scope_report((other,), CHANGE, root=tmp_path)
    bootstrap = official_change_bootstrap_scope_report(
        root=tmp_path, official=_partial(), requested_paths=(other,), requested_change=CHANGE
    )

    assert refused["required_gaps"] == [f"openspec_change_path_mismatch:{CHANGE}:{other}"]
    assert bootstrap == {}


def test_taplo_owns_the_record_and_its_archived_copy_is_immutable(tmp_path: Path) -> None:
    """The format and config gates format the record in an active Change and never once archived.

    The record's own row outranks the official OpenSpec owner of the Change's directory.
    """
    archived = f"openspec/changes/archive/2026-11-11-{CHANGE}/rebuild.toml"
    for path in (RECORD, archived):
        (tmp_path / path).parent.mkdir(parents=True)
        (tmp_path / path).write_text('version = 1\nid = "record"\n', encoding="utf-8")

    report = format_ownership(tmp_path, (RECORD, archived, f"openspec/changes/{CHANGE}/design.md"))

    owners = {
        item["path"]: (item["format_owner"], item["mutation_policy"])
        for item in report["assignments"]
    }
    assert report["verdict"] == "pass"
    assert owners == {
        RECORD: ("taplo", "native-formatter"),
        archived: ("immutable-carrier", "forbidden"),
        f"openspec/changes/{CHANGE}/design.md": ("official-openspec", "official-owner-only"),
    }
