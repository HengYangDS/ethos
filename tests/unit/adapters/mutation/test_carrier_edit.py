"""Exercise exact carrier effects with native Git patches and unchanged authoring state."""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.carrier_edit as carrier_edit
from ethos.adapters.admission.current.authority import observe_current_authority
from ethos.adapters.admission.patch_admission import patch_admission
from ethos.adapters.repo.git import run_git
from ethos.repository.paradigm.repair import CarrierEdit
from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    for relative, text in {
        "docs/guide.md": "# Committed\n",
        "docs/remove.md": "# Remove\n",
        "unrelated.txt": "committed\n",
    }.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode())
    run_git(root, "init", "-q")
    run_git(root, "add", "-A")
    run_git(
        root,
        "-c",
        "commit.gpgsign=false",
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "commit",
        "-qm",
        "fixture",
    )
    return root


def _git_snapshot(root: Path) -> tuple[bytes, bytes, bytes]:
    return (
        (root / ".git/index").read_bytes(),
        run_git(root, "rev-parse", "HEAD", text=False, observation=True).stdout,
        run_git(root, "for-each-ref", text=False, observation=True).stdout,
    )


def _guard(calls: list[dict[str, object]]) -> object:
    def admit(
        *,
        root: Path,
        paths: list[Path],
        patch: str,
        editor_root: Path,
        require_editor_root: bool,
    ) -> dict[str, object]:
        assert editor_root == root
        assert require_editor_root
        requested = tuple(path.relative_to(root).as_posix() for path in paths)
        report = patch_admission(
            root=root,
            requested_paths=requested,
            baseline_head=run_git(root, "rev-parse", "HEAD").stdout.strip(),
            patch=patch,
        )
        calls.append({"paths": requested, "patch": patch, "report": report})
        branch = run_git(root, "symbolic-ref", "--short", "HEAD").stdout.strip()
        authority = observe_current_authority(root=root, branch=branch, actor="", required=False)
        return {
            **report,
            "mutation_authority": authority.projection(),
            "required_gaps": [] if report["verdict"] == "pass" else [report["reason"]],
        }

    return admit


def test_preview_apply_and_repeat_use_dirty_bytes_and_native_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native patch admission consumes live CRLF bytes, not committed or staged text."""
    root = _repository(tmp_path)
    guide = root / "docs/guide.md"
    before = b"# Dirty author\r\n\r\nUnformatted"
    after = b"# Dirty author\r\n\r\nFormatted\r\n"
    guide.write_bytes(before)
    unrelated = root / "unrelated.txt"
    unrelated.write_bytes(b"staged unrelated\n")
    run_git(root, "add", "unrelated.txt")
    unrelated.write_bytes(b"unstaged unrelated\n")
    edits = (
        CarrierEdit("docs/guide.md", before.decode(), after.decode()),
        CarrierEdit("docs/[literal]*.md", None, "# New\n"),
        CarrierEdit("docs/remove.md", "# Remove\n", None),
    )
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _guard(calls))
    snapshot = _git_snapshot(root)

    preview = carrier_edit.apply_carrier_edits(root=root, edits=edits)
    assert preview["verdict"] == "pass", preview
    assert calls == []
    assert guide.read_bytes() == before
    assert _git_snapshot(root) == snapshot
    patch = preview["patch"]
    assert isinstance(patch, str)
    assert patch.startswith("diff --git ")
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=edits,
        apply=True,
        preview_patch=patch,
    )

    assert result["verdict"] == "pass", result
    assert result["applied"] is True
    assert result["effects"] == {
        "docs/[literal]*.md": "postimage",
        "docs/guide.md": "postimage",
        "docs/remove.md": "postimage",
    }
    assert guide.read_bytes() == after
    assert (root / "docs/[literal]*.md").read_bytes() == b"# New\n"
    assert not (root / "docs/remove.md").exists()
    assert unrelated.read_bytes() == b"unstaged unrelated\n"
    assert _git_snapshot(root) == snapshot
    assert calls[0]["patch"] == patch
    assert calls[0]["paths"] == tuple(sorted(edit.path for edit in edits))
    assert all(result["preservation"].values())
    repeated = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(CarrierEdit("docs/guide.md", after.decode(), after.decode()),),
        apply=True,
    )
    assert repeated["state"] == "conforming"
    assert repeated["applied"] is False
    assert len(calls) == 1
    assert _git_snapshot(root) == snapshot


def test_preview_patch_mismatch_refuses_without_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A caller cannot substitute a different action patch for its preview."""
    root = _repository(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _guard(calls))
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(CarrierEdit("docs/guide.md", "# Committed\n", "# New\n"),),
        apply=True,
        preview_patch="different patch",
    )
    assert result["verdict"] == "block"
    assert result["required_gaps"] == ["carrier_edit_preview_patch_mismatch"]
    assert (root / "docs/guide.md").read_bytes() == b"# Committed\n"
    assert calls == []


def test_missing_native_authority_refuses_without_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A passing label without the guard's authority cannot authorize an effect."""
    root = _repository(tmp_path)
    native = _guard([])

    def incomplete(**options: object) -> dict[str, object]:
        report = native(**options)
        report.pop("mutation_authority")
        return report

    monkeypatch.setattr(carrier_edit, "prewrite_guard", incomplete)
    snapshot = _git_snapshot(root)
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(CarrierEdit("docs/guide.md", "# Committed\n", "# New\n"),),
        apply=True,
    )

    assert result["verdict"] == "block", result
    assert result["required_gaps"] == ["carrier_edit_mutation_authority_missing"]
    assert result["applied"] is False
    assert (root / "docs/guide.md").read_bytes() == b"# Committed\n"
    assert _git_snapshot(root) == snapshot


