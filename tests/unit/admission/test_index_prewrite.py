"""Qualify exact index previews through native Git, intent and staged custody."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import ethos.adapters.admission.index_prewrite as index_prewrite
import ethos.adapters.admission.prewrite as prewrite
from ethos.adapters.openspec.selection import preserved_incoming_change_paths
from ethos.adapters.repo.git import run_git
from ethos.adapters.store.state.lease.projection import lease_rows
from ethos.adapters.store.state.schema import state_database
from tests.support.ethos_cli_runner import full_result
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import write_active_commitment

PATCH = (
    "diff --git a/module.py b/module.py\n--- a/module.py\n+++ b/module.py\n"
    "@@ -1 +1 @@\n-VALUE = 2\n+VALUE = 3\n"
)


@pytest.fixture
def mixed_lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "unrelated.py").write_text("OTHER = 1\n", encoding="utf-8")
    (root / "outside/hidden.py").parent.mkdir()
    (root / "outside/hidden.py").write_text("HIDDEN = 1\n", encoding="utf-8")
    commit_fixture(root, "test: prepare index source")
    write_active_commitment(fixture.candidate, change_id="static-delivery")
    commit_fixture(fixture.candidate, "test: incoming intent")
    git(root, "merge", "--no-ff", "--no-commit", git(fixture.candidate, "rev-parse", "HEAD"))
    (root / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "unrelated.py").write_text("OTHER = 2\n", encoding="utf-8")
    git(root, "add", "module.py", "unrelated.py")
    (root / "module.py").write_text("VALUE = 99\n", encoding="utf-8")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    return root


def _index(root: Path) -> Path:
    return Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "index"))


def _snapshot(root: Path) -> tuple:
    index = _index(root)
    objects = Path(git(root, "rev-parse", "--path-format=absolute", "--git-path", "objects"))
    return (
        {p.name: p.read_bytes() for p in index.parent.glob("*index*") if p.is_file()},
        (root / "module.py").read_bytes(),
        git(root, "show-ref"),
        {p.relative_to(objects): p.read_bytes() for p in objects.rglob("*") if p.is_file()},
        lease_rows(state_database(root)),
    )


def _preview(root: Path, **kwargs) -> dict:
    return prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        **{"target": "index", **kwargs},
    )


def test_public_index_preview_binds_prestate_and_preserves_mixed_content(
    mixed_lane: Path,
    tmp_path: Path,
) -> None:
    root = mixed_lane
    expected_tree = git(root, "write-tree")
    before = _snapshot(root)
    patch = tmp_path / "selection.patch"
    patch.write_text(PATCH, encoding="utf-8")
    result = run_ethos_raw(
        "lane",
        "prewrite",
        "module.py",
        "--target",
        "index",
        "--patch",
        str(patch),
        "--editor-root",
        str(root),
        "--require-editor-root",
        "--json",
        cwd=root,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    report = full_result(result)["data"]
    state = report["request_binding"]["expected_state"]
    assert state["expected_index_tree"] == expected_tree
    assert state["index_tree"] != expected_tree
    assert state["index_preimage_sha256"] == hashlib.sha256(before[0]["index"]).hexdigest()
    assert state["patch_sha256"] == hashlib.sha256(PATCH.encode()).hexdigest()
    assert report["decision"]["reusable_authorization"] is False
    assert _snapshot(root) == before
    assert git(root, "show", ":unrelated.py") == "OTHER = 2"


@pytest.mark.parametrize("outcome", ["pass", "block", "exception"])
def test_candidate_custody_is_explicit_and_cleanup_covers_every_outcome(
    mixed_lane: Path,
    outcome: str,
) -> None:
    root, scratch, candidates = mixed_lane, [], []
    before = _snapshot(root)
    incoming = ("openspec/changes/static-delivery/tasks.md",)

    def evaluate(environment):
        scratch.append(Path(environment["GIT_INDEX_FILE"]).parent)
        tree = run_git(root, "write-tree", env=environment).stdout.strip()
        candidates.append(tree)
        assert run_git(root, "show", f"{tree}:module.py", env=environment).stdout == "VALUE = 3\n"
        assert (
            preserved_incoming_change_paths(root, incoming, tree_ref=tree, environment=environment)
            == incoming
        )
        assert preserved_incoming_change_paths(root, incoming, tree_ref=tree) == ()
        if outcome == "exception":
            message = "candidate reader unavailable"
            raise OSError(message)
        return {"verdict": outcome, "index_tree": tree}

    report = index_prewrite.index_patch_prewrite(root, [root / "module.py"], PATCH, evaluate)
    assert report["verdict"] == ("unknown" if outcome == "exception" else outcome)
    assert _snapshot(root) == before
    assert all(not path.exists() for path in scratch)
    assert all(run_git(root, "cat-file", "-e", tree, check=False).returncode for tree in candidates)


@pytest.mark.parametrize(
    ("condition", "verdict", "gap"),
    [
        ("locked", "unknown", "prewrite_index_locked"),
        ("split", "unknown", "prewrite_index_split_index_unavailable"),
        ("missing", "unknown", "prewrite_index_observation_unavailable"),
        ("conflicted", "unknown", "prewrite_index_prestate_unavailable"),
        ("scope", "block", "prewrite_patch_paths_mismatch"),
        ("preimage", "block", "prewrite_patch_preimage_mismatch"),
        ("patch", "block", "prewrite_index_patch_required"),
        ("editor", "block", "editor_root_mismatch"),
        ("foreign", "block", "lease_holder_mismatch"),
    ],
)
def test_refusals_leave_real_state_untouched(
    mixed_lane: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition: str,
    verdict: str,
    gap: str,
) -> None:
    root, patch, paths, editor = mixed_lane, PATCH, [mixed_lane / "module.py"], mixed_lane
    if condition == "locked":
        Path(str(_index(root)) + ".lock").write_bytes(b"writer")
    elif condition == "split":
        git(root, "update-index", "--split-index")
        assert git(root, "rev-parse", "--shared-index-path")
    elif condition == "missing":
        _index(root).unlink()
    elif condition == "conflicted":
        blob = git(root, "rev-parse", "HEAD:module.py")
        run_git(
            root,
            "update-index",
            "--index-info",
            stdin=f"0 {'0' * 40}\tmodule.py\n100644 {blob} 1\tmodule.py\n",
        )
    elif condition == "scope":
        paths = [root / "unrelated.py"]
    elif condition in {"preimage", "patch"}:
        patch = PATCH.replace("VALUE = 2", "VALUE = 4") if condition == "preimage" else ""
    elif condition == "editor":
        editor = root.parent
    else:
        monkeypatch.setenv("ETHOS_ACTOR", "agent:foreign")
    before = _snapshot(root)
    report = prewrite.prewrite_guard(
        root=root, paths=paths, editor_root=editor, patch=patch, target="index"
    )
    assert report["verdict"] == verdict, report
    assert any(item.startswith(gap) for item in report["required_gaps"])
    assert _snapshot(root) == before


@pytest.mark.parametrize("coordinate", ["index", "head", "lease"])
def test_in_preview_drift_refuses_without_restoring_the_concurrent_writer(
    mixed_lane: Path,
    monkeypatch: pytest.MonkeyPatch,
    coordinate: str,
) -> None:
    root, concurrent = mixed_lane, []
    original = prewrite.staged_artifact_admission

    def observe(repo, baseline, *, index_env):
        result = original(repo, baseline, index_env=index_env)
        if coordinate == "index":
            (root / "unrelated.py").write_text("OTHER = 7\n", encoding="utf-8")
            git(root, "add", "unrelated.py")
        elif coordinate == "head":
            git(root, "commit", "-m", "test: concurrent writer")
        else:
            monkeypatch.setenv("ETHOS_ACTOR", "agent:foreign")
        concurrent.append(_snapshot(root))
        return result

    monkeypatch.setattr(prewrite, "staged_artifact_admission", observe)
    report = _preview(root)
    assert report["verdict"] == report["decision"]["verdict"] == "block", report
    assert report["required_gaps"] == report["decision"]["required_gaps"]
    if coordinate != "lease":
        assert f"prewrite_index_{coordinate}_changed_during_admission" in report["required_gaps"]
    assert _snapshot(root) == concurrent[0]


@pytest.mark.parametrize("form", ["default", "sparse", "rename", "symlink"])
def test_native_index_forms_keep_worktree_selection_separate(mixed_lane: Path, form: str) -> None:
    root, patch, paths = mixed_lane, PATCH, [mixed_lane / "module.py"]
    if form == "sparse":
        git(root, "sparse-checkout", "set", "--cone", "--sparse-index", "openspec", ".ethos")
        assert "040000" in git(root, "ls-files", "--sparse", "--stage")
    elif form == "rename":
        patch = (
            "diff --git a/module.py b/src/moved.py\nsimilarity index 100%\n"
            "rename from module.py\nrename to src/moved.py\n"
        )
        paths.append(root / "src/moved.py")
    elif form == "symlink":
        source = root / "module.py"
        source.unlink()
        source.symlink_to(root / "unrelated.py")
    before = _snapshot(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=paths,
        editor_root=root,
        patch=patch,
        target="worktree" if form == "default" else "index",
    )
    assert report["verdict"] == ("block" if form == "default" else "pass"), report
    assert _snapshot(root) == before
