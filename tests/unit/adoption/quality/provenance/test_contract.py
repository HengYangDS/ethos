"""Require typed native source contracts rather than unchecked artifact labels."""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import pytest
import tomli_w

if TYPE_CHECKING:
    from pathlib import Path
from pydantic import ValidationError

from ethos.adapters.gates.python_quality import static_report
from ethos.adapters.repo.gate_policy import observe_quality_subjects
from ethos.repository.policy.quality.obligations import source_integrity_gaps
from ethos.repository.policy.quality.obligations import source_kinds
from ethos.repository.policy.quality.obligations import source_verifier_gaps
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import render_repository_profile
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile


def test_native_source_contract_round_trips_without_a_second_manifest() -> None:
    """One profile relates artifacts to existing native owners and one integrity gate."""
    relation = {
        "kind": "generated",
        "input_refs": [".config/checks/ci-projection/policy.toml"],
        "members": {"generated.py": [".config/checks/ci-projection/policy.toml", "generated.py"]},
        "integrity_gate": "source-integrity",
    }
    declaration = RepositoryProfileDeclaration.model_validate(
        {
            "profile_id": "example",
            "proof": {"gate_registry": "system/gates.toml", "source_contracts": [relation]},
        }
    )
    assert tomllib.loads(render_repository_profile(declaration))["proof"]["source_contracts"] == [
        relation
    ]


@pytest.mark.parametrize("artifact", ["../escape.py", "/absolute.py", "folder\\escape.py"])
def test_source_contract_rejects_nonrepository_members(artifact: str) -> None:
    """A source relationship is bounded to one repository, not an arbitrary producer."""
    with pytest.raises(ValidationError):
        RepositoryProfileDeclaration.model_validate(
            {
                "profile_id": "example",
                "proof": {
                    "gate_registry": "system/gates.toml",
                    "source_contracts": [
                        {
                            "kind": "generated",
                            "input_refs": [".config/checks/ci-projection/policy.toml"],
                            "members": {
                                artifact: [".config/checks/ci-projection/policy.toml", artifact]
                            },
                            "integrity_gate": "source-integrity",
                        }
                    ],
                },
            }
        )


def test_static_selection_preserves_artifact_obligations(tmp_path: Path) -> None:
    """Generated code has byte provenance and behavior obligations, not authored style."""
    repo = init_git_repo(tmp_path / "repository")
    (repo / "authored.py").write_text("VALUE = 42\n")
    content = "import math\nVALUE = 42\n"
    (repo / "generated.py").write_text(content)
    (repo / "template.txt").write_text(content)
    (repo / ".gitattributes").write_text("generated.py ethos-role=generated\n")
    owner = ".config/checks/ci-projection/policy.toml"
    target = repo / owner
    target.parent.mkdir(parents=True)
    target.write_text(
        tomli_w.dumps(
            {
                "schema": "ethos-ci-template-consistency-v1",
                "projection": [{"template": "template.txt", "projection": "generated.py"}],
            }
        )
    )
    write_test_profile(
        repo,
        profile_id="example",
        proof={
            "gate_registry": "system/gates.toml",
            "source_contracts": [
                {
                    "kind": "generated",
                    "input_refs": [owner],
                    "members": {"generated.py": [owner, "generated.py"]},
                    "integrity_gate": "source-integrity",
                }
            ],
        },
    )
    commit_fixture(repo, "declare exact native source relationship")

    tree, subjects = observe_quality_subjects(repo)
    report = static_report(repo)

    assert report["verdict"] == "pass", report
    assert report["quality_evidence"] == {
        "axis": "static-analysis",
        "source_tree": tree,
        "selected_paths": ["authored.py", "generated.py"],
        "authored_paths": ["authored.py"],
        "artifact_paths": ["generated.py"],
        "python_target": {
            "version": "py312",
            "basis": "ruff-target-version",
            "files": [".config/checks/ruff/ruff.toml"],
        },
    }
    assert next(subject for subject in subjects if subject.path == "generated.py").requires_behavior


@pytest.mark.parametrize("contracts", [None, {}, [{"kind": "generated"}]])
def test_source_obligation_boundary_rejects_invalid_native_contracts(contracts: object) -> None:
    """Malformed serialized contracts neither grant style exemptions nor evade evidence."""
    owner = {"source_contracts": contracts}
    assert source_kinds(owner) == {}
    assert source_verifier_gaps(owner, ()) == ("source_contract_invalid",)
    assert source_integrity_gaps({"owner": owner}, (), source_tree="a" * 40) == (
        "source_contract_invalid",
    )


def test_source_member_type_is_rejected_by_native_validation() -> None:
    """Malformed paths remain declared validation failures through every consumer."""
    owner = ".config/checks/ci-projection/policy.toml"
    relation = {
        "kind": "generated",
        "input_refs": [owner],
        "members": {"generated.py": [owner, 1]},
        "integrity_gate": "source-integrity",
    }
    with pytest.raises(ValidationError, match="valid string"):
        RepositoryProfileDeclaration.model_validate(
            {"profile_id": "example", "proof": {"source_contracts": [relation]}}
        )
    policy = {"source_contracts": [relation]}
    assert source_kinds(policy) == {}
    assert source_verifier_gaps(policy, ()) == ("source_contract_invalid",)
    assert source_integrity_gaps({"owner": policy}, (), source_tree="a" * 40) == (
        "source_contract_invalid",
    )
