"""Applicable shared proof and native configuration compose through one product owner."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("mode", ["default", "full", "focused"])
def test_applicable_common_document_floor_preserves_native_increment_and_focus(
    tmp_path: Path, mode: str
) -> None:
    """Actual documents require shared owners without importing a product toolchain."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="document-repository",
            proof=ProofPolicy(
                code_correctness_gates=("native",),
                gates=(Gate(id="native", kind="test", command=("native-check",)),),
                code_correctness_map={"behavior": "native", "static-analysis": "native"},
            ),
        ),
    )
    policy = compile_gate_policy(
        profile=profile,
        repository_paths=("README.md", "docs/design.md", "openspec/config.yaml"),
        gate_ids=("native",) if mode == "focused" else (),
        full=mode == "full",
    )
    common = {"docs-registry", "markdown-lint", "markdown-links", "openspec", "schemas"}
    assert set(policy.gate_ids) == ({"native"} if mode == "focused" else {"native", *common})
    assert policy.registry["native"].command == ("native-check",)
    if mode != "focused":
        assert all(not policy.registry[name].command for name in common)
        assert not any("nox" in gate.command for gate in policy.gates)
        assert policy.declaration.proof_sets.default == ("native",)
        assert policy.declaration.proof_sets.full == ("native",)
        assert {gate["id"] for gate in policy.projection["gates"]} == {"native", *common}


def test_required_common_verifier_cannot_be_replaced_by_same_named_native_command(
    tmp_path: Path,
) -> None:
    """Native increments remain local, but cannot impersonate a shared required owner."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="document-repository",
            proof=ProofPolicy(
                code_correctness_gates=("markdown-lint",),
                gates=(Gate(id="markdown-lint", kind="test", command=("true",)),),
                code_correctness_map={
                    "behavior": "markdown-lint",
                    "static-analysis": "markdown-lint",
                },
            ),
        ),
    )
    with pytest.raises(ValueError, match="common_gate_execution_conflict:markdown-lint"):
        compile_gate_policy(profile=profile, repository_paths=("README.md",), full=True)


def test_native_configuration_uses_one_shared_directory_shape() -> None:
    """Historical alternative paths cannot silently select a second policy owner."""
    with pytest.raises(ValueError, match="native_tool_configuration_location_invalid:lychee"):
        native_tool_configuration((".config/checks/lychee/lychee.toml",), "lychee")
    expected = ".config/checks/links/lychee.toml"
    assert native_tool_configuration((expected,), "lychee") == expected


def test_same_executor_preserves_the_complete_applicable_common_contract(tmp_path: Path) -> None:
    """A native redeclaration cannot lower the shared floor's policy or evidence bounds."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="document-repository",
            proof=ProofPolicy(
                code_correctness_gates=("markdown-lint",),
                gates=(
                    Gate(
                        id="markdown-lint",
                        kind="native",
                        providers=("ethos.adapters.gates.tool:markdown_lint_report",),
                        policy="advisory",
                        network_policy="unrestricted",
                        trust_bearing=False,
                        writes_files=True,
                    ),
                ),
                code_correctness_map={
                    "behavior": "markdown-lint",
                    "static-analysis": "markdown-lint",
                },
            ),
        ),
    )
    policy = compile_gate_policy(profile=profile, repository_paths=("README.md",), full=True)
    expected = (
        load_gate_registry_declaration()
        .registry()["markdown-lint"]
        .model_copy(update={"profile": "repository", "tool_adapter": "ethos"})
    )
    assert policy.registry["markdown-lint"] == expected
    assert profile.declaration is not None
    assert profile.declaration.proof.gates[0].policy == "advisory"
