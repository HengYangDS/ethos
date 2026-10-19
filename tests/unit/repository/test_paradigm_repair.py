"""Deterministic repairs derived from repository paradigm gaps."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import tomli_w

from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.paradigm.repair import paradigm_repair_plan
from tests.support.paradigm import CONFORMING
from tests.support.paradigm import paradigm_report

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.paradigm.repair import RepairPlan

_RELEASE = (
    '[release]\nversion_source = "VERSION"\ntag_pattern = "v{version}"\n\n'
    '[[publication.peers]]\nid = "gitlab"\nprovider = "gitlab"\ngit_remote = "origin"\n'
    'capabilities = ["repository"]\n\n'
    '[[publication.peers]]\nid = "github"\nprovider = "github"\n'
)
_PRETTIER = ".config/checks/prettier/prettier.toml"
_TAPLO = ".config/checks/taplo/taplo.toml"
_EDITOR_DEFAULTS = "[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\n"
_WORKSPACE = ".ethos/workspace.toml"
_SCOPES = '[commit_policy]\nscopes = ["cli"]\n'


def _plan(root: Path, changes: dict[str, str | None]) -> tuple[RepairPlan, dict]:
    """Write the conforming tree with changes, None removing a carrier, then plan its repairs."""
    merged = {**CONFORMING, **changes}
    files = {path: text for path, text in merged.items() if text is not None}
    gaps = [ParadigmGap(**gap) for gap in paradigm_report(root, files)["gaps"]]
    return paradigm_repair_plan(root, gaps), files


def _apply(root: Path, plan: RepairPlan, files: dict[str, str], prefix: str = "") -> list[str]:
    """Write the planned edits, deleting removed carriers, and return the gaps left by prefix."""
    repaired = dict(files)
    for edit in plan.edits:
        if edit.after is None:
            repaired.pop(edit.path)
            (root / edit.path).unlink()
        else:
            repaired[edit.path] = edit.after
    gaps = paradigm_report(root, repaired)["required_gaps"]
    return [gap for gap in gaps if gap.startswith(prefix)]


def test_conforming_tree_plans_nothing(tmp_path: Path) -> None:
    """A conforming repository has neither an edit nor a report-only gap."""
    plan, _ = _plan(tmp_path, {})
    assert plan.edits == plan.repaired == plan.actions == plan.report_only == ()


def test_missing_normalization_carriers_are_created(tmp_path: Path) -> None:
    """Both normalization carriers are created with the shared rule and defaults."""
    plan, files = _plan(tmp_path, {".gitattributes": None, ".editorconfig": None})
    edits = {edit.path: edit for edit in plan.edits}
    assert edits[".gitattributes"].before is None
    assert edits[".gitattributes"].after == "* text=auto eol=lf\n"
    assert edits[".editorconfig"].after.startswith("root = true\n\n[*]\n")
    assert _apply(tmp_path, plan, files) == []


def test_missing_formatter_carriers_are_created_with_the_shared_settings(tmp_path: Path) -> None:
    """A missing carrier is written with the paradigm settings in their native tables."""
    plan, files = _plan(tmp_path, {_TAPLO: None, _PRETTIER: None})
    edits = {edit.path: edit.after for edit in plan.edits}
    assert edits[_TAPLO] == "[formatting]\ncolumn_width = 100\n"
    assert edits[_PRETTIER] == 'proseWrap = "preserve"\nprintWidth = 100\n'
    assert _apply(tmp_path, plan, files) == []


# Each repair edits or removes one carrier and leaves the repaired tree conforming.
_REPAIRS = {
    # The shared rule becomes the last catch-all pattern and earlier lines stay.
    "gitattributes-overridden": (
        ".gitattributes",
        "*.png binary\n* -text\n\n",
        "*.png binary\n* -text\n* text=auto eol=lf\n",
    ),
    "gitattributes-empty": (".gitattributes", "", "* text=auto eol=lf\n"),
    # The shared defaults land in [*], ahead of narrower sections that may refine them.
    "editorconfig-wrong-default": (
        ".editorconfig",
        "root = true\n\n[*]\ncharset = latin1\n\n[*.py]\nindent_size = 4\n",
        f"root = true\n\n{_EDITOR_DEFAULTS}\n[*.py]\nindent_size = 4\n",
    ),
    "editorconfig-narrower-only": (
        ".editorconfig",
        "root = true\n\n[*.py]\nindent_size = 4\n",
        f"root = true\n\n{_EDITOR_DEFAULTS}\n[*.py]\nindent_size = 4\n",
    ),
    "editorconfig-root": (".editorconfig", "root = true\n", f"root = true\n\n{_EDITOR_DEFAULTS}"),
    "editorconfig-blank": (".editorconfig", "\n", f"root = true\n\n{_EDITOR_DEFAULTS}"),
    # A wrong or missing setting is set without disturbing comments or other keys.
    "prettier-width": (
        _PRETTIER,
        '# shared width\nprintWidth = 80\nproseWrap = "preserve"\n',
        '# shared width\nprintWidth = 100\nproseWrap = "preserve"\n',
    ),
    "ruff-target": (
        ".config/checks/ruff/ruff.toml",
        "line-length = 100\n\n[lint]\nselect = []\n",
        'line-length = 100\ntarget-version = "py312"\n\n[lint]\nselect = []\n',
    ),
    "taplo-width": (
        _TAPLO,
        "[formatting]\nalign_entries = false\n\n[schema]\nenabled = false\n",
        "[formatting]\nalign_entries = false\ncolumn_width = 100\n\n[schema]\nenabled = false\n",
    ),
    "taplo-table": (
        _TAPLO,
        'include = ["**/*.toml"]\n',
        'include = ["**/*.toml"]\n\n[formatting]\ncolumn_width = 100\n',
    ),
    # The <!-- and --> lines go; the front matter and the body keep every byte.
    "front-matter-wrapped": (
        "docs/guide.md",
        "<!--\n---\nsubject: sample:guide\n---\n-->\n\n# Guide\n",
        "---\nsubject: sample:guide\n---\n\n# Guide\n",
    ),
    # The default mirror needs no declaration, so a binding that held only it goes.
    "independent-mirror": (
        _WORKSPACE,
        '# Branch roles.\n[branch_roles]\nrelease_mirror = "independent"\n',
        None,
    ),
    # Every header of an unread table goes; a binding left with nothing is removed.
    "legacy-schema": (
        _WORKSPACE,
        (
            '[workspace]\nmode = "monorepo"\n\n[packages.root]\npath = "."\n\n'
            '# Core.\n[packages.core]\npath = "packages/core"\n'
        ),
        None,
    ),
    # Either signing field goes; a binding left with nothing to declare is removed.
    "signature-alone": (
        _WORKSPACE,
        '# Signed commits.\n[commit_policy]\nsigning_required = false\nsigning_format = "ssh"\n',
        None,
    ),
    # The scopes the binding restricts stay with their table.
    "signature-beside-scopes": (
        _WORKSPACE,
        '[commit_policy]\nscopes = ["cli"]\nsigning_required = true\nsigning_format = "ssh"\n',
        _SCOPES,
    ),
}


@pytest.mark.parametrize(("path", "before", "after"), _REPAIRS.values(), ids=_REPAIRS)
def test_a_deterministic_repair_edits_only_its_carrier(
    tmp_path: Path, path: str, before: str, after: str | None
) -> None:
    """The plan edits or removes the one carrier, and the repaired tree reports no gap."""
    plan, files = _plan(tmp_path, {path: before})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(path, after)]
    assert _apply(tmp_path, plan, files) == []


def test_a_setting_that_cannot_be_rewritten_stays_report_only(tmp_path: Path) -> None:
    """A multi-line value would break the document, so the gap keeps its canonical repair."""
    plan, _ = _plan(tmp_path, {_PRETTIER: 'printWidth = [\n  80,\n]\nproseWrap = "preserve"\n'})
    assert plan.edits == ()
    assert [gap.carrier for gap in plan.report_only] == [f"{_PRETTIER}:printWidth"]


def test_an_untracked_carrier_is_tracked_rather_than_rewritten(tmp_path: Path) -> None:
    """A carrier present on disk but untracked needs `git add`, not new text."""
    report = paradigm_report(tmp_path, CONFORMING, untracked=(_TAPLO,))
    plan = paradigm_repair_plan(tmp_path, [ParadigmGap(**gap) for gap in report["gaps"]])
    assert plan.edits == ()
    assert plan.actions == (f"git add {_TAPLO}",)


@pytest.mark.parametrize(
    "text",
    [
        "# Guide\n",
        "<!--\n---\nsubject: sample:guide\n",
        "<!--\n---\nsubject: sample:guide\n---\n# Guide\n",
    ],
)
def test_front_matter_that_needs_authoring_stays_report_only(tmp_path: Path, text: str) -> None:
    """A document without a complete comment-wrapped block needs a written front matter."""
    plan, _ = _plan(tmp_path, {"docs/guide.md": text})
    assert plan.edits == ()
    assert [gap.obligation for gap in plan.report_only] == ["front-matter"]


def test_a_peer_remote_is_named_after_its_peer(tmp_path: Path) -> None:
    """The peer's git_remote changes and the local rename is the next action, not an effect."""
    plan, files = _plan(tmp_path, {".ethos/release.toml": _RELEASE, "VERSION": "1.0.0\n"})
    release = next(edit for edit in plan.edits if edit.path == ".ethos/release.toml")
    assert 'id = "gitlab"\nprovider = "gitlab"\ngit_remote = "gitlab"\n' in release.after
    assert 'id = "github"\ngit_remote = "github"\nprovider = "github"\n' in release.after
    assert plan.actions == ("git remote rename origin gitlab",)
    assert not _apply(tmp_path, plan, files, "repository_paradigm_peer_remote")


