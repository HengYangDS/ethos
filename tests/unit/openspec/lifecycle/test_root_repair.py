"""Exact supporting-template relocation repairs its own OpenSpec admission gap."""

from __future__ import annotations

import json
import shutil
from difflib import unified_diff
from pathlib import Path

import pytest

from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.openspec.lifecycle.root_repair import supporting_relocation_scope
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane

SOURCE = "openspec/specs/template.md"
TARGET = "openspec/schemas/local-spec-driven/templates/canonical-spec.md"
GUIDE = "README.md"
TEMPLATE = "# Canonical Specification Template\n\n## Purpose\n\nDescribe stable behavior.\n"


def _root_repair_repository(tmp_path: Path) -> Path:
    root = prepared_work_lane(tmp_path).worktree
    command = openspec_base_command(execution_probe=False)
    assert command is not None
    schema = Path(command[1]).resolve().parent.parent / "schemas/spec-driven"
    destination = root / "openspec/schemas/local-spec-driven"
    shutil.copytree(schema, destination)
    config = root / "openspec/config.yaml"
    config.write_text(
        config.read_text().replace("schema: spec-driven", "schema: local-spec-driven")
    )
    (root / SOURCE).write_text(TEMPLATE)
    (root / GUIDE).write_text(f"# Guide\n\n[Canonical template]({SOURCE}#purpose).\n")
    commit_fixture(root, "declare supporting template and its consumer")
    return root


def _patch(postimages: dict[str, tuple[str, str]]) -> str:
    return "".join(
        f"diff --git a/{path} b/{path}\n"
        + "".join(
            unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{path}" if before else "/dev/null",
                tofile=f"b/{path}" if after else "/dev/null",
            )
        )
        for path, (before, after) in postimages.items()
    )


def _relocation(root: Path, *, target: str = TARGET) -> dict[str, tuple[str, str]]:
    guide = (root / GUIDE).read_text()
    return {
        SOURCE: ((root / SOURCE).read_text(), ""),
        target: ("", (root / SOURCE).read_text()),
        GUIDE: (guide, guide.replace(SOURCE, target)),
    }


def _prewrite(root: Path, postimages: dict[str, tuple[str, str]], patch_file: Path):
    patch_file.write_text(_patch(postimages))
    result = run_ethos_raw(
        "lane",
        "prewrite",
        *postimages,
        "--editor-root",
        root.as_posix(),
        "--require-editor-root",
        "--patch",
        patch_file.as_posix(),
        "--json",
        cwd=root,
    )
    return json.loads(result.stdout)


def test_supporting_template_repair_has_exact_native_scope_without_mutation(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    head = git(root, "rev-parse", "HEAD")
    index = git(root, "write-tree")
    postimages = _relocation(root)
    report = _prewrite(root, postimages, tmp_path / "relocation.patch")

    assert report["verdict"] == "pass", report
    scope = report["data"]["material_scope"]
    assert scope["state"] == "openspec_supporting_file_relocation"
    assert set(scope["authorized_paths"]) == set(postimages)
    assert scope["changes"] == [
        {"name": "fixture-change", "path": "openspec/changes/fixture-change"}
    ]
    assert scope["removed_gaps"] == ["openspec_specs_root_entry_unexpected:template.md"]
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "write-tree") == index
    assert (root / SOURCE).read_text() == TEMPLATE
    assert not (root / TARGET).exists()
    assert (root / GUIDE).read_text() == postimages[GUIDE][0]


@pytest.mark.parametrize("mutation", ["content", "consumer", "destination", "extra"])
def test_supporting_template_repair_preserves_source_and_complete_reference_custody(
    tmp_path: Path, mutation: str
):
    root = _root_repair_repository(tmp_path)
    postimages = _relocation(root)
    if mutation == "content":
        postimages[TARGET] = ("", TEMPLATE + "Unrelated normative addition.\n")
    elif mutation == "consumer":
        postimages.pop(GUIDE)
    elif mutation == "destination":
        postimages = _relocation(root, target="docs/templates/canonical-spec.md")
    else:
        postimages["openspec/changes/fixture-change/tasks.md"] = (
            (root / "openspec/changes/fixture-change/tasks.md").read_text(),
            "## Tasks\n\n- [x] 1.1 Premature completion\n",
        )
    before = git(root, "status", "--porcelain=v1")
    report = _prewrite(root, postimages, tmp_path / "invalid.patch")
    assert report["verdict"] == "block", report
    assert git(root, "status", "--porcelain=v1") == before
    assert (root / SOURCE).read_text() == TEMPLATE


