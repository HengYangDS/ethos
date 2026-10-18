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


def _plan(root: Path, changes: dict[str, str | None]) -> tuple[RepairPlan, dict]:
    """Write the conforming tree with changes, then plan repairs for its report."""
    files = {**CONFORMING, **{path: text for path, text in changes.items() if text is not None}}
    for path in (path for path, text in changes.items() if text is None):
        files.pop(path, None)
    report = paradigm_report(root, files)
    gaps = [ParadigmGap(**gap) for gap in report["gaps"]]
    return paradigm_repair_plan(root, gaps), files


def _apply(root: Path, plan: RepairPlan, files: dict[str, str]) -> dict:
    """Write the planned edits, deleting removed carriers, and re-evaluate the repaired tree."""
    repaired = dict(files)
    for edit in plan.edits:
        if edit.after is None:
            repaired.pop(edit.path)
            (root / edit.path).unlink()
        else:
            repaired[edit.path] = edit.after
    return paradigm_report(root, repaired)


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
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("*.png binary\n* -text\n\n", "*.png binary\n* -text\n* text=auto eol=lf\n"),
        ("", "* text=auto eol=lf\n"),
    ],
)
def test_gitattributes_ends_with_the_shared_rule(tmp_path: Path, before: str, after: str) -> None:
    """The shared rule becomes the last catch-all pattern and earlier lines stay."""
    plan, files = _plan(tmp_path, {".gitattributes": before})
    assert [edit.after for edit in plan.edits] == [after]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (
            "root = true\n\n[*]\ncharset = latin1\n\n[*.py]\nindent_size = 4\n",
            (
                "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\n"
                "insert_final_newline = true\n\n[*.py]\nindent_size = 4\n"
            ),
        ),
        (
            "root = true\n\n[*.py]\nindent_size = 4\n",
            (
                "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\n"
                "insert_final_newline = true\n\n[*.py]\nindent_size = 4\n"
            ),
        ),
        (
            "root = true\n",
            "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\n",
        ),
        (
            "\n",
            "root = true\n\n[*]\ncharset = utf-8\nend_of_line = lf\ninsert_final_newline = true\n",
        ),
    ],
)
def test_editorconfig_defaults_apply_to_every_file(tmp_path: Path, before: str, after: str) -> None:
    """The shared defaults land in [*], ahead of narrower sections that may refine them."""
    plan, files = _plan(tmp_path, {".editorconfig": before})
    assert [edit.after for edit in plan.edits] == [after]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


def test_missing_formatter_carriers_are_created_with_the_shared_settings(tmp_path: Path) -> None:
    """A missing carrier is written with the paradigm settings in their native tables."""
    missing = (".config/checks/taplo/taplo.toml", ".config/checks/prettier/prettier.toml")
    plan, files = _plan(tmp_path, dict.fromkeys(missing))
    edits = {edit.path: edit.after for edit in plan.edits}
    assert edits[missing[0]] == "[formatting]\ncolumn_width = 100\n"
    assert edits[missing[1]] == 'proseWrap = "preserve"\nprintWidth = 100\n'
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


@pytest.mark.parametrize(
    ("path", "before", "after"),
    [
        (
            ".config/checks/prettier/prettier.toml",
            '# shared width\nprintWidth = 80\nproseWrap = "preserve"\n',
            '# shared width\nprintWidth = 100\nproseWrap = "preserve"\n',
        ),
        (
            ".config/checks/ruff/ruff.toml",
            "line-length = 100\n\n[lint]\nselect = []\n",
            'line-length = 100\ntarget-version = "py312"\n\n[lint]\nselect = []\n',
        ),
        (
            ".config/checks/taplo/taplo.toml",
            "[formatting]\nalign_entries = false\n\n[schema]\nenabled = false\n",
            (
                "[formatting]\nalign_entries = false\ncolumn_width = 100\n"
                "\n[schema]\nenabled = false\n"
            ),
        ),
        (
            ".config/checks/taplo/taplo.toml",
            'include = ["**/*.toml"]\n',
            'include = ["**/*.toml"]\n\n[formatting]\ncolumn_width = 100\n',
        ),
    ],
)
def test_formatter_settings_are_set_in_place(
    tmp_path: Path, path: str, before: str, after: str
) -> None:
    """A wrong or missing setting is set without disturbing comments or other keys."""
    plan, files = _plan(tmp_path, {path: before})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(path, after)]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


def test_a_setting_that_cannot_be_rewritten_stays_report_only(tmp_path: Path) -> None:
    """A multi-line value would break the document, so the gap keeps its canonical repair."""
    path = ".config/checks/prettier/prettier.toml"
    plan, _ = _plan(tmp_path, {path: 'printWidth = [\n  80,\n]\nproseWrap = "preserve"\n'})
    assert plan.edits == ()
    assert [gap.carrier for gap in plan.report_only] == [f"{path}:printWidth"]


def test_an_untracked_carrier_is_tracked_rather_than_rewritten(tmp_path: Path) -> None:
    """A carrier present on disk but untracked needs `git add`, not new text."""
    path = ".config/checks/taplo/taplo.toml"
    report = paradigm_report(tmp_path, CONFORMING, untracked=(path,))
    plan = paradigm_repair_plan(tmp_path, [ParadigmGap(**gap) for gap in report["gaps"]])
    assert plan.edits == ()
    assert plan.actions == (f"git add {path}",)


