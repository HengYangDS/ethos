"""Decision identity is a portable Docs Registry obligation, not a second index."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ethos.surface.cli.root.reference import docs_registry_report
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _document(subject: str, role: str, title: str) -> str:
    return (
        f"---\nsubject: {subject}\nrole: {role}\nstate: canonical\nrelations: {{}}\n"
        f"---\n\n# {title}\n\nStatus: canonical.\n\nPurpose: exercise decision identity.\n"
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

    report = docs_registry_report(tmp_path)

    assert "docs_decision_name_invalid:handbook/rulings/choice.md" in report["required_gaps"]


def test_public_docs_gate_blocks_unnumbered_decision_record(tmp_path: Path) -> None:
    """The CLI cannot prove a repository with an unstable decision identity."""
    root = init_git_repo(tmp_path / "repo")
    decision = root / "docs/rulings/choice.md"
    decision.parent.mkdir(parents=True)
    decision.write_text(_document("sample:decision:choice", "decision", "Choice"))
    commit_fixture(root, "unnumbered decision")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "docs-registry", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    provider = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]

    assert result.returncode != 0
    assert report["verdict"] == "block"
    assert report["summary"]["proof_attestation_issued"] is False
    assert provider["required_gaps"] == ["docs_decision_name_invalid:docs/rulings/choice.md"]
