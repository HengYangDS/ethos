"""Installed document quality uses one native production supply and policy."""

from __future__ import annotations

import json
import subprocess
from importlib import import_module
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.content.source import SourceTree
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.gates import Gate
from ethos.repository.policy.gates import source_paths_for_gate
from ethos.repository.release.resources import canonical_resource
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_document_tools_have_complete_production_supply() -> None:
    """An installed adopter does not need the product developer toolchain."""
    for tool, entry in (
        ("prettier", "bin/prettier.cjs"),
        ("markdownlint-cli2", "markdownlint-cli2.mjs"),
    ):
        package = product_node_module(tool)
        assert (package / entry).is_file()
        metadata = json.loads((package / "package.json").read_text(encoding="utf-8"))
        assert metadata["name"] == tool
    for carrier in (
        ".config/checks/prettier/prettier.toml",
        ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
    ):
        assert canonical_resource(carrier).is_file()


def test_document_format_check_is_native_nonmutating_and_ambient_independent(
    tmp_path: Path,
) -> None:
    """The same source fails layout despite a candidate's disabling config."""
    repo = init_git_repo(tmp_path / "repository")
    guide = repo / "README.md"
    guide.write_text("# Guide\n\n\nRead the evidence.\n", encoding="utf-8")
    (repo / ".prettierrc.json").write_text('{"proseWrap":"always"}\n')
    (repo / ".markdownlint.json").write_text('{"default":false}\n')
    commit_fixture(repo, "declare an unformatted document")
    original = guide.read_bytes()

    report = import_module("ethos.adapters.gates.markdown").markdown_format_report(repo)

    assert report["verdict"] == "block", report
    assert report["checked_paths"] == sorted(
        path for path in SourceTree.observe(repo).entries if path.endswith(".md")
    )
    assert "README.md" in report["format_drift"]
    assert report["required_gaps"]
    assert guide.read_bytes() == original


def test_native_document_diagnostics_bind_literal_delivered_paths(tmp_path: Path) -> None:
    """Native CLI2 findings retain the exact selected filename, not the launch cwd."""
    owner = import_module("ethos.adapters.gates.markdown")
    sources = {"docs/native [input].md": "# Guide\n\nRead [the result]().\n"}
    observed = owner.native_document_observation(tmp_path, sources)
    assert observed["lint_exit"] == 1
    assert observed["findings"]
    assert {finding["fileName"] for finding in observed["findings"]} == set(sources)
    assert any("MD042" in finding["ruleNames"] for finding in observed["findings"])


def test_native_formatter_preserves_containers_and_lint_compatible_layout(tmp_path: Path) -> None:
    """Native Prettier defines list and quote structure, including byte-exact examples."""
    owner = import_module("ethos.adapters.gates.markdown")
    source = (
        "# Guide\n\n"
        "- First item.\n\n  A separate paragraph.\n\n- Second item.\n\n"
        "> First quoted paragraph.\n>\n> A separate quoted paragraph.\n\n"
        "<!-- prettier-ignore -->\n"
        "| exact | example |\n| - | - |\n| x | y |\n"
    )
    first = owner.native_document_observation(tmp_path, {"guide.md": source})
    canonical = first["formatted"]["guide.md"]
    second = owner.native_document_observation(tmp_path, {"guide.md": canonical})
    assert second["formatted"]["guide.md"] == canonical
    assert second["lint_exit"] == 0, second
    assert second["findings"] == []
    assert ">\n> A separate quoted paragraph." in canonical
    assert "| exact | example |\n| - | - |\n| x | y |" in canonical


@pytest.mark.parametrize(
    "path", ["../outside.md", "/outside.md", "docs/../guide.md", "docs\\guide.md"]
)
def test_native_document_selection_rejects_unbound_paths(tmp_path: Path, path: str) -> None:
    """Only canonical repository-relative identities can become native input keys."""
    owner = import_module("ethos.adapters.gates.markdown")
    with pytest.raises(ValueError, match="markdown_input_path_invalid"):
        owner.native_document_observation(tmp_path, {path: "# Guide\n"})


def test_native_document_format_subset_is_explicit(tmp_path: Path) -> None:
    """An unrelated format key cannot masquerade as a checked authoring input."""
    owner = import_module("ethos.adapters.gates.markdown")
    with pytest.raises(ValueError, match="markdown_format_selection_invalid"):
        owner.native_document_observation(
            tmp_path, {"guide.md": "# Guide\n"}, format_paths=("missing.md",)
        )