def test_wrapped_front_matter_loses_only_its_comment_lines(tmp_path: Path) -> None:
    """The <!-- and --> lines go; the front matter and the body keep every byte."""
    document = "docs/guide.md"
    wrapped = "<!--\n---\nsubject: sample:guide\n---\n-->\n\n# Guide\n"
    plan, files = _plan(tmp_path, {document: wrapped})
    assert [(edit.path, edit.after) for edit in plan.edits] == [
        (document, "---\nsubject: sample:guide\n---\n\n# Guide\n")
    ]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


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
    assert not [
        gap
        for gap in _apply(tmp_path, plan, files)["required_gaps"]
        if gap.startswith("repository_paradigm_peer_remote")
    ]


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


_WORKSPACE = ".ethos/workspace.toml"


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
    repaired = (
        '# The native train.\n[branch_roles]\nrelease_mirror = "accepted_ff"\n\n'
        '[commit_policy]\nscopes = ["cli"]\n'
    )
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
    assert not [
        gap
        for gap in _apply(tmp_path, plan, files)["required_gaps"]
        if gap.startswith("repository_paradigm_commit_grammar")
    ]


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


def test_an_independent_mirror_and_its_emptied_binding_are_deleted(tmp_path: Path) -> None:
    """The default mirror needs no declaration, so a binding that held only it goes."""
    workspace = '# Branch roles.\n[branch_roles]\nrelease_mirror = "independent"\n'
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, None)]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


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
        '[branch_roles]\nrelease_branch = "main"\nrelease_mirror = "accepted_ff"\n\n'
        '[commit_policy]\nscopes = ["cli"]\n'
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace, _RELEASE_BINDING: release})
    assert {edit.path: edit.after for edit in plan.edits} == {
        _WORKSPACE: '[commit_policy]\nscopes = ["cli"]\n',
        _RELEASE_BINDING: repaired,
    }
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


def test_an_unread_legacy_schema_is_deleted_with_its_sub_tables(tmp_path: Path) -> None:
    """Every header of an unread table goes; a binding left with nothing is removed."""
    workspace = (
        '[workspace]\nmode = "monorepo"\n\n[packages.root]\npath = "."\n\n'
        '# Core.\n[packages.core]\npath = "packages/core"\n'
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, None)]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


def test_an_unread_value_outside_a_table_header_stays_report_only(tmp_path: Path) -> None:
    """Only whole table blocks are deleted; an inline declaration keeps its gap."""
    workspace = 'package = { name = "root" }\n\n[commit_policy]\nscopes = ["cli"]\n'
    plan, _ = _plan(tmp_path, {_WORKSPACE: workspace})
    assert plan.edits == ()
    assert [gap.obligation for gap in plan.report_only] == ["workspace-binding"]


@pytest.mark.parametrize("value", ["true", "false"])
def test_the_retired_sibling_worktree_setting_is_deleted(tmp_path: Path, value: str) -> None:
    """No reader consults the setting, so either value goes and the report no longer names it."""
    kept = '[commit_policy]\nscopes = ["cli"]\n'
    workspace = (
        f"{kept}\n# Lanes live beside the repository.\n"
        f"[branch_roles]\ncanonical_sibling_worktrees = {value}\n"
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, kept)]
    assert not [
        gap
        for gap in _apply(tmp_path, plan, files)["required_gaps"]
        if gap.startswith("repository_paradigm_branch_roles")
    ]


def test_a_retired_field_the_binding_no_longer_declares_stays_report_only(tmp_path: Path) -> None:
    """A gap that names an absent field plans no edit."""
    carrier = f"{_WORKSPACE}:branch_roles.canonical_sibling_worktrees"
    gap = ParadigmGap("branch-roles", carrier, "remove it")
    plan = _workspace_plan(tmp_path, '[branch_roles]\nrelease_mirror = "independent"\n', [gap])
    assert plan.edits == ()
    assert plan.report_only == (gap,)


def test_a_restated_signature_and_its_emptied_binding_are_deleted(tmp_path: Path) -> None:
    """Either signing field goes; a binding left with nothing to declare is removed."""
    workspace = (
        '# Signed commits.\n[commit_policy]\nsigning_required = false\nsigning_format = "ssh"\n'
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace})
    assert [(edit.path, edit.after) for edit in plan.edits] == [(_WORKSPACE, None)]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []


def test_a_restated_signature_is_deleted_beside_declared_scopes(tmp_path: Path) -> None:
    """The scopes the binding restricts stay with their table."""
    workspace = (
        '[commit_policy]\nscopes = ["cli"]\nsigning_required = true\nsigning_format = "ssh"\n'
    )
    plan, files = _plan(tmp_path, {_WORKSPACE: workspace})
    assert [(edit.path, edit.after) for edit in plan.edits] == [
        (_WORKSPACE, '[commit_policy]\nscopes = ["cli"]\n')
    ]
    assert _apply(tmp_path, plan, files)["required_gaps"] == []