def test_supporting_relocation_repair_does_not_grant_ordinary_write(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    result = run_ethos_raw(
        "lane", "prewrite", SOURCE, "--editor-root", root.as_posix(), "--json", cwd=root
    )
    report = json.loads(result.stdout)
    assert result.returncode != 0
    assert report["verdict"] == "block"
    assert "openspec_specs_root_entry_unexpected:template.md" in report["required_gaps"]
    assert (root / SOURCE).read_text() == TEMPLATE


def test_exact_patch_report_binds_native_root_gap_reduction(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    postimages = _relocation(root)
    report = patch_admission(
        root=root,
        requested_paths=tuple(postimages),
        baseline_head=git(root, "rev-parse", "HEAD"),
        patch=_patch(postimages),
    )
    assert report["verdict"] == "pass", report
    repair = report["openspec_root_repair"]
    assert isinstance(repair, dict)
    assert repair["paths"] == sorted(postimages)
    assert repair["removed_gaps"] == ["openspec_specs_root_entry_unexpected:template.md"]
    assert repair["source"] == SOURCE
    assert repair["destination"] == TARGET


@pytest.mark.parametrize("coordinate", ["cli", "configuration", "gap", "change"])
def test_supporting_repair_requires_the_complete_current_native_observation(
    tmp_path: Path, coordinate: str
):
    root = _root_repair_repository(tmp_path)
    postimages = _relocation(root)
    report = _prewrite(root, postimages, tmp_path / "bound.patch")
    assert report["verdict"] == "pass", report
    data = report["data"]
    official = data["openspec"]
    if coordinate == "cli":
        official["official_cli"]["available"] = False
    elif coordinate == "configuration":
        official["official_config"]["input_digest"] = "stale"
    elif coordinate == "gap":
        official["required_gaps"].append("unrelated_governance_gap")
    else:
        official["commands"]["status"]["json"]["changeName"] = "other"
    scope = supporting_relocation_scope(
        role="work_lane",
        requested_paths=tuple(postimages),
        repair=data["patch_admission"]["openspec_root_repair"],
        official=official,
    )
    assert scope == {}


def test_supporting_move_preserves_reference_definitions_and_code_mentions(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    guide = (
        "# Guide\n\n[Canonical][template].\n\n"
        f"[template]: {SOURCE}#purpose\n\n"
        f"`{SOURCE}` is a historical mention, not a link.\n\n"
        "[Unrelated authored reference](unavailable-historical-input.md).\n"
    )
    (root / GUIDE).write_text(guide)
    commit_fixture(root, "declare native reference kinds")
    postimages = _relocation(root)
    postimages[GUIDE] = (guide, guide.replace(f"]: {SOURCE}", f"]: {TARGET}"))
    report = _prewrite(root, postimages, tmp_path / "native-reference.patch")
    assert report["verdict"] == "pass", report
    assert (root / GUIDE).read_text() == guide


def test_exact_relocation_does_not_reinterpret_unchanged_historical_commands(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    guide = (root / GUIDE).read_text() + "\n```sh\nplan inspect\n```\n"
    (root / GUIDE).write_text(guide)
    commit_fixture(root, "preserve authored historical command example")
    report = _prewrite(root, _relocation(root), tmp_path / "preserved-command.patch")
    assert report["verdict"] == "pass", report
    assert (root / GUIDE).read_text() == guide


def test_supporting_move_preserves_local_references_inside_the_template(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    template = TEMPLATE + "\n[Guidance](../../README.md).\n"
    (root / SOURCE).write_text(template)
    commit_fixture(root, "declare template-local destination")
    postimages = _relocation(root)
    postimages[TARGET] = ("", template.replace("../../README.md", "../../../../README.md"))
    report = _prewrite(root, postimages, tmp_path / "template-local-link.patch")
    assert report["verdict"] == "pass", report
    assert (root / SOURCE).read_text() == template


def test_supporting_move_rejects_unrelated_permission_changes(tmp_path: Path):
    root = _root_repair_repository(tmp_path)
    postimages = _relocation(root)
    patch_file = tmp_path / "mode-change.patch"
    patch_file.write_text(
        _patch(postimages).replace(
            f"diff --git a/{GUIDE} b/{GUIDE}\n",
            f"diff --git a/{GUIDE} b/{GUIDE}\nold mode 100644\nnew mode 100755\n",
        )
    )
    result = run_ethos_raw(
        "lane",
        "prewrite",
        *postimages,
        "--editor-root",
        root.as_posix(),
        "--patch",
        patch_file.as_posix(),
        "--json",
        cwd=root,
    )
    report = json.loads(result.stdout)
    assert result.returncode != 0
    assert report["verdict"] == "block", report
    assert (root / GUIDE).stat().st_mode & 0o777 == 0o644