@pytest.mark.parametrize("coordinate", ["raw_index", "refs", "head"])
def test_git_drift_during_admission_is_preserved_without_carrier_effect(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    coordinate: str,
) -> None:
    """A concurrent index or ref effect blocks application without being undone."""
    root = _repository(tmp_path)
    calls: list[dict[str, object]] = []
    native = _guard(calls)

    def admit(**options: object) -> dict[str, object]:
        report = native(**options)
        if coordinate == "raw_index":
            (root / "unrelated.txt").write_bytes(b"intervening staged\n")
            run_git(root, "add", "unrelated.txt")
        elif coordinate == "refs":
            run_git(root, "update-ref", "refs/heads/intervening", "HEAD")
        else:
            run_git(
                root,
                "-c",
                "commit.gpgsign=false",
                "-c",
                "user.name=Test",
                "-c",
                "user.email=test@example.invalid",
                "commit",
                "--allow-empty",
                "-qm",
                "intervening",
            )
        return report

    monkeypatch.setattr(carrier_edit, "prewrite_guard", admit)
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(CarrierEdit("docs/guide.md", "# Committed\n", "# New\n"),),
        apply=True,
    )
    assert result["verdict"] == "block", result
    assert result["preservation"][coordinate] is False
    assert (root / "docs/guide.md").read_bytes() == b"# Committed\n"


def test_changed_lease_generation_blocks_before_native_apply(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reobserve the original authority rather than reuse a once-passing generation."""
    root = _repository(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _guard(calls))

    def changed_authority(**options: object):
        observed = observe_current_authority(**options)
        return replace(observed, lease={**observed.lease, "generation": 2})

    monkeypatch.setattr(carrier_edit, "observe_current_authority", changed_authority)
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(CarrierEdit("docs/guide.md", "# Committed\n", "# New\n"),),
        apply=True,
    )
    assert result["verdict"] == "block", result
    assert "carrier_edit_authority_changed:generation" in result["required_gaps"]
    assert (root / "docs/guide.md").read_bytes() == b"# Committed\n"


@pytest.mark.parametrize("failure", [OSError("injected I/O failure"), KeyboardInterrupt()])
def test_partial_native_effect_is_reobserved_without_compensation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    """An interruption after one actual Git write reports retained, partial effects."""
    root = _repository(tmp_path)
    calls: list[dict[str, object]] = []
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _guard(calls))
    native = carrier_edit.run_git

    def interrupted(repo, *args, **options):
        if args and args[0] == "apply":
            applied = native(repo, *args, "--include=docs/guide.md", **options)
            assert applied.returncode == 0
            raise failure
        return native(repo, *args, **options)

    monkeypatch.setattr(carrier_edit, "run_git", interrupted)
    snapshot = _git_snapshot(root)
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(
            CarrierEdit("docs/guide.md", "# Committed\n", "# New\n"),
            CarrierEdit("docs/remove.md", "# Remove\n", "# Changed\n"),
        ),
        apply=True,
    )
    assert result["applied"] is False, result
    assert result["partial_transition"] is True, result
    assert result["effects"] == {"docs/guide.md": "postimage", "docs/remove.md": "preimage"}
    assert result["lifecycle_effect_outcome"]["effect_state"] == "mutated"
    assert result["recovery"]["automatic"] is False
    assert result["recovery"]["restorable_paths"] == ["docs/guide.md"]
    assert (root / "docs/guide.md").read_bytes() == b"# New\n"
    assert (root / "docs/remove.md").read_bytes() == b"# Remove\n"
    assert _git_snapshot(root) == snapshot


def test_postimage_contestation_is_not_overwritten(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A later author retains their bytes even when Git reported successful application."""
    root = _repository(tmp_path)
    monkeypatch.setattr(carrier_edit, "prewrite_guard", _guard([]))
    native = carrier_edit.run_git
    intervening = b"# Later author\n"

    def contested(repo, *args, **options):
        result = native(repo, *args, **options)
        if args and args[0] == "apply":
            (root / "docs/guide.md").write_bytes(intervening)
        return result

    monkeypatch.setattr(carrier_edit, "run_git", contested)
    result = carrier_edit.apply_carrier_edits(
        root=root,
        edits=(CarrierEdit("docs/guide.md", "# Committed\n", "# New\n"),),
        apply=True,
    )
    assert result["verdict"] == "block"
    assert result["partial_transition"] is True
    assert result["effects"] == {"docs/guide.md": "diverged"}
    assert result["recovery"]["contested_paths"] == ["docs/guide.md"]
    assert result["recovery"]["restorable_paths"] == []
    assert (root / "docs/guide.md").read_bytes() == intervening


def test_native_work_lane_admits_the_same_dirty_document_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The real Work Lane guard consumes the producer patch under its current lease."""
    fixture = prepared_work_lane(tmp_path, name="carrier-edit", docs_only=True)
    root = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    target = root / "docs/guide.md"
    target.parent.mkdir(exist_ok=True)
    target.write_bytes(b"# Dirty author\n")
    edits = (CarrierEdit("docs/guide.md", "# Dirty author\n", "# Formatted author\n"),)
    git_dir = root / run_git(root, "rev-parse", "--git-dir").stdout.strip()
    index = (git_dir / "index").read_bytes()
    result = carrier_edit.apply_carrier_edits(root=root, edits=edits, apply=True)

    assert result["verdict"] == "pass", result
    assert result["admission"]["patch_admission"]["paths"] == ["docs/guide.md"]
    assert result["admission"]["work_lane_lease"]["generation"] == 1
    assert target.read_bytes() == b"# Formatted author\n"
    assert (git_dir / "index").read_bytes() == index
    assert all(result["preservation"].values())
