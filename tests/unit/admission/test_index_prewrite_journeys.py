"""Qualify native Lease, official intent and merge readers in index previews."""

from __future__ import annotations

from pathlib import Path

from ethos.adapters.admission.index_prewrite import index_patch_prewrite
from ethos.adapters.openspec.selection import preserved_incoming_change_paths
from ethos.adapters.repo.git import run_git
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane
from tests.support.openspec_lifecycle import native_merge_fixture


def test_public_index_journey_uses_real_lease_and_official_intent(tmp_path: Path) -> None:
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    source = root / "README.md"
    before = source.read_text(encoding="utf-8")
    # Produce an exact patch against the real index, then leave unrelated prose unstaged.
    source.write_text(before + "\nA selected addition.\n", encoding="utf-8")
    patch = git(root, "diff", "--", "README.md") + "\n"
    source.write_text(before + "\nUnrelated working prose.\n", encoding="utf-8")
    patch_path = tmp_path / "readme.patch"
    patch_path.write_text(patch, encoding="utf-8")
    index_path = run_git(
        root, "rev-parse", "--path-format=absolute", "--git-path", "index"
    ).stdout.strip()
    index_before = Path(index_path).read_bytes()
    report = run_ethos(
        "lane",
        "prewrite",
        "README.md",
        "--target",
        "index",
        "--patch",
        str(patch_path),
        "--editor-root",
        str(root),
        "--change",
        "fixture-change",
        "--json",
        cwd=root,
    )
    assert report["verdict"] == "pass", report
    assert Path(index_path).read_bytes() == index_before
    assert source.read_text(encoding="utf-8") == before + "\nUnrelated working prose.\n"


def test_isolated_index_tree_keeps_native_incoming_change_observable(tmp_path: Path) -> None:
    root = native_merge_fixture(tmp_path)
    readme = root / "README.md"
    readme.write_text("# Combined contribution\n", encoding="utf-8")
    git(root, "add", "README.md")
    readme.write_text("# Previewed contribution\n", encoding="utf-8")
    patch = git(root, "diff", "--", "README.md") + "\n"
    readme.write_text("# Unrelated working content\n", encoding="utf-8")
    before = Path(
        git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")
    ).read_bytes()
    paths = ("openspec/changes/static-delivery/tasks.md",)

    def evaluate(environment):
        tree = run_git(root, "write-tree", env=environment).stdout.strip()
        assert (
            preserved_incoming_change_paths(root, paths, tree_ref=tree, environment=environment)
            == paths
        )
        return {"verdict": "pass", "index_tree": tree}

    report = index_patch_prewrite(root, [readme], patch, evaluate)
    assert report["verdict"] == "pass", report
    assert (
        Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "index")).read_bytes()
        == before
    )
    assert readme.read_text() == "# Unrelated working content\n"
