"""Decision identity is a portable Docs Registry obligation, not a second index."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.git import run_git
from ethos.repository.registry.docs.health import docs_health_report
from ethos.repository.registry.docs.registry import build_docs_registry
from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _document(subject: str, role: str, title: str) -> str:
    if role == "decision":
        number = match[1] if (match := re.match(r"dr-([0-9]{4})-", title)) else "0001"
        return _decision(f"DR-{number}", subject=subject)
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: canonical\nrelations: {{}}\n"
        f"---\n\n# {title}\n\nStatus: canonical.\n\nPurpose: exercise decision identity.\n"
    )


def _decision(identity: str = "DR-0001", *, subject: str = "sample:decision") -> str:
    return (
        f"---\nsubject: {subject}\nrole: decision\nstate: canonical\n"
        f"decision_id: {identity}\ndecision_status: accepted\nrelations: {{}}\n---\n\n"
        f"# {identity}: Shared rationale\n\n"
        "## Context\n\nA lasting choice needs an explicit reason.\n\n"
        "## Decision\n\nKeep rationale with its semantic owner.\n\n"
        "## Alternatives Rejected\n\nAn execution log cannot explain the trade-off.\n\n"
        "## Consequences and Boundary\n\nCurrent behavior stays with the contract.\n\n"
        "## Evidence and Revisit\n\nRevisit when the original assumptions change.\n"
    )


@pytest.mark.parametrize(
    ("names", "expected"),
    [
        (["dr-0006-proof-trust-boundary.md"], []),
        (
            ["proof-trust-boundary.md"],
            ["docs_decision_name_invalid:docs/decisions/proof-trust-boundary.md"],
        ),
        (["dr-0000-invalid.md"], ["docs_decision_name_invalid:docs/decisions/dr-0000-invalid.md"]),
        (
            ["dr-0006-first.md", "dr-0006-second.md"],
            [
                "docs_decision_id_duplicate:0006:docs/decisions/dr-0006-first.md,docs/decisions/dr-0006-second.md"
            ],
        ),
    ],
)
def test_decision_records_have_stable_unique_numbered_names(
    tmp_path: Path, names: list[str], expected: list[str]
) -> None:
    """The existing docs owner checks record identity without another registry."""
    decisions = tmp_path / "docs/decisions"
    decisions.mkdir(parents=True)
    for name in names:
        (decisions / name).write_text(_document(f"sample:decision:{name}", "decision", name))
    entrance = _document("sample:decisions", "index", "Decisions")
    entrance += "".join(f"\n- [{name}]({name})" for name in names) + "\n"
    (decisions / "README.md").write_text(entrance)
    run_git(tmp_path, "init", "--quiet")
    run_git(tmp_path, "add", "docs")

    report = docs_registry_report(tmp_path)

    assert [gap for gap in report["required_gaps"] if gap.startswith("docs_decision_")] == expected


def test_adopter_native_docs_root_uses_the_same_decision_identity_rule(tmp_path: Path) -> None:
    """Decision identity is portable without imposing ETHOS's directory path."""
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'sample'\n[roots]\ndocs = 'handbook'\n")
    decisions = tmp_path / "handbook/rulings"
    decisions.mkdir(parents=True)
    (decisions / "choice.md").write_text(_document("sample:decision:choice", "decision", "Choice"))
    run_git(tmp_path, "init", "--quiet")
    run_git(tmp_path, "add", ".ethos/profile.toml", "handbook")

    report = docs_registry_report(tmp_path)

    assert "docs_decision_name_invalid:handbook/rulings/choice.md" in report["required_gaps"]


@pytest.mark.parametrize("valid_identity", [False, True])
def test_public_docs_gate_blocks_invalid_decision_record(
    tmp_path: Path, *, valid_identity: bool
) -> None:
    """The CLI cannot prove an unstable identity or incomplete decision rationale."""
    root = init_git_repo(tmp_path / "repo")
    filename = "dr-0001-rationale.md" if valid_identity else "choice.md"
    decision = root / "docs/rulings" / filename
    decision.parent.mkdir(parents=True)
    source = _document("sample:decision:choice", "decision", "Choice")
    if valid_identity:
        source = source.replace(
            "## Alternatives Rejected\n\nAn execution log cannot explain the trade-off.\n\n",
            "",
        )
    decision.write_text(source)
    commit_fixture(root, "invalid decision")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    provider = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]

    assert result.returncode != 0
    assert report["verdict"] == "block"
    assert report["summary"]["proof_attestation_issued"] is False
    gap = "sections" if valid_identity else "name"
    assert provider["required_gaps"] == [f"docs_decision_{gap}_invalid:docs/rulings/{filename}"]
    assert decision.read_text() == source


