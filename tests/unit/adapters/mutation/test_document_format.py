"""Exercise the native document formatter through an admitted authoring effect."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

import pytest

from ethos.adapters.gates.markdown import native_document_observation
from ethos.adapters.gates.markdown import working_document_report
from ethos.adapters.repo.git import run_git
from tests.support.governed_repository import prepared_work_lane


def _snapshot(root: Path) -> tuple[bytes, bytes, bytes]:
    index = run_git(
        root, "rev-parse", "--path-format=absolute", "--git-path", "index", observation=True
    ).stdout.strip()
    return (
        Path(index).read_bytes(),
        run_git(root, "rev-parse", "HEAD", text=False, observation=True).stdout,
        run_git(root, "for-each-ref", text=False, observation=True).stdout,
    )


def _lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict[str, str]]:
    fixture = prepared_work_lane(tmp_path, name="document-format", docs_only=True)
    root = fixture.worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    sources = {
        "README.md": "# Guide\r\n\r\n\r\nRead the evidence.\r\n",
        "docs/[literal]*.md": "# Native\n\n\nRead the result.\n",
    }
    for path, text in sources.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    return root, sources


def test_native_preview_apply_check_and_noop_preserve_git_authoring_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A real Work Lane consumes original Prettier output and exact preview admission."""
    root, sources = _lane(tmp_path, monkeypatch)
    agents = root / "AGENTS.md"
    agents.write_bytes(b"# Agents\n\nStaged unrelated authoring.\n")
    run_git(root, "add", "AGENTS.md")
    agents.write_bytes(b"# Agents\n\nUnstaged unrelated authoring.\n")
    canonical = native_document_observation(root, sources, lint=False)["formatted"]
    before = _snapshot(root)
    owner = import_module("ethos.adapters.mutation.document_format")

    check_before = working_document_report(root, kind="format")
    assert check_before["verdict"] == "block", check_before
    assert set(sources).issubset(check_before["format_drift"])
    preview = owner.format_documents(root=root, sources=sources)
    assert preview["verdict"] == "pass", preview
    assert preview["state"] == "planned"
    assert preview["applied"] is False
    assert preview["input_kind"] == "working-tree"
    assert preview["checked_paths"] == sorted(sources)
    assert isinstance(preview["patch"], str)
    assert preview["patch"].startswith("diff --git ")
    assert _snapshot(root) == before
    for path, text in sources.items():
        assert (root / path).read_bytes() == text.encode("utf-8")

    applied = owner.format_documents(
        root=root, sources=sources, apply=True, preview_patch=preview["patch"]
    )
    assert applied["verdict"] == "pass", applied
    assert applied["applied"] is True
    assert applied["admission"]["patch_admission"]["paths"] == sorted(sources)
    assert applied["patch"] == preview["patch"]
    assert all(applied["preservation"].values())
    assert _snapshot(root) == before
    assert agents.read_bytes() == b"# Agents\n\nUnstaged unrelated authoring.\n"
    for path, text in canonical.items():
        assert (root / path).read_bytes() == text.encode("utf-8")

    check_after = working_document_report(root, kind="format")
    assert check_after["verdict"] == "pass", check_after
    assert check_after["input_kind"] == "working-tree"
    repeated = owner.format_documents(root=root, sources=canonical, apply=True)
    assert repeated["verdict"] == "pass", repeated
    assert repeated["state"] == "conforming"
    assert repeated["applied"] is False
    assert repeated["patch"] == ""
    assert _snapshot(root) == before


def test_native_refusal_has_no_effect_without_current_actor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Native admission refusal does not change documents, HEAD, refs or raw index."""
    root, sources = _lane(tmp_path, monkeypatch)
    owner = import_module("ethos.adapters.mutation.document_format")
    preview = owner.format_documents(root=root, sources=sources)
    before = _snapshot(root)
    monkeypatch.delenv("ETHOS_ACTOR")
    result = owner.format_documents(
        root=root, sources=sources, apply=True, preview_patch=preview["patch"]
    )
    assert result["verdict"] == "block", result
    assert result["applied"] is False
    assert any("invocation_actor_missing" in gap for gap in result["required_gaps"])
    assert result["lifecycle_effect_outcome"]["effect_state"] == "zero_effect"
    assert _snapshot(root) == before
    for path, text in sources.items():
        assert (root / path).read_bytes() == text.encode("utf-8")


@pytest.mark.parametrize("patch", [None, "substituted preview"])
def test_apply_requires_the_exact_preview_without_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patch: str | None
) -> None:
    """Neither a missing preview nor a replacement patch authorizes formatting."""
    root, sources = _lane(tmp_path, monkeypatch)
    owner = import_module("ethos.adapters.mutation.document_format")
    before = _snapshot(root)
    result = owner.format_documents(root=root, sources=sources, apply=True, preview_patch=patch)
    assert result["verdict"] == "block", result
    assert result["applied"] is False
    assert result["required_gaps"] == [
        "document_format_preview_required"
        if patch is None
        else "carrier_edit_preview_patch_mismatch"
    ]
    assert _snapshot(root) == before
    for path, text in sources.items():
        assert (root / path).read_bytes() == text.encode("utf-8")


def test_stale_formatter_inputs_preserve_an_intervening_author(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Caller-owned preview preimages cannot overwrite a subsequent document edit."""
    root, sources = _lane(tmp_path, monkeypatch)
    owner = import_module("ethos.adapters.mutation.document_format")
    preview = owner.format_documents(root=root, sources=sources)
    intervening = b"# Later author\n"
    (root / "README.md").write_bytes(intervening)
    before = _snapshot(root)
    result = owner.format_documents(
        root=root, sources=sources, apply=True, preview_patch=preview["patch"]
    )
    assert result["verdict"] == "block", result
    assert result["applied"] is False
    assert result["required_gaps"] == ["document_format_source_changed:README.md"]
    assert (root / "README.md").read_bytes() == intervening
    assert (root / "docs/[literal]*.md").read_bytes() == sources["docs/[literal]*.md"].encode()
    assert _snapshot(root) == before


def test_official_and_immutable_documents_are_observed_but_never_formatted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The native OpenSpec owner and archived originals remain outside the write set."""
    root, sources = _lane(tmp_path, monkeypatch)
    excluded = {
        "openspec/changes/fixture-change/design.md": "# Design\n\n\nPreserve official bytes.\n",
        "openspec/changes/archive/2026-01-01-original/tasks.md": "# Tasks\n\n\nPreserve archive.\n",
    }
    for path, text in excluded.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    selected = {**sources, **excluded}
    owner = import_module("ethos.adapters.mutation.document_format")
    preview = owner.format_documents(root=root, sources=selected)
    assert preview["verdict"] == "pass", preview
    assert preview["excluded_paths"] == sorted(excluded)
    assert {edit["path"] for edit in preview["edits"]} == set(sources)
    for path, text in excluded.items():
        assert (root / path).read_bytes() == text.encode("utf-8")
    protected = owner.format_documents(root=root, sources=excluded, apply=True)
    assert protected["state"] == "conforming", protected
    assert protected["applied"] is False
    assert protected["patch"] == ""
    for path, text in excluded.items():
        assert (root / path).read_bytes() == text.encode("utf-8")
