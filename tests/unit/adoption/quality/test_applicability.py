"""Execute native document proof while refusing code hidden behind a document profile."""

from __future__ import annotations

import json
import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment
from tests.support.proof import run_quality_proof

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def document_repository(tmp_path: Path) -> Path:
    """Bind two native document roots to real content and the original tool carrier."""
    repo = init_git_repo(tmp_path / "documents")
    write_active_commitment(repo)
    profile = repo / ".ethos/profile.toml"
    declaration = tomllib.loads(profile.read_text())
    declaration["proof"] = {
        "code_correctness_gates": ["docs-registry", "markdown-links"],
        "gates": [
            {
                "id": "docs-registry",
                "kind": "docs",
                "providers": ["ethos.surface.cli.root.reference:docs_registry_report"],
            },
            {
                "id": "markdown-links",
                "kind": "docs",
                "providers": ["ethos.adapters.gates.tool:markdown_links_report"],
            },
        ],
    }
    profile.write_text(tomli_w.dumps(declaration))
    configuration = repo / ".config/checks/lychee/lychee.toml"
    configuration.parent.mkdir(parents=True, exist_ok=True)
    configuration.write_text("offline = true\nno_progress = true\ninclude_verbatim = false\n")
    document = repo / "docs/handoff.md"
    document.parent.mkdir()
    document.write_text(
        "---\nsubject: documents:handoff\nrole: policy\nstate: canonical\nrelations: {}\n"
        "---\n\n# Handoff\n\n## Evidence\n\nCheck the current source before delivery.\n"
    )
    (repo / "README.md").write_text("# Documents\n\n[Handoff](docs/handoff.md#evidence).\n")
    commit_fixture(repo, "declare native document proof")
    return repo


def test_document_only_profile_executes_both_native_proof_roots(document_repository: Path) -> None:
    """Public proof runs actual document checks without a code package or code-axis map."""
    repo = document_repository
    head = git(repo, "rev-parse", "HEAD")

    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)

    assert result.returncode == 0, result.stderr or result.stdout
    assert payload["verdict"] == "pass"
    assert payload["required_gaps"] == []
    assert [check["action_id"] for check in payload["data"]["checks"]] == [
        "docs-registry",
        "markdown-links",
    ]
    reports = [
        json.loads(check["stdout"])["providers"][0]["report"] for check in payload["data"]["checks"]
    ]
    assert reports[0]["document_count"] == 1
    assert reports[1]["source_tree"] == git(repo, "rev-parse", "HEAD^{tree}")
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""


@pytest.mark.parametrize(
    ("source_path", "source_text", "role_attr"),
    [
        ("app.py", 'raise RuntimeError("not document content")\n', "*.py ethos-role=docs\n"),
        ("run", "#!/bin/sh\nif then\n", ""),
        ("main.ts", "export const answer: = ;\n", "*.ts ethos-role=code\n"),
    ],
    ids=["relabelled-code", "native-script", "declared-code"],
)
def test_document_profile_cannot_omit_observed_code_obligations(
    document_repository: Path, source_path: str, source_text: str, role_attr: str
) -> None:
    """A valid document binding does not waive discovered code or its native evidence."""
    repo = document_repository
    (repo / source_path).write_text(source_text)
    attributes = repo / ".gitattributes"
    attributes.write_text(attributes.read_text() + role_attr)
    head = commit_fixture(repo, "introduce code into the document repository")

    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert payload["data"]["checks"] == []
    assert set(payload["required_gaps"]) == {
        "quality_obligation_unproven:behavior",
        "quality_obligation_unproven:static-analysis",
    }
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""