@pytest.mark.parametrize("commented", [False, True])
def test_shared_decision_contract_preserves_metadata_and_readable_rationale(
    tmp_path: Path, *, commented: bool
) -> None:
    """A native root keeps the same decision contract and ordinary evidence prose."""
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = 'sample'\n[roots]\ndocs = 'handbook'\n")
    path = tmp_path / "handbook/dr-0001-rationale.md"
    path.parent.mkdir()
    source = _decision().replace(
        "Current behavior stays with the contract.",
        "Each repository's profile owns current behavior;\n"
        "this soft wrap remains one rationale paragraph. `node` names a host; "
        "`./tools/check.py` is an evidence path.\n\n"
        "| Choice | Reason |\n| --- | --- |\n| Shared owner | One quality floor |\n\n"
        "> This independent quotation preserves a reason\n\n"
        "Rationale remains with the owner\n\n"
        "See docs/proof.md for the evidence.\n\n"
        "The evidence [source `git status`](https://example.test/decision) "
        "is not a procedure.",
    )
    if commented:
        metadata, body = source.split("\n---\n", 1)
        source = f"<!--\n{metadata}\n---\n-->\n{body}"
    path.write_text(source)

    registry = build_docs_registry(tmp_path)
    report = docs_health_report(tmp_path)

    assert registry[0]["decision_id"] == "DR-0001"
    assert registry[0]["decision_status"] == "accepted"
    assert report["required_gaps"] == []
    assert report["verdict"] == "pass"


@pytest.mark.parametrize(
    ("original", "replacement", "gap"),
    [
        ("decision_id: DR-0001", "decision_id: DR-0002", "identity"),
        ("decision_id: DR-0001", "decision_id: 1", "metadata"),
        ("decision_status: accepted", "decision_status: planned", "status"),
        ("state: canonical", "state: active", "status"),
        ("# DR-0001: Shared rationale", "# DR-0002: Shared rationale", "title"),
        ("## Decision", "## Decision\n\n### Nested procedure", "sections"),
        ("## Evidence and Revisit", "## Implementation", "sections"),
        (
            "## Alternatives Rejected\n\nAn execution log cannot explain the trade-off.\n\n",
            "",
            "sections",
        ),
        ("An execution log cannot explain the trade-off.", "", "rationale"),
        ("Current behavior stays with the contract.", "```sh\ngit status\n```", "execution"),
        ("Current behavior stays with the contract.", "    arbitrary_code()", "execution"),
        ("Current behavior stays with the contract.", "- [ ] Publish the result.", "execution"),
        ("Current behavior stays with the contract.", "<div>Procedure</div>", "execution"),
        (
            "Current behavior stays with the contract.",
            "The Change owns `env X=1 git status --short`.",
            "execution",
        ),
        ("Current behavior stays with the contract.", "$ git status", "execution"),
        ("Current behavior stays with the contract.", "source ./setup", "execution"),
        ("Current behavior stays with the contract.", "uv run ./tools/check.mjs", "execution"),
    ],
)
def test_shared_decision_contract_refuses_diagnosed_mismatches_without_mutation(
    tmp_path: Path, original: str, replacement: str, gap: str
) -> None:
    """The shared owner rejects the proven gap, rather than relying on an adopter parser."""
    path = tmp_path / "docs/dr-0001-rationale.md"
    path.parent.mkdir()
    source = _decision().replace(original, replacement)
    path.write_text(source)

    report = docs_health_report(tmp_path)

    assert report["verdict"] == "block"
    assert any(
        value.startswith((f"docs_decision_{gap}_", "docs_metadata_invalid:"))
        for value in report["required_gaps"]
    )
    assert path.read_text() == source