def test_native_document_payload_retains_rule_details_and_rejects_false_eof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A native report needs a terminal marker and exact source/output identities."""
    owner = import_module("ethos.adapters.gates.markdown")
    base = owner.native_document_observation(
        tmp_path, {"guide.md": "# Guide\n\nRead [the result]().\n"}
    )
    native = {key: value for key, value in base.items() if key not in ("command", "stderr")}
    assert base["findings"][0]["ruleDescription"] == "No empty links"
    for update in ({"lint_reported": False}, {"lint_exit": True}, {"formatted": {}}):
        payload = {**native, **update}
        monkeypatch.setattr(
            owner,
            "run_command",
            lambda *_args, payload=payload, **_kwargs: subprocess.CompletedProcess(
                [], 0, json.dumps(payload), ""
            ),
        )
        with pytest.raises(ValueError, match="markdown_native_report_invalid"):
            owner.native_document_observation(tmp_path, {"guide.md": "# Guide\n"})


def test_document_inputs_reject_empty_selection(tmp_path: Path) -> None:
    """An empty native document selection is not a successful document check."""
    owner = import_module("ethos.adapters.gates.markdown")
    with pytest.raises(ValueError, match="markdown_input_selection_empty"):
        owner.document_inputs(SourceTree(tmp_path, "head", "tree", {}))


def test_document_check_refuses_drift_and_keeps_untracked_bytes_out(tmp_path: Path) -> None:
    """Native checks observe the same committed subject before and after execution."""
    repo = init_git_repo(tmp_path / "repository")
    (repo / "README.md").write_text("# Guide\n\nRead the evidence.\n", encoding="utf-8")
    commit_fixture(repo, "declare document source")
    (repo / "untracked.md").write_text("# Untracked\n", encoding="utf-8")
    owner = import_module("ethos.adapters.gates.markdown")
    report = owner.markdown_format_report(repo)
    assert report["verdict"] == "pass", report
    assert "untracked.md" not in report["checked_paths"]
    (repo / "README.md").write_text("# Changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match=r"source_member_changed:README\.md"):
        owner.markdown_format_report(repo)


def test_native_prose_binds_literal_source_and_ignores_candidate_policy(tmp_path: Path) -> None:
    """Shipped Vale policy finds actual errors without trusting candidate disabling files."""
    repo = init_git_repo(tmp_path / "repository")
    guide = repo / "docs/native [input].md"
    guide.parent.mkdir()
    guide.write_text("# Guide\n\nRead the teh teh result.\n", encoding="utf-8")
    (repo / ".vale.ini").write_text("[*.md]\nBasedOnStyles =\n", encoding="utf-8")
    commit_fixture(repo, "declare prose source")
    original = guide.read_bytes()
    owner = import_module("ethos.adapters.gates.markdown")
    report = owner.markdown_prose_report(repo)
    assert report["verdict"] == "block", report
    assert "docs/native [input].md" in report["findings"]
    assert all(finding["Line"] == 3 for finding in report["findings"]["docs/native [input].md"])
    assert guide.read_bytes() == original


def test_native_prose_rejects_active_policy_and_preserves_literal_examples(tmp_path: Path) -> None:
    """Only active native HTML controls can suppress prose; code examples stay literal."""
    repo = init_git_repo(tmp_path / "repository")
    guide = repo / "README.md"
    owner = import_module("ethos.adapters.gates.markdown")
    literal = "# Guide\n\nUse `<!-- vale off -->` as code.\n\n```html\n<!-- vale off -->\n```\n"
    guide.write_text(literal, encoding="utf-8")
    assert owner.working_document_report(repo, kind="prose")["verdict"] == "pass"
    for directive in ("vale off", "vale Vale.Spelling = NO"):
        guide.write_text(f"# Guide\n\n<!-- {directive} -->\n\nUse teh result.\n", encoding="utf-8")
        original = guide.read_bytes()
        with pytest.raises(ValueError, match="markdown_prose_inline_policy_forbidden:README"):
            owner.working_document_report(repo, kind="prose")
        assert guide.read_bytes() == original


@pytest.mark.parametrize(
    "fault",
    ["boolean-exit", "empty-failure", "false-success", "line", "span", "missing-match", "message"],
)
def test_native_prose_refuses_contradictory_or_unbound_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault: str
) -> None:
    """A provider preserves native failures and cannot admit forged success or positions."""
    repo = init_git_repo(tmp_path / "repository")
    (repo / "README.md").write_text("# Guide\n\nUse teh result.\n", encoding="utf-8")
    owner = import_module("ethos.adapters.gates.markdown")
    original = owner.run_command

    def inject(*args, **kwargs):
        result = original(*args, **kwargs)
        if "ls-config" in result.args:
            return result
        rows = json.loads(result.stdout)
        entry = next(iter(rows.values()))[0]
        if fault in {"boolean-exit", "empty-failure"}:
            result.returncode = False if fault == "boolean-exit" else 1
            rows = {}
        elif fault == "false-success":
            result.returncode = 0
        elif fault == "line":
            entry["Line"] = 999
        elif fault == "span":
            entry["Span"] = [900, 909]
        elif fault == "missing-match":
            entry.pop("Match")
        else:
            entry["Message"] = ""
        result.stdout = json.dumps(rows)
        return result

    monkeypatch.setattr(owner, "run_command", inject)
    report = owner.working_document_report(repo, kind="prose")
    assert report["verdict"] == "block", report
    assert report["state"] == "native_report_invalid"
    assert report["stdout"]


def test_native_prose_preserves_original_execution_diagnostics(tmp_path: Path) -> None:
    """Invalid source syntax retains the actual native exit and diagnostic bytes."""
    repo = init_git_repo(tmp_path / "repository")
    (repo / "README.md").write_text("---\ntitle: [\n---\n\n# Guide\n", encoding="utf-8")
    owner = import_module("ethos.adapters.gates.markdown")
    report = owner.working_document_report(repo, kind="prose")
    assert report["verdict"] == "block"
    assert report["state"] == "native_execution_failed"
    assert report["exit_code"] == 2
    assert "E201" in report["stdout"] + report["stderr"]


def test_document_gates_use_product_native_providers() -> None:
    """Installed adopters consume document checks without the product's Nox tree."""
    gate = Gate(
        id="markdown-format",
        kind="lint",
        providers=("ethos.adapters.gates.markdown:markdown_format_report",),
        profile="repository",
        execution_mode="provider",
        tool_adapter="ethos",
    )
    assert gate.execution_mode == "provider"
    assert not gate.command
    assert not gate.writes_files
    assert "@ethos/adapters/gates/markdown.py" in source_paths_for_gate(gate)


