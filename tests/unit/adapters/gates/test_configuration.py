"""Native configuration and Markdown quality use shipped policy without source tooling."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.gates.tool as tool
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("relative", "content", "verdict"),
    [
        ("source.json", '{\n  "value": true\n}\n', "pass"),
        ("source.json", '{"value":true}\n', "block"),
        ("source.json", '{\n  "values": [\n    1,\n    2\n  ]\n}\n', "pass"),
        ("system/schemas/contracts/example.schema.json", '{"type":"object"}\n', "pass"),
        ("source.yaml", "---\nvalue: true\n", "pass"),
        ("source.yaml", "---\nvalue: |\n  first\n\n\n  second\n", "pass"),
        ("source.yaml", "---\nvalue: 1\nvalue: 2\n", "block"),
    ],
)
def test_shipped_configuration_quality_checks_exact_inputs_without_writes(
    tmp_path: Path, relative: str, content: str, verdict: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    assert callable(getattr(tool, "native_configurations", None))
    owner = import_module("ethos.adapters.gates.configuration")
    report = owner.configuration_report(root, paths=(relative,))
    assert report["verdict"] == verdict, report
    assert report["file_count"] == 1
    assert bool(report["required_gaps"]) == (verdict == "block")
    assert path.read_text() == content


@pytest.mark.parametrize(
    ("content", "verdict"),
    [("# Current\n\nThis is maintained prose.\n", "pass"), ("# Current\n\n[Broken]()\n", "block")],
)
def test_shipped_markdown_quality_runs_without_repository_nox(
    tmp_path: Path, content: str, verdict: str
) -> None:
    root = init_git_repo(tmp_path / "repo")
    path = root / "README.md"
    path.write_text(content)
    commit_fixture(root, "declare native document inputs")
    provider = import_module("ethos.adapters.gates.markdown").markdown_format_report
    assert callable(provider)
    originals = {source: source.read_bytes() for source in root.glob("*.md")}
    report = provider(root)
    assert report["verdict"] == verdict, report
    assert report["file_count"] == len(originals)
    assert bool(report["required_gaps"]) == (verdict == "block")
    assert all(source.read_bytes() == original for source, original in originals.items())
    assert not (root / "noxfile.py").exists()
