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
        "# Guide\n\nWe utilize the the data.\n\nThis offers a rich tapestry of insights.\n",
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
    assert {"plain.concise", "plain.stock-phrases", "Vale.Repetition"} <= checks
    assert "Vale.Spelling" not in checks
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


def test_common_vale_policy_separates_machine_front_matter_from_human_prose(
    tmp_path: Path,
) -> None:
    """Machine identifiers are inert while human fields retain native diagnostics."""
    config = canonical_resource(".config/checks/vale/vale.ini")
    executable = resolve_native_tool("vale")
    source = tmp_path / "metadata [literal].md"
    contents = (
        "---\nsubject: ethos:docs-registry\nrole: explanation\nstate: canonical\n"
        "relations: {}\nname: ethos-quality-gate-governance\n"
        "title: Quality Guide\ndescription: The report is ready.\n---\n\n"
        "# Guide\n\nUse `teh Github ethos:docs-registry` as literal code.\n"
    )
    source.write_text(contents, encoding="utf-8")
    original = source.read_bytes()
    command = (
        str(executable),
        "--no-global",
        f"--config={config}",
        "--output=JSON",
        "--no-color",
        str(source),
    )

    accepted = run_command(tmp_path, command, timeout=20)

    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert not accepted.stderr
    assert not any(json.loads(accepted.stdout).values())
    assert source.read_bytes() == original

    for correct, defective, expected in (
        (
            "description: The report is ready.",
            "description: The teh report is on Github.",
            {("Vale.Terms", "Github", 8, (35, 40))},
        ),
        (
            "title: Quality Guide",
            "title: teh Github Guide",
            {("Vale.Terms", "Github", 7, (12, 17))},
        ),
    ):
        source.write_text(contents.replace(correct, defective), encoding="utf-8")
        original = source.read_bytes()

        rejected = run_command(tmp_path, command, timeout=20)

        assert rejected.returncode == 1, rejected.stdout + rejected.stderr
        assert not rejected.stderr
        findings = json.loads(rejected.stdout)
        assert set(findings) == {str(source)}
        assert expected <= {
            (item["Check"], item["Match"], item["Line"], tuple(item["Span"]))
            for item in findings[str(source)]
        }, rejected.stdout
        assert all(item["Line"] in {7, 8} for item in findings[str(source)])
        assert source.read_bytes() == original


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
        spelling = [result for result in report["native"] if result["tool"] == sys.executable]
        assert [result["command"][:4] for result in spelling] == [
            [sys.executable, "-B", "-I", "-m"]
        ] * 2
    assert [result["exit_code"] != 0 for result in spelling] == [True, False]
    local.write_text("[tool.codespell]\nwrite-changes = true\n")
    report = gate_tool.prose_report(tmp_path)
    assert (report["verdict"], document.read_text()) == ("block", source)
    files.clear()
    report = gate_tool.prose_report(tmp_path)
    assert (report["verdict"], report["file_count"]) == ("pass", 0)


def test_prose_gate_runs_the_shipped_and_repository_vale_policy(tmp_path, monkeypatch):
    """Plain-language findings block beside spelling; each repository policy adds its own rules."""
    document = tmp_path / "README.md"
    local = tmp_path / ".config/checks/vale/vale.ini"
    files = ["README.md"]
    monkeypatch.setattr(native_inputs, "quality_source_files", lambda *_args: files)
    monkeypatch.setenv("PATH", "")
    for source, verdict in (
        ("We use the data to decide.\n", "pass"),
        ("We utilize the data to decide.\n", "block"),
    ):
        document.write_text(source)
        report = gate_tool.prose_report(tmp_path)
        assert (report["verdict"], document.read_text()) == (verdict, source), report
        assert [result["id"] for result in report["native"]] == ["prose", "prose-vale"]
    assert "quality_gate_failed:prose-vale" in report["required_gaps"]
    local.parent.mkdir(parents=True)
    local.write_text("[*.md]\nBasedOnStyles = Vale\nVale.Spelling = error\n")
    files.append(local.relative_to(tmp_path).as_posix())
    document.write_text("We use the qzxwvvv data to decide.\n")
    report = gate_tool.prose_report(tmp_path)
    assert [result["id"] for result in report["native"]] == [
        "prose",
        "prose-vale",
        "prose-vale-increment",
    ]
    assert report["required_gaps"] == ["quality_gate_failed:prose-vale-increment"], report
    local.write_text("[*.md]\nBasedOnStyles = Missing\n")
    report = gate_tool.prose_report(tmp_path)
    assert report["native"][-1]["required_gaps"] == [
        "quality_gate_failed:prose-vale-increment",
        "native_prose_not_read_only_clean",
    ], report