@pytest.mark.parametrize("profile", ["product", "repository"])
def test_document_gate_binding_covers_native_policy_and_script_inputs(profile: str) -> None:
    """The gate identity binds its native program, locked supply and effective policy."""
    gate = Gate(
        id="markdown-format",
        kind="lint",
        providers=("ethos.adapters.gates.markdown:markdown_format_report",),
        profile=profile,
        execution_mode="provider",
        tool_adapter="ethos",
    )
    formatting = set(source_paths_for_gate(gate))
    prose = set(
        source_paths_for_gate(
            gate.model_copy(
                update={"providers": ("ethos.adapters.gates.markdown:markdown_prose_report",)}
            )
        )
    )
    source = "@ethos/" if profile == "repository" else "src/ethos/"
    resource = "@ethos/resources/" if profile == "repository" else ""
    assert source + "adapters/gates/markdown.mjs" in formatting
    assert {
        ".config/mise/config.toml",
        ".config/mise/mise.lock",
        "package.json",
        "package-lock.json",
        ".config/checks/prettier/prettier.toml",
        ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
    } <= {path.removeprefix(resource) for path in formatting}
    assert {
        ".config/mise/config.toml",
        ".config/mise/mise.lock",
        ".config/checks/vale/vale.ini",
        ".config/checks/vale/styles/plain/concise.yml",
        ".config/checks/vale/styles/plain/stock-phrases.yml",
        ".config/checks/vale/styles/config/vocabularies/common/accept.txt",
        ".config/checks/vale/styles/config/vocabularies/common/reject.txt",
    } <= {path.removeprefix(resource) for path in prose}


def test_prose_checks_current_source_but_keeps_official_history_distinct(tmp_path: Path) -> None:
    """Archived wording is not a current style claim; current Changes still are."""
    repo = init_git_repo(tmp_path / "repository")
    for path, body in {
        "README.md": "# Guide\n\nRead the evidence.\n",
        "openspec/changes/archive/2026-01-01-old/tasks.md": "# Tasks\n\nUse teh result.\n",
        "openspec/changes/current/tasks.md": "# Tasks\n\nUse teh result.\n",
    }.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    commit_fixture(repo, "declare current and historical prose")
    report = import_module("ethos.adapters.gates.markdown").markdown_prose_report(repo)
    assert report["verdict"] == "block", report
    assert "openspec/changes/current/tasks.md" in report["checked_paths"]
    assert "openspec/changes/archive/2026-01-01-old/tasks.md" not in report["checked_paths"]


def test_authoring_document_check_uses_live_source_without_claiming_committed_proof(
    tmp_path: Path,
) -> None:
    """Fix/check authoring sees exact dirty and untracked inputs, leaving proof distinct."""
    repo = init_git_repo(tmp_path / "repository")
    guide = repo / "README.md"
    guide.write_text("# Guide\n\nRead the evidence.\n", encoding="utf-8")
    commit_fixture(repo, "declare clean authoring baseline")
    guide.write_text("# Guide\n\n\nRead the evidence.\n", encoding="utf-8")
    extra = repo / "candidate [literal].md"
    extra.write_text("# Candidate\n\nUse teh result.\n", encoding="utf-8")
    original = {path: path.read_bytes() for path in (guide, extra)}
    owner = import_module("ethos.adapters.gates.markdown")
    format_report = owner.working_document_report(repo, kind="format")
    prose_report = owner.working_document_report(repo, kind="prose")
    assert format_report["verdict"] == prose_report["verdict"] == "block"
    assert format_report["input_kind"] == prose_report["input_kind"] == "working-tree"
    assert format_report["source_tree"] == prose_report["source_tree"] == ""
    assert "candidate [literal].md" in prose_report["checked_paths"]
    assert guide.read_bytes() == original[guide]
    assert extra.read_bytes() == original[extra]
    with pytest.raises(ValueError, match=r"source_member_size_exceeded:README\.md"):
        owner.markdown_format_report(repo)
