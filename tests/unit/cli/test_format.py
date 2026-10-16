"""The public format operation preserves literal sources and exact write admission."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.formatting as owner

if TYPE_CHECKING:
    from pathlib import Path

from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


def _repository(root: Path) -> Path:
    repo = root / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs/guide [draft].md").write_bytes(
        b"# Guide  \n\n\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    )
    (repo / "policy.toml").write_bytes(b"key   =   'value'\n")
    (repo / "settings.yaml").write_bytes(b"key:    value\n")
    for args in (("init",), ("add", ".")):
        subprocess.run(("git", "-C", str(repo), *args), check=True, capture_output=True)
    return repo


def test_check_is_literal_nonmutating_and_reports_the_native_diff(
    tmp_path: Path,
) -> None:
    """A native check neither expands brackets nor repairs an unrequested sibling."""
    repo = _repository(tmp_path)
    selected = repo / "docs/guide [draft].md"
    before = selected.read_bytes()
    sibling = (repo / "policy.toml").read_bytes()
    result = run_ethos_blocked(
        "format", "docs/guide [draft].md", "--check", "--root", str(repo), "--json"
    )
    assert result["verdict"] == "block"
    data = result["data"]
    assert data["state"] == "format_required"
    assert data["changed_paths"] == ["docs/guide [draft].md"]
    assert data["applied"] is False
    assert selected.read_bytes() == before
    assert (repo / "policy.toml").read_bytes() == sibling


def test_apply_requires_exact_admission_and_second_check_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One public operation formats all supported authored carriers, then reaches a fixed point."""
    repo = _repository(tmp_path)
    seen: list[str] = []

    def admitted(**kwargs):
        seen.extend(path.relative_to(repo).as_posix() for path in kwargs["paths"])
        assert kwargs["root"] == repo
        return {"verdict": "pass"}

    monkeypatch.setattr(owner, "prewrite_guard", admitted)
    result = run_ethos("format", "--apply", "--root", str(repo), "--json")
    assert result["data"]["applied"] is True
    assert set(seen) == {"docs/guide [draft].md", "policy.toml", "settings.yaml"}
    after = {path: (repo / path).read_bytes() for path in seen}
    result = run_ethos("format", "--check", "--root", str(repo), "--json")
    assert result["data"]["changed_paths"] == []
    assert all((repo / path).read_bytes() == content for path, content in after.items())


@pytest.mark.parametrize("path", ["../outside.md", "missing.md", "docs/*.md"])
def test_invalid_literal_selection_is_refused_without_source_writes(
    tmp_path: Path, path: str
) -> None:
    """Explicit inputs must be exact tracked authored files, not guesses or globs."""
    repo = _repository(tmp_path)
    before = (repo / "docs/guide [draft].md").read_bytes()
    result = run_ethos_blocked("format", path, "--apply", "--root", str(repo), "--json")
    assert result["data"]["applied"] is False
    assert result["required_gaps"]
    assert (repo / "docs/guide [draft].md").read_bytes() == before


def test_admission_refusal_preserves_all_source_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rendering a candidate is not permission to write it."""
    repo = _repository(tmp_path)
    before = (repo / "docs/guide [draft].md").read_bytes()
    monkeypatch.setattr(
        owner,
        "prewrite_guard",
        lambda **_: {"verdict": "block", "required_gaps": ["test_denied"]},
    )
    result = run_ethos_blocked("format", "--apply", "--root", str(repo), "--json")
    assert "test_denied" in result["required_gaps"]
    assert (repo / "docs/guide [draft].md").read_bytes() == before


def test_content_drift_at_admission_is_preserved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A same-path edit during admission must not be overwritten by an earlier rendering."""
    repo = _repository(tmp_path)
    selected = repo / "docs/guide [draft].md"

    def concurrent(**_):
        selected.write_bytes(b"# Concurrent author\n")
        return {"verdict": "pass"}

    monkeypatch.setattr(owner, "prewrite_guard", concurrent)
    result = run_ethos_blocked("format", "--apply", "--root", str(repo), "--json")
    assert result["data"]["applied"] is False
    assert selected.read_bytes() == b"# Concurrent author\n"


def test_format_ignores_untracked_document_registry_lookalikes(tmp_path: Path) -> None:
    """A malformed untracked sibling cannot select or block a tracked literal source."""
    repo = _repository(tmp_path)
    untracked = repo / "docs/untracked.md"
    untracked.write_bytes(b"---\nrole: [not, a, role]\n---\n\n# Untracked\n")
    result = run_ethos_blocked(
        "format", "docs/guide [draft].md", "--check", "--root", str(repo), "--json"
    )
    assert result["data"]["state"] == "format_required"
    assert result["data"]["selected_paths"] == ["docs/guide [draft].md"]
    assert untracked.read_bytes().startswith(b"---\nrole: [not, a, role]")


