"""Native check runs vouch for clean files; every other file still renders alone."""

from __future__ import annotations

import os
import subprocess
from typing import TYPE_CHECKING
from typing import Any

import pytest

import ethos.adapters.gates.format_checks as format_checks
import ethos.adapters.gates.formatting as formatting_gate
import ethos.adapters.gates.native.inputs as native_inputs
import ethos.adapters.gates.tool as gate_tool
from ethos.adapters.gates.formatting import prepare_source_format
from tests.support.governed_repository import write_tree

if TYPE_CHECKING:
    from pathlib import Path


def _recorded_launches(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Record every native run that the format gate and its bulk checks start."""
    launched: list[tuple[str, ...]] = []
    native = format_checks.run_command

    def recorded(root: Path, command: tuple[str, ...], **options: Any) -> Any:
        launched.append(command)
        return native(root, command, **options)

    monkeypatch.setattr(format_checks, "run_command", recorded)
    return launched


def test_clean_selection_costs_the_same_native_checks_at_any_size(
    lane: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Each formatter checks a clean selection in one native run, however many files it owns."""
    launched = _recorded_launches(monkeypatch)
    counts = []
    for size in (2, 6):
        sources = {
            **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(size)},
            **{f"src/module{index}.py": f"VALUE = {index}\n" for index in range(size)},
            **{f"settings{index}.toml": f"value = {index}\n" for index in range(size)},
        }
        write_tree(lane, sources)
        launched.clear()
        report = formatting_gate.source_format_report(lane, paths=tuple(sources))
        assert (report["verdict"], report["changed_paths"]) == ("pass", []), report
        counts.append(len(launched))
    assert counts[0] == counts[1], launched


def test_a_clean_selection_lists_the_repository_equally_often_at_any_size(
    lane: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A configuration is a fact of the tree: no gate lists the repository once for each file."""
    listings: list[tuple[str, ...]] = []
    native = native_inputs.git_files

    def recorded(root: Path, *arguments: str, **options: Any) -> Any:
        listings.append(arguments)
        return native(root, *arguments, **options)

    monkeypatch.setattr(native_inputs, "git_files", recorded)
    counts = []
    for size in (2, 6):
        sources = {f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(size)}
        write_tree(lane, sources)
        listings.clear()
        report = formatting_gate.source_format_report(lane, paths=tuple(sources))
        assert (report["verdict"], report["changed_paths"]) == ("pass", []), report
        formatted = len(listings)
        lint = gate_tool.markdown_lint_report(lane)
        assert lint["native"][0]["required_gaps"] == [], lint
        counts.append((formatted, len(listings) - formatted))
    assert counts[0] == counts[1], counts


def test_a_clean_selection_under_an_ignore_file_costs_the_same_at_any_size(
    lane: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A repository's Prettier ignore file is asked about every file in one native run."""
    launched = _recorded_launches(monkeypatch)
    counts = []
    for size in (2, 6):
        sources = {
            ".config/checks/prettier/prettierignore": "../../../docs/untouched.md\n",
            "docs/untouched.md": "# Untouched\n\n\n\ntext   \n",
            **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(size)},
        }
        write_tree(lane, sources)
        launched.clear()
        pages = tuple(name for name in sources if name.endswith(".md"))
        report = formatting_gate.source_format_report(lane, paths=pages)
        assert (report["verdict"], report["changed_paths"]) == ("pass", []), report
        assert report["ignored_paths"] == ["docs/untouched.md"], report
        counts.append(len(launched))
    assert counts[0] == counts[1], launched


def test_under_an_ignore_file_drift_is_reported_and_an_excluded_file_is_left(lane: Path) -> None:
    """The one run that reads the ignore file changes no verdict and no postimage."""
    sources = {
        ".config/checks/prettier/prettierignore": "../../../docs/untouched.md\n",
        "docs/untouched.md": "# Untouched\n\n\n\ntext   \n",
        "docs/drift.md": "# Drift\n\ntext   \n",
        **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(3)},
    }
    write_tree(lane, sources)
    pages = tuple(name for name in sources if name.endswith(".md"))
    report = formatting_gate.source_format_report(lane, paths=pages)
    assert report["changed_paths"] == ["docs/drift.md"], report
    assert report["ignored_paths"] == ["docs/untouched.md"], report
    postimages = {item.path: item.after for item in prepare_source_format(lane, paths=pages)}
    assert postimages["docs/drift.md"] == b"# Drift\n\ntext\n"
    assert postimages["docs/untouched.md"] == sources["docs/untouched.md"].encode()


