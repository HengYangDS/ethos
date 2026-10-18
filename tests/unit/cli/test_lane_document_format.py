"""Native document commands retain authoring inputs and exact mutation admission."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.repo.git import run_git
from tests.support.ethos_cli_runner import result_data
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    import pytest


def _snapshot(root: Path) -> tuple[bytes, bytes, bytes]:
    """Retain raw index, HEAD and refs without refreshing the index."""
    index = run_git(
        root, "rev-parse", "--path-format=absolute", "--git-path", "index", observation=True
    ).stdout.strip()
    return (
        Path(index).read_bytes(),
        run_git(root, "rev-parse", "HEAD", text=False, observation=True).stdout,
        run_git(root, "for-each-ref", text=False, observation=True).stdout,
    )


def test_cli_preview_apply_and_noop_use_native_current_documents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A public command previews original native bytes and applies only that preview."""
    lane = prepared_work_lane(tmp_path, name="document-command", docs_only=True).worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    guide = lane / "README.md"
    guide.write_bytes(b"# Guide\r\n\r\n\r\nRead the evidence.\r\n")
    original, coordinates = guide.read_bytes(), _snapshot(lane)
    command = ("lane", "format-documents", "--root", str(lane), "--json")

    preview = result_data(run_ethos(*command))

    assert preview["state"] == "planned"
    assert preview["applied"] is False
    assert preview["input_kind"] == "working-tree"
    assert "README.md" in preview["checked_paths"]
    assert preview["patch"].startswith("diff --git ")
    assert guide.read_bytes() == original
    assert _snapshot(lane) == coordinates
    patch = tmp_path / "format.patch"
    patch.write_bytes(preview["patch"].encode("utf-8"))

    applied = result_data(run_ethos(*command, "--apply", "--preview-patch", str(patch)))

    assert applied["applied"] is True
    assert applied["admission"]["patch_admission"]["paths"] == ["README.md"]
    assert guide.read_bytes() == b"# Guide\n\nRead the evidence.\n"
    assert _snapshot(lane) == coordinates
    repeated = result_data(run_ethos(*command, "--apply"))
    assert repeated["state"] == "conforming"
    assert repeated["applied"] is False
    assert repeated["patch"] == ""
    assert _snapshot(lane) == coordinates


def test_cli_refuses_missing_preview_and_missing_actor_without_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The native entry cannot replace preview consent or current Work Lane authority."""
    lane = prepared_work_lane(tmp_path, name="document-command", docs_only=True).worktree
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    guide = lane / "README.md"
    guide.write_bytes(b"# Guide\n\n\nRead the evidence.\n")
    original, coordinates = guide.read_bytes(), _snapshot(lane)
    command = ("lane", "format-documents", "--root", str(lane), "--json")
    preview = result_data(run_ethos(*command))
    missing = run_ethos_blocked(*command, "--apply")
    assert missing["required_gaps"] == ["document_format_preview_required"]
    patch = tmp_path / "format.patch"
    patch.write_bytes(preview["patch"].encode("utf-8"))
    monkeypatch.delenv("ETHOS_ACTOR")

    refused = run_ethos_blocked(*command, "--apply", "--preview-patch", str(patch))

    assert any("invocation_actor_missing" in gap for gap in refused["required_gaps"])
    assert guide.read_bytes() == original
    assert _snapshot(lane) == coordinates
