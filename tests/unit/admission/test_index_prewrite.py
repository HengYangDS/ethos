"""Qualify exact index patches without substituting mixed working content."""

from __future__ import annotations

from pathlib import Path

import pytest

import ethos.adapters.admission.index_prewrite as index_prewrite
import ethos.adapters.admission.prewrite as prewrite
from ethos.adapters.admission.current.authority import CurrentAuthority
from ethos.adapters.repo.git import run_git
from tests.support.ethos_cli_runner import full_result
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

PATCH = (
    "diff --git a/module.py b/module.py\n"
    "--- a/module.py\n"
    "+++ b/module.py\n"
    "@@ -1 +1 @@\n"
    "-VALUE = 2\n"
    "+VALUE = 3\n"
)


def _mixed_repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = init_git_repo(tmp_path / "repo")
    (root / "module.py").write_text("VALUE = 1\n", encoding="utf-8")
    (root / "unrelated.py").write_text("OTHER = 1\n", encoding="utf-8")
    git(root, "add", "module.py", "unrelated.py")
    git(root, "commit", "-m", "prepare mixed source")
    git(root, "checkout", "-b", "work/example")
    (root / "module.py").write_text("VALUE = 2\n", encoding="utf-8")
    (root / "unrelated.py").write_text("OTHER = 2\n", encoding="utf-8")
    git(root, "add", "module.py", "unrelated.py")
    (root / "module.py").write_text("VALUE = 99\n", encoding="utf-8")
    monkeypatch.setattr(prewrite, "runtime_binding_check", lambda _status: {"verdict": "pass"})
    monkeypatch.setattr(prewrite, "openspec_profile_enabled", lambda _root: False)
    authority = CurrentAuthority(
        verdict="pass",
        reason="matched",
        branch="work/example",
        actor="agent:test",
        lease={"holder_ref": "agent:test", "generation": 1},
        current_head=git(root, "rev-parse", "HEAD"),
        current_tree=git(root, "rev-parse", "HEAD^{tree}"),
    )
    monkeypatch.setattr(prewrite, "observe_current_authority", lambda **_kwargs: authority)
    return root


def _index_bytes(root: Path) -> bytes:
    return (root / ".git/index").read_bytes()


def test_index_patch_admits_exact_postimage_and_preserves_mixed_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    before = _index_bytes(root)
    observe = prewrite.staged_artifact_admission
    contents = {}

    def candidate_contents(repo, baseline, *, index_env):
        report = observe(repo, baseline, index_env=index_env)
        tree = report["index_tree"]
        contents.update(
            {
                path: run_git(repo, "show", f"{tree}:{path}", env=index_env).stdout.strip()
                for path in ("module.py", "unrelated.py")
            }
        )
        return report

    monkeypatch.setattr(prewrite, "staged_artifact_admission", candidate_contents)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] == "pass", report
    assert _index_bytes(root) == before
    assert (root / "module.py").read_text() == "VALUE = 99\n"
    assert git(root, "show", ":unrelated.py") == "OTHER = 2"
    subject = report["request_binding"]
    assert isinstance(subject, dict)
    binding = subject["expected_state"]
    assert isinstance(binding, dict)
    assert binding["target"] == "index"
    assert binding["index_preimage_sha256"]
    assert binding["patch_sha256"]
    assert binding["index_tree"]
    assert contents == {"module.py": "VALUE = 3", "unrelated.py": "OTHER = 2"}
    decision = report["decision"]
    assert isinstance(decision, dict)
    assert decision["reusable_authorization"] is False


def test_default_target_does_not_silently_stage_the_index_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
    )
    assert report["verdict"] == "block"
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert "prewrite_patch_preimage_mismatch" in gaps
    assert _index_bytes(root) == before


@pytest.mark.parametrize("coordinate", ["index", "head"])
def test_index_prestate_drift_cannot_be_hidden_by_stable_scratch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    coordinate: str,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    original_scope = prewrite.non_openspec_prewrite_scope
    concurrent = b""

    def concurrent_scope(paths):
        nonlocal concurrent
        if coordinate == "index":
            (root / "unrelated.py").write_text("OTHER = 7\n", encoding="utf-8")
            git(root, "add", "unrelated.py")
        else:
            git(root, "commit", "--allow-empty", "-m", "concurrent writer")
        concurrent = _index_bytes(root)
        return original_scope(paths)

    monkeypatch.setattr(prewrite, "non_openspec_prewrite_scope", concurrent_scope)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert f"prewrite_index_{coordinate}_changed_during_admission" in gaps
    assert _index_bytes(root) == concurrent


