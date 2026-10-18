"""Common prose policy is enforced by the native Vale consumer."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import ethos.adapters.gates.native.inputs as native_inputs
import ethos.adapters.gates.tool as gate_tool
from ethos.adapters.process import run_command
from ethos.adapters.repo.runtime.materialization.native_supply import resolve_native_tool
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.repository.paradigm.names import authored_name_gaps
from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    from pathlib import Path


def test_common_vale_policy_enforces_concise_specific_and_correct_prose(tmp_path: Path) -> None:
    """The shipped floor rejects each required defect, not just spelling mistakes."""
    config = canonical_resource(".config/checks/vale/vale.ini")
    assert config.is_file(), "The common native Vale policy must ship with ETHOS."
    executable = resolve_native_tool("vale")
    source = tmp_path / "guide [literal].md"
    source.write_text(
        "# Guide\n\nWe utilize the the data.\n\n"
        "This offers a rich tapestry of insights.\n\nThe qzxwvvv report is ready.\n",
        encoding="utf-8",
    )
    original = source.read_bytes()

    result = run_command(
        tmp_path,
        (
            str(executable),
            "--no-global",
            f"--config={config}",
            "--output=JSON",
            "--no-color",
            str(source),
        ),
        timeout=20,
    )

    assert result.returncode == 1, result.stdout + result.stderr
    assert not result.stderr
    findings = json.loads(result.stdout)
    checks = {item["Check"] for entries in findings.values() for item in entries}
    assert {
        "plain.concise",
        "plain.stock-phrases",
        "Vale.Repetition",
        "Vale.Spelling",
    } <= checks
    assert source.read_bytes() == original


def test_common_vale_policy_names_conform_to_the_shared_paradigm() -> None:
    """Native policy names obey the same naming floor as other authored resources."""
    root = canonical_resource(".config/checks/vale")
    selected = frozenset(
        f".config/checks/vale/{path.relative_to(root).as_posix()}"
        for path in root.rglob("*")
        if path.is_file()
    )
    assert selected
    assert not tuple(authored_name_gaps(load_repository_paradigm(), selected))


def test_common_vale_policy_keeps_code_and_uncertainty_meaning(tmp_path: Path) -> None:
    """Plain-language rules preserve literal code and honest qualifications."""
    config = canonical_resource(".config/checks/vale/vale.ini")
    assert config.is_file(), "The common native Vale policy must ship with ETHOS."
    executable = resolve_native_tool("vale")
    source = tmp_path / "guide.md"
    source.write_text(
        "# Guide\n\nUse `utilize in order to` only as a literal token.\n\n"
        "The request may be rejected when evidence is incomplete.\n",
        encoding="utf-8",
    )
    original = source.read_bytes()

    result = run_command(
        tmp_path,
        (
            str(executable),
            "--no-global",
            f"--config={config}",
            "--output=JSON",
            "--no-color",
            str(source),
        ),
        timeout=20,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not result.stderr
    assert not any(json.loads(result.stdout).values())
    assert source.read_bytes() == original


def test_common_native_vocabulary_preserves_tool_names_and_rejects_misspellings(
    tmp_path: Path,
) -> None:
    """Terms are shared policy rather than duplicated per-repository exceptions."""
    config = canonical_resource(".config/checks/vale/vale.ini")
    executable = resolve_native_tool("vale")
    source = tmp_path / "terms.md"
    source.write_text(
        "# Terms\n\nETHOS, OpenSpec, GitLab and GitHub use a SemVer Changelog.\n\n"
        "Gitlab is a misspelled publisher name.\n",
        encoding="utf-8",
    )
    result = run_command(
        tmp_path,
        (str(executable), "--no-global", f"--config={config}", "--output=JSON", str(source)),
        timeout=20,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    findings = [item for rows in json.loads(result.stdout).values() for item in rows]
    assert any(item["Check"] == "Vale.Terms" for item in findings)
    assert not any(
        item["Check"] == "Vale.Spelling"
        and item["Match"] in {"ETHOS", "OpenSpec", "GitLab", "GitHub", "SemVer", "Changelog"}
        for item in findings
    )


def test_prose_gate_keeps_native_spelling_without_adopter_toolchain(tmp_path, monkeypatch):
    """The installed owner ignores ambient policy and preserves exact authored bytes."""
    gate = load_gate_registry_declaration().registry()["prose"]
    assert gate.providers == ("ethos.adapters.gates.tool:prose_report",)
    assert not gate.command
    document = tmp_path / "README.md"
    local = tmp_path / ".config/checks/codespell/codespell.toml"
    local.parent.mkdir(parents=True)
    local.write_text('[tool.codespell]\nignore-words-list = "teh"\n')
    (tmp_path / "pyproject.toml").write_text('[tool.codespell]\nskip = "*"\n')
    files = ["README.md", local.relative_to(tmp_path).as_posix()]
    monkeypatch.setattr(native_inputs, "quality_source_files", lambda *_args: files)
    monkeypatch.setenv("PATH", "")
    for source, verdict in (
        ("The result is verified.\n", "pass"),
        ("The result is teh result.\n", "block"),
    ):
        document.write_text(source)
        report = gate_tool.prose_report(tmp_path)
        assert (report["verdict"], document.read_text()) == (verdict, source), report
        assert len(report["native"]) == 2
        commands = [result["command"][:4] for result in report["native"]]
        assert commands == [[sys.executable, "-B", "-I", "-m"]] * 2
    assert report["native"][0]["exit_code"] != 0
    assert report["native"][1]["exit_code"] == 0
    local.write_text("[tool.codespell]\nwrite-changes = true\n")
    report = gate_tool.prose_report(tmp_path)
    assert (report["verdict"], document.read_text()) == ("block", source)
    files.clear()
    report = gate_tool.prose_report(tmp_path)
    assert (report["verdict"], report["file_count"]) == ("pass", 0)