def test_a_peer_block_that_cannot_be_read_alone_stays_report_only(tmp_path: Path) -> None:
    """A block whose lines start like a table cannot be edited without guessing its end."""
    release = (
        '[[publication.peers]]\nid = "gitlab"\ngit_remote = "origin"\nmatrix = [\n  ["a"],\n]\n'
    )
    plan, _ = _plan(tmp_path, {".ethos/release.toml": release})
    assert plan.edits == ()
    assert [gap.obligation for gap in plan.report_only] == ["peer-remote"]


def test_gaps_without_a_deterministic_repair_stay_report_only(tmp_path: Path) -> None:
    """A gap that needs judgment, or a carrier the plan cannot read, keeps its repair text."""
    (tmp_path / ".gitattributes").write_bytes(b"\xff\xfe")
    gaps = [
        ParadigmGap("python-size", "src/sample/module.py", "split it"),
        ParadigmGap("text-normalization", ".gitattributes", "declare it"),
        ParadigmGap("formatter-binding", ".config/checks/eslint/eslint.config.mjs", "bind it"),
        ParadigmGap("formatter-binding", ".config/checks/unknown/unknown.toml", "bind it"),
        ParadigmGap("peer-remote", ".ethos/release.toml:publication.peers.absent", "rename it"),
    ]
    plan = paradigm_repair_plan(tmp_path, gaps)
    assert plan.edits == plan.repaired == plan.actions == ()
    assert plan.report_only == tuple(gaps)


