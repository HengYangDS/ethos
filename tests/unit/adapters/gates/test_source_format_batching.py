"""Native check runs vouch for clean files; every other file still renders alone."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.gates.formatting as formatting_gate
from ethos.adapters.gates.formatting import prepare_source_format
from tests.support.governed_repository import prepared_work_lane

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def _write(root: Path, files: Mapping[str, str]) -> None:
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


@pytest.fixture
def lane(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    return prepared_work_lane(tmp_path, name="format").worktree


def test_clean_selection_costs_the_same_native_checks_at_any_size(
    lane: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each formatter checks a clean selection in one native run, however many files it owns."""
    launched: list[tuple[str, ...]] = []
    native = formatting_gate.run_command

    def recorded(root: Path, command: tuple[str, ...], **options: Any) -> Any:
        launched.append(command)
        return native(root, command, **options)

    monkeypatch.setattr(formatting_gate, "run_command", recorded)
    counts = []
    for size in (2, 6):
        sources = {
            **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(size)},
            **{f"src/module{index}.py": f"VALUE = {index}\n" for index in range(size)},
            **{f"settings{index}.toml": f"value = {index}\n" for index in range(size)},
        }
        _write(lane, sources)
        launched.clear()
        report = formatting_gate.source_format_report(lane, paths=tuple(sources))
        assert (report["verdict"], report["changed_paths"]) == ("pass", []), report
        counts.append(len(launched))
    assert counts[0] == counts[1], launched


def test_drift_in_a_clean_selection_keeps_its_exact_native_postimage(lane: Path) -> None:
    """A checked run that finds drift still renders and reports only the drifting file."""
    sources = {
        **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(3)},
        "docs/drift.md": "# Drift\n\ntext   \n",
        "src/clean.py": "VALUE = 1\n",
        "src/drift.py": "value=2\n",
    }
    _write(lane, sources)
    report = formatting_gate.source_format_report(lane, paths=tuple(sources))
    assert report["changed_paths"] == ["docs/drift.md", "src/drift.py"], report
    postimages = {
        item.path: item.after for item in prepare_source_format(lane, paths=tuple(sources))
    }
    assert postimages["docs/drift.md"] == b"# Drift\n\ntext\n"
    assert postimages["src/drift.py"] == b"value = 2\n"
    assert all(
        postimages[path] == content.encode()
        for path, content in sources.items()
        if "drift" not in path
    )


def test_listed_markdown_drift_renders_only_the_listed_file(
    lane: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Prettier names each drifting file, so its clean neighbours never render alone."""
    rendered: list[str] = []
    native = formatting_gate.render_source_content

    def recorded(root: Path, relative: str, *arguments: Any, **options: Any) -> Any:
        rendered.append(relative)
        return native(root, relative, *arguments, **options)

    monkeypatch.setattr(formatting_gate, "render_source_content", recorded)
    sources = {
        **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(4)},
        "docs/drift.md": "# Drift\n\ntext   \n",
    }
    _write(lane, sources)
    report = formatting_gate.source_format_report(lane, paths=tuple(sources))
    assert report["changed_paths"] == ["docs/drift.md"], report
    assert rendered == ["docs/drift.md"]


@pytest.mark.skipif(os.name == "nt", reason="a backslash separates Windows paths")
def test_a_toml_path_taplo_does_not_collect_still_renders_alone(lane: Path) -> None:
    """Taplo's clean exit vouches only for the files it reports collecting.

    Taplo globs each named path, so it collects no file whose name holds a backslash, as it
    collects none on Windows, where it joins every name onto the backslash working directory.
    """
    sources = {"settings/plain.toml": "value = 1\n", "settings/back\\slash.toml": "value   =   2\n"}
    _write(lane, sources)
    report = formatting_gate.source_format_report(lane, paths=tuple(sources))
    assert report["changed_paths"] == ["settings/back\\slash.toml"], report