@pytest.mark.parametrize(
    ("patch", "paths", "gap"),
    [
        ("", ["module.py"], "prewrite_index_patch_required"),
        (PATCH, ["unrelated.py"], "prewrite_patch_paths_mismatch"),
        (PATCH, ["../repo/module.py"], "prewrite_patch_paths_mismatch"),
        (PATCH, ["../outside.py"], "prewrite_patch_paths_mismatch"),
        (
            PATCH.replace("VALUE = 2", "VALUE = 4"),
            ["module.py"],
            "prewrite_patch_preimage_mismatch",
        ),
    ],
)
def test_index_patch_refusals_preserve_real_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    patch: str,
    paths: list[str],
    gap: str,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / path for path in paths],
        editor_root=root,
        patch=patch,
        target="index",
    )
    assert report["verdict"] == "block", report
    gaps = report["required_gaps"]
    assert isinstance(gaps, list)
    assert gap in gaps
    assert _index_bytes(root) == before
    assert (root / "module.py").read_text() == "VALUE = 99\n"


def test_public_cli_routes_index_target(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    patch = tmp_path / "selection.patch"
    patch.write_text(PATCH, encoding="utf-8")
    completed = run_ethos_raw(
        "lane",
        "prewrite",
        "module.py",
        "--target",
        "index",
        "--patch",
        str(patch),
        "--editor-root",
        str(root),
        "--json",
        cwd=root,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    assert full_result(completed)["verdict"] == "pass"


@pytest.mark.parametrize("failure", ["missing-index", "unmerged-index", "scope-unknown"])
def test_index_observation_unknown_has_no_real_effect_and_no_scratch_residue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    directory = index_prewrite.tempfile.TemporaryDirectory
    monkeypatch.setattr(
        index_prewrite.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: directory(dir=scratch, **kwargs),
    )
    if failure == "missing-index":
        (root / ".git/index").unlink()
    elif failure == "unmerged-index":
        blob = git(root, "rev-parse", "HEAD:module.py")

        run_git(
            root,
            "update-index",
            "--index-info",
            stdin=f"0 {'0' * 40}\tmodule.py\n100644 {blob} 1\tmodule.py\n",
        )
        assert git(root, "ls-files", "--unmerged")
        assert run_git(root, "write-tree", check=False).returncode != 0
    else:
        monkeypatch.setattr(
            prewrite,
            "non_openspec_prewrite_scope",
            lambda _paths: {"verdict": "unknown", "required_gaps": ["scope_unavailable"]},
        )
    index = root / ".git/index"
    before = index.read_bytes() if index.exists() else None
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] != "pass", report
    assert (index.read_bytes() if index.exists() else None) == before
    assert (root / "module.py").read_text() == "VALUE = 99\n"
    assert list(scratch.iterdir()) == []


@pytest.mark.parametrize("boundary", ["protected", "foreign"])
def test_index_target_does_not_grant_lane_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    boundary: str,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    if boundary == "protected":
        git(root, "checkout", "dev")
    else:
        authority = CurrentAuthority(
            verdict="block",
            reason="lease_holder_mismatch:work/example",
            branch="work/example",
            actor="agent:foreign",
            lease={"holder_ref": "agent:test", "generation": 1},
            current_head=git(root, "rev-parse", "HEAD"),
            current_tree=git(root, "rev-parse", "HEAD^{tree}"),
        )
        monkeypatch.setattr(prewrite, "observe_current_authority", lambda **_kwargs: authority)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] == "block", report
    assert _index_bytes(root) == before


def test_failed_index_evaluator_removes_preparation_and_preserves_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    directory = index_prewrite.tempfile.TemporaryDirectory
    monkeypatch.setattr(
        index_prewrite.tempfile,
        "TemporaryDirectory",
        lambda **kwargs: directory(dir=scratch, **kwargs),
    )

    def unavailable(_paths):
        message = "scope observer unavailable"
        raise OSError(message)

    monkeypatch.setattr(prewrite, "non_openspec_prewrite_scope", unavailable)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] == "unknown"
    assert _index_bytes(root) == before
    assert list(scratch.iterdir()) == []


def test_index_admission_rechecks_lease_after_scope_observation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    original_scope = prewrite.non_openspec_prewrite_scope

    def transfer_during_scope(paths):
        foreign = CurrentAuthority(
            verdict="block",
            reason="lease_holder_mismatch:work/example",
            branch="work/example",
            actor="agent:test",
            lease={"holder_ref": "agent:other", "generation": 2},
            current_head=git(root, "rev-parse", "HEAD"),
            current_tree=git(root, "rev-parse", "HEAD^{tree}"),
        )
        monkeypatch.setattr(prewrite, "observe_current_authority", lambda **_kwargs: foreign)
        return original_scope(paths)

    monkeypatch.setattr(prewrite, "non_openspec_prewrite_scope", transfer_during_scope)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[root / "module.py"],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] == "block", report
    assert _index_bytes(root) == before