def _workspace_plan(root: Path, workspace: str, gaps: list[ParadigmGap]) -> RepairPlan:
    """Plan repairs for the given gaps over one workspace binding."""
    (root / ".ethos").mkdir()
    (root / _WORKSPACE).write_text(workspace, encoding="utf-8")
    return paradigm_repair_plan(root, gaps)


def test_restated_standard_role_names_are_deleted(tmp_path: Path) -> None:
    """Standard role names go; the fields the paradigm leaves open and every comment stay."""
    workspace = (
        '# The native train.\n[branch_roles]\nrelease_branch = "main"\n'
        'accepted_branch = "dev"\nrelease_mirror = "accepted_ff"\n'
        'work_branch_prefix = "work/"\n\n[commit_policy]\nscopes = ["cli"]\n'
    )
    gaps = [
        ParadigmGap("branch-roles", f"{_WORKSPACE}:branch_roles.{role}", "remove it")
        for role in ("release_branch", "accepted_branch", "work_branch_prefix")
    ]
    plan = _workspace_plan(tmp_path, workspace, gaps)
    repaired = f'# The native train.\n[branch_roles]\nrelease_mirror = "accepted_ff"\n\n{_SCOPES}'
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, repaired)]
    assert plan.repaired == tuple(gaps)


def test_legacy_role_names_stay_until_closeout_renames_the_refs(tmp_path: Path) -> None:
    """A legacy name is still the ref closeout renames, so its gap stays report-only."""
    plan, _ = _plan(tmp_path, {_WORKSPACE: '[branch_roles]\naccepted_branch = "accepted/x"\n'})
    assert plan.edits == ()
    assert [gap.carrier for gap in plan.report_only] == [
        f"{_WORKSPACE}:branch_roles.accepted_branch"
    ]


def test_a_restated_shared_commit_grammar_is_deleted(tmp_path: Path) -> None:
    """A subject pattern equal to the shared grammar goes, and the report no longer names it."""
    grammar = load_repository_paradigm().commit.subject_pattern()
    policy = {"commit_policy": {"subject_pattern": grammar}}
    plan, files = _plan(tmp_path, {_WORKSPACE: tomli_w.dumps(policy)})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, None)]
    assert not _apply(tmp_path, plan, files, "repository_paradigm_commit_grammar")


def test_a_repository_commit_grammar_stays_report_only(tmp_path: Path) -> None:
    """A grammar of the repository's own needs judgment, so its gap keeps the canonical repair."""
    workspace = "[commit_policy]\nsubject_pattern = '^(feat|fix): .+'\n"
    plan, _ = _plan(tmp_path, {_WORKSPACE: workspace})
    assert plan.edits == ()
    assert [gap.obligation for gap in plan.report_only] == ["commit-grammar"]