def test_drift_in_a_clean_selection_keeps_its_exact_native_postimage(lane: Path) -> None:
    """A checked run that finds drift still renders and reports only the drifting file."""
    sources = {
        **{f"docs/page{index}.md": f"# Page {index}\n\nText.\n" for index in range(3)},
        "docs/drift.md": "# Drift\n\ntext   \n",
        "src/clean.py": "VALUE = 1\n",
        "src/drift.py": "value=2\n",
    }
    write_tree(lane, sources)
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
    write_tree(lane, sources)
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
    write_tree(lane, sources)
    report = formatting_gate.source_format_report(lane, paths=tuple(sources))
    assert report["changed_paths"] == ["settings/back\\slash.toml"], report


def test_a_selection_without_a_prettier_file_leaves_the_ignore_carrier_unread(
    lane: Path, tmp_path: Path
) -> None:
    """A linked Prettier ignore carrier refuses only a selection that holds a Prettier file."""
    write_tree(lane, {"src/module.py": "VALUE = 1\n"})
    (tmp_path / "linked-prettierignore").write_text("", encoding="utf-8")
    carrier = lane / ".config/checks/prettier/prettierignore"
    carrier.parent.mkdir(parents=True, exist_ok=True)
    carrier.symlink_to(tmp_path / "linked-prettierignore")
    report = formatting_gate.source_format_report(lane, paths=("src/module.py",))
    assert (report["verdict"], report["required_gaps"]) == ("pass", []), report


@pytest.mark.parametrize("status", [0, 1])
def test_an_ignore_query_warning_refuses_nothing_and_a_failure_carries_its_text(
    lane: Path, monkeypatch: pytest.MonkeyPatch, status: int
) -> None:
    """A warning on standard error refuses no selection; a failed query's gap says it whole."""
    native = format_checks.run_command

    def stub(root: Path, command: tuple[str, ...], **options: Any) -> Any:
        completed = native(root, command, **options)
        if not command[1].endswith("prettier-ignored.mjs"):
            return completed
        warning = b"(node:7) Warning: stub\n"
        return subprocess.CompletedProcess(command, status, completed.stdout, warning)

    monkeypatch.setattr(format_checks, "run_command", stub)
    write_tree(lane, {".config/checks/prettier/prettierignore": "", "docs/page.md": "# Page\n"})
    report = formatting_gate.source_format_report(lane, paths=("docs/page.md",))
    assert (report["verdict"] == "pass") is (status == 0), report
    assert ("Warning: stub" in str(report["required_gaps"])) is (status == 1), report


def test_one_file_refusing_its_postimage_keeps_the_drift_the_earlier_files_showed(
    lane: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A refusal no longer hides the gaps that the files prepared before it already computed."""
    write_tree(
        lane,
        {
            ".config/checks/prettier/prettierignore": "",
            "docs/a.md": "# A\n",
            "docs/b.md": "# B\n",
        },
    )
    render = formatting_gate.render_source_content
    refused: set[str] = set()

    def stub(
        root: Path, relative: str, owner: str, content: bytes, **options: Any
    ) -> tuple[bytes, bool]:
        if refused:
            message = f"policy conflict in {relative}"
            raise ValueError(message)
        refused.add(relative)
        # The first file's postimage differs from its source, so it holds a drift to report.
        drifted = render(root, relative, owner, content, **options)[0] + b"\n"
        return drifted, False

    monkeypatch.setattr(formatting_gate, "render_source_content", stub)

    def nobody_is_clean(*_args: object, **_options: object) -> frozenset[str]:
        return frozenset()

    monkeypatch.setattr(formatting_gate, "checked_clean", nobody_is_clean)
    report = gate_tool.markdown_lint_report(lane)
    format_report = next(item for item in report["native"] if item["id"] == "markdown-format")
    gaps = format_report["required_gaps"]
    drifted = [gap for gap in gaps if str(gap).startswith("source_format_drift:")]
    assert len(drifted) == 1, format_report
    assert any("policy conflict in" in str(gap) for gap in gaps), format_report