@pytest.mark.parametrize(
    ("relative", "content"),
    [
        ("docs/config [draft].toml", b"key   =   'value'\n"),
        ("docs/source\nnext.md", b"# Guide  \n\n\n"),
    ],
)
def test_format_preserves_special_literal_paths(
    tmp_path: Path, relative: str, content: bytes
) -> None:
    """Native tools must process one literal path, not glob or line-delimited aliases."""
    repo = _repository(tmp_path)
    target = repo / relative
    target.write_bytes(content)
    subprocess.run(("git", "-C", str(repo), "add", "--", relative), check=True)
    result = run_ethos_blocked("format", relative, "--check", "--root", str(repo), "--json")
    assert result["data"]["state"] == "format_required"
    assert result["data"]["selected_paths"] == [relative]
    assert target.read_bytes() == content


@pytest.mark.parametrize(
    ("relative", "replacement"),
    [("policy.toml", b"key = 'different'\n"), ("settings.yaml", b"key: different\n")],
)
def test_format_refuses_native_structured_value_changes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
    replacement: bytes,
) -> None:
    """A successful renderer cannot grant permission to change structured source values."""
    repo = _repository(tmp_path)
    before = (repo / relative).read_bytes()
    monkeypatch.setattr(
        owner,
        "format_source_contents",
        lambda _root, _owner, sources: dict.fromkeys(sources, replacement),
    )
    monkeypatch.setattr(owner, "prewrite_guard", lambda **_: {"verdict": "pass"})
    result = run_ethos_blocked("format", relative, "--apply", "--root", str(repo), "--json")
    assert "format_semantics_changed:" + relative in result["required_gaps"]
    assert (repo / relative).read_bytes() == before


def test_format_unavailable_native_supply_never_writes_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unavailable product supply stays unknown before source write admission."""
    repo = _repository(tmp_path)
    originals = {
        path: path.read_bytes()
        for path in repo.rglob("*")
        if path.is_file() and ".git" not in path.parts
    }

    def unavailable(_name: str) -> Path:
        message = "node_package_supply_unavailable"
        raise ValueError(message)

    monkeypatch.setattr("ethos.adapters.gates.tool.product_node_module", unavailable)
    result = run_ethos_blocked("format", "--apply", "--root", str(repo), "--json")
    assert result["verdict"] == "unknown"
    assert result["data"]["applied"] is False
    assert result["required_gaps"] == ["node_package_supply_unavailable"]
    assert all(path.read_bytes() == content for path, content in originals.items())


@pytest.mark.parametrize("concurrent", [False, True])
def test_partial_format_compensates_only_its_matching_written_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, concurrent: bool
) -> None:
    """A partial apply cannot become success or overwrite a concurrent author during recovery."""
    repo = _repository(tmp_path)
    originals = {
        "docs/guide [draft].md": (repo / "docs/guide [draft].md").read_bytes(),
        "policy.toml": (repo / "policy.toml").read_bytes(),
        "settings.yaml": (repo / "settings.yaml").read_bytes(),
    }
    native_replace = owner._replace
    written: list[str] = []
    concurrent_bytes = b"# Concurrent author\n"

    def interrupted(root, edit, *, restore=False):
        if not restore and written:
            if concurrent:
                (repo / written[0]).write_bytes(concurrent_bytes)
            message = "test_partial_write_failed"
            raise OSError(message)
        native_replace(root, edit, restore=restore)
        if not restore:
            written.append(edit.path)

    monkeypatch.setattr(owner, "prewrite_guard", lambda **_: {"verdict": "pass"})
    monkeypatch.setattr(owner, "_replace", interrupted)
    result = run_ethos_blocked("format", "--apply", "--root", str(repo), "--json")
    assert result["data"]["applied"] is False
    assert result["data"]["state"] == "unproven"
    assert "test_partial_write_failed" in result["required_gaps"]
    assert len(written) == 1
    for relative, content in originals.items():
        expected = concurrent_bytes if concurrent and relative == written[0] else content
        assert (repo / relative).read_bytes() == expected
    if concurrent:
        assert "format_source_stale:" + written[0] in result["required_gaps"]
    assert not list((repo / "docs").glob(".guide [draft].md.*"))