@pytest.mark.parametrize(
    "workspace",
    [
        '[branch_roles]\nrelease_branch = "main"\nrelease_branch = "main"\n',
        'branch_roles.release_branch = "main"\n',
        '[branch_roles]\nnote = """\nrelease_branch = "x"\n"""\nrelease_branch = "main"\n',
    ],
)
def test_a_standard_name_the_plan_cannot_isolate_stays_report_only(
    tmp_path: Path, workspace: str
) -> None:
    """A field that is not one plain line of its own table, beside other fields, keeps its gap."""
    gap = ParadigmGap("branch-roles", f"{_WORKSPACE}:branch_roles.release_branch", "remove it")
    plan = _workspace_plan(tmp_path, workspace, [gap])
    assert plan.edits == ()
    assert plan.report_only == (gap,)


@pytest.mark.parametrize(
    "workspace",
    [
        '[branch_roles]\n"release\\u005fbranch" = "main"\n',
        '[branch_roles]\nrelease_branch = """\nmain"""\n',
    ],
)
def test_a_field_that_is_its_table_goes_with_the_table(tmp_path: Path, workspace: str) -> None:
    """Removing the only field removes its whole table block, however the field is written."""
    gap = ParadigmGap("branch-roles", f"{_WORKSPACE}:branch_roles.release_branch", "remove it")
    plan = _workspace_plan(tmp_path, workspace, [gap])
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, None)]
    assert plan.repaired == (gap,)


_RELEASE_BINDING = ".ethos/release.toml"
_PUBLICATION = '[publication]\nlocal_verification_command = "check"\n'


@pytest.mark.parametrize(
    ("release", "repaired"),
    [
        (None, '[release]\nmirror = "accepted_ff"\n'),
        (_PUBLICATION, f'{_PUBLICATION}\n[release]\nmirror = "accepted_ff"\n'),
        (
            f'[release]\nversion_source = "VERSION"\n\n{_PUBLICATION}',
            f'[release]\nversion_source = "VERSION"\nmirror = "accepted_ff"\n\n{_PUBLICATION}',
        ),
    ],
    ids=["no-release-binding", "no-release-table", "release-table"],
)
def test_an_accepted_mirror_moves_to_the_release_binding(
    tmp_path: Path, release: str | None, repaired: str
) -> None:
    """The mirror leaves the workspace with its emptied table and lands in `[release] mirror`."""
    workspace = (
        '[[package]]\nname = "root"\npath = "."\n\n'
        "# The native train keeps main release-facing.\n"
        f'[branch_roles]\nrelease_branch = "main"\nrelease_mirror = "accepted_ff"\n\n{_SCOPES}'
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace, _RELEASE_BINDING: release})
    edits = {edit.path: edit.after for edit in plan.edits}
    assert edits == {_WORKSPACE: _SCOPES, _RELEASE_BINDING: repaired}
    assert _apply(tmp_path, plan, files) == []


def test_an_unread_value_outside_a_table_header_stays_report_only(tmp_path: Path) -> None:
    """Only whole table blocks are deleted; an inline declaration keeps its gap."""
    workspace = 'package = { name = "root" }\n\n[commit_policy]\nscopes = ["cli"]\n'
    plan, _ = _plan(tmp_path, {_WORKSPACE: workspace})
    assert plan.edits == ()
    assert [gap.obligation for gap in plan.report_only] == ["workspace-binding"]


@pytest.mark.parametrize("value", ["true", "false"])
def test_the_retired_sibling_worktree_setting_is_deleted(tmp_path: Path, value: str) -> None:
    """No reader consults the setting, so either value goes and the report no longer names it."""
    workspace = (
        f"{_SCOPES}\n# Lanes live beside the repository.\n"
        f"[branch_roles]\ncanonical_sibling_worktrees = {value}\n"
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, _SCOPES)]
    assert not _apply(tmp_path, plan, files, "repository_paradigm_branch_roles")


def test_a_retired_field_the_binding_no_longer_declares_stays_report_only(tmp_path: Path) -> None:
    """A gap that names an absent field plans no edit."""
    carrier = f"{_WORKSPACE}:branch_roles.canonical_sibling_worktrees"
    gap = ParadigmGap("branch-roles", carrier, "remove it")
    plan = _workspace_plan(tmp_path, '[branch_roles]\nrelease_mirror = "independent"\n', [gap])
    assert plan.edits == ()
    assert plan.report_only == (gap,)
