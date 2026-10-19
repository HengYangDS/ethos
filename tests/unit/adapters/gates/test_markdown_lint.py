"""Native Markdown lint consumes exact source and preserves formatter-owned layout."""

from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.adapters.gates.native.inputs as native_inputs
import ethos.adapters.gates.tool as gate_tool
from ethos.contracts.gates import load_gate_registry_declaration

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def _quality_files(monkeypatch: pytest.MonkeyPatch, *files: str) -> None:
    monkeypatch.setattr(native_inputs, "quality_source_files", lambda *_args: list(files))


def test_packaged_markdown_gate_uses_shipped_node_tools_and_selected_native_config(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Markdown proof needs no adopter Python recipe or dependency installation."""
    config = tmp_path / ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"
    config.parent.mkdir(parents=True)
    config.write_text("noInlineConfig: true\nconfig:\n  default: false\n")
    (tmp_path / "README.md").write_text("# Current\n\n[Empty link]()\n")
    _quality_files(monkeypatch, "README.md", str(config.relative_to(tmp_path)))
    selected = load_gate_registry_declaration().registry()["markdown-lint"]
    assert selected.command == ()
    assert selected.providers == ("ethos.adapters.gates.tool:markdown_lint_report",)
    report = gate_tool.markdown_lint_report(tmp_path)
    assert report["verdict"] == "block"
    native = report["native"]
    assert len(native) == 3
    assert native[2]["command"][3] == str(config)
    assert all(item["file_count"] == 1 for item in native)
    assert "MD042" in native[1]["stderr"]
    assert native[2]["verdict"] == "pass"


def test_native_markdown_configuration_preserves_nested_rule_parameters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The official CLI consumes nested native parameters, not just Boolean rules."""
    config = tmp_path / ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml"
    config.parent.mkdir(parents=True)
    config.write_text(
        "config:\n  default: false\n  MD024: {siblings_only: true}\n", encoding="utf-8"
    )
    (tmp_path / "README.md").write_text(
        "# Native\n\n## One\n\n### Fixed\n\nWords.\n\n## Two\n\n### Fixed\n\nMore words.\n",
        encoding="utf-8",
    )
    _quality_files(monkeypatch, "README.md", str(config.relative_to(tmp_path)))
    report = gate_tool.markdown_lint_report(tmp_path)
    assert report["verdict"] == "pass", report


def test_common_markdown_policy_accepts_native_formatter_container_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The native fix/check journey has one spacing owner and preserves semantic lint."""
    document = tmp_path / "README.md"
    accepted = b"# Spacing\n\n- First.\n  ```text\n  example\n  ```\n- Second.\n"
    document.write_bytes(accepted)
    _quality_files(monkeypatch, "README.md")

    report = gate_tool.markdown_lint_report(tmp_path)

    assert report["verdict"] == "pass", report
    assert document.read_bytes() == accepted
    native = report["native"]
    assert native[0]["files"] == ["README.md"]
    assert native[0]["required_gaps"] == []
    document.write_bytes(accepted.rstrip(b"\n"))
    refused = gate_tool.markdown_lint_report(tmp_path)
    assert refused["verdict"] == "block"
    assert document.read_bytes() == accepted.rstrip(b"\n")
    fixed, _ignored = gate_tool.render_source_content(
        tmp_path, "README.md", "prettier", document.read_bytes()
    )
    document.write_bytes(fixed)
    assert document.read_bytes() == accepted
    assert gate_tool.markdown_lint_report(tmp_path)["verdict"] == "pass"
    repeated, _ignored = gate_tool.render_source_content(
        tmp_path, "README.md", "prettier", document.read_bytes()
    )
    document.write_bytes(repeated)
    assert document.read_bytes() == accepted
    document.write_text("# Semantic lint\n\n[Empty link]()\n", encoding="utf-8")
    semantic = gate_tool.markdown_lint_report(tmp_path)
    assert semantic["verdict"] == "block"
    assert "MD042" in semantic["native"][1]["stderr"]