def test_staged_authority_preserves_owned_rebase_context(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    authority = prewrite.observe_current_authority(
        root=root, branch="work/example", actor="agent:test", required=True
    )
    git(root, "checkout", "--detach")
    rebase = root / ".git/rebase-merge"
    rebase.mkdir()
    (rebase / "head-name").write_text("refs/heads/work/example\n", encoding="utf-8")

    def observe(**coordinates):
        return CurrentAuthority(
            verdict="pass",
            reason="matched",
            branch=coordinates["branch"],
            actor=authority.actor,
            lease=authority.lease,
            current_head=authority.current_head,
            current_tree=authority.current_tree,
            head_source=coordinates["head_source"],
        )

    monkeypatch.setattr(prewrite, "observe_current_authority", observe)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root, paths=[root / "module.py"], editor_root=root, patch=PATCH, target="index"
    )
    assert report["verdict"] == "pass", report
    assert _index_bytes(root) == before


def test_index_drift_projects_the_same_refusal_in_decision(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    original = prewrite.non_openspec_prewrite_scope

    def change_index(paths):
        (root / "unrelated.py").write_text("OTHER = 7\n", encoding="utf-8")
        git(root, "add", "unrelated.py")
        return original(paths)

    monkeypatch.setattr(prewrite, "non_openspec_prewrite_scope", change_index)
    report = prewrite.prewrite_guard(
        root=root, paths=[root / "module.py"], editor_root=root, patch=PATCH, target="index"
    )
    assert report["verdict"] == "block"
    decision = report["decision"]
    assert isinstance(decision, dict)
    assert decision["verdict"] == report["verdict"]
    assert decision["required_gaps"] == report["required_gaps"]
    assert decision["next_action"] == "repair_required_gap"


@pytest.mark.parametrize("include_source", [False, True])
def test_index_rename_binds_both_effect_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, include_source: bool
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    observe = prewrite.staged_artifact_admission
    contents = []

    def candidate_contents(repo, baseline, *, index_env):
        report = observe(repo, baseline, index_env=index_env)
        contents.append(
            run_git(repo, "show", f"{report['index_tree']}:src/moved.py", env=index_env).stdout
        )
        return report

    monkeypatch.setattr(prewrite, "staged_artifact_admission", candidate_contents)
    patch = (
        "diff --git a/module.py b/src/moved.py\n"
        "similarity index 100%\n"
        "rename from module.py\n"
        "rename to src/moved.py\n"
    )
    paths = [root / "src/moved.py", *([root / "module.py"] if include_source else [])]
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root, paths=paths, editor_root=root, patch=patch, target="index"
    )
    assert report["verdict"] == ("pass" if include_source else "block"), report
    if include_source:
        binding = report["request_binding"]
        assert isinstance(binding, dict)
        state = binding["expected_state"]
        assert isinstance(state, dict)
        assert sorted(state["paths"]) == ["module.py", "src/moved.py"]
        assert contents == ["VALUE = 2\n"]
    else:
        gaps = report["required_gaps"]
        assert isinstance(gaps, list)
        assert "prewrite_patch_paths_mismatch" in gaps
    assert _index_bytes(root) == before
    assert (root / "module.py").read_text() == "VALUE = 99\n"


@pytest.mark.parametrize("relative", [False, True])
def test_index_path_identity_does_not_follow_unstaged_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, relative: bool
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    outside = tmp_path / "outside.py"
    outside.write_text("EXTERNAL = 1\n", encoding="utf-8")
    source = root / "module.py"
    source.unlink()
    source.symlink_to(outside)
    before = _index_bytes(root)
    report = prewrite.prewrite_guard(
        root=root,
        paths=[source.relative_to(root) if relative else source],
        editor_root=root,
        patch=PATCH,
        target="index",
    )
    assert report["verdict"] == "pass", report
    assert _index_bytes(root) == before
    assert source.is_symlink()
    assert outside.read_text() == "EXTERNAL = 1\n"


@pytest.mark.parametrize("outcome", ["pass", "block", "exception"])
def test_index_preparation_reclaims_candidate_objects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    root = _mixed_repository(tmp_path, monkeypatch)
    objects = root / ".git/objects"
    before = {
        path.relative_to(objects): path.read_bytes()
        for path in objects.rglob("*")
        if path.is_file()
    }
    index = _index_bytes(root)
    scratch = []
    candidates = []

    def evaluate(environment):
        scratch.append(Path(environment["GIT_INDEX_FILE"]).parent)
        tree = run_git(root, "write-tree", env=environment).stdout.strip()
        candidates.append(tree)
        assert run_git(root, "show", f"{tree}:module.py", env=environment).stdout == "VALUE = 3\n"
        if outcome == "exception":
            message = "candidate observer unavailable"
            raise OSError(message)
        return {"verdict": outcome, "index_tree": tree}

    report = index_prewrite.index_patch_prewrite(root, [root / "module.py"], PATCH, evaluate)
    assert report["verdict"] == ("unknown" if outcome == "exception" else outcome)
    assert {
        path.relative_to(objects): path.read_bytes()
        for path in objects.rglob("*")
        if path.is_file()
    } == before
    assert all(not path.exists() for path in scratch)
    assert all(
        run_git(root, "cat-file", "-e", tree, check=False).returncode != 0 for tree in candidates
    )
    assert _index_bytes(root) == index
    assert (root / "module.py").read_text() == "VALUE = 99\n"
