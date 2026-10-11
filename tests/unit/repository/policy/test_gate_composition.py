"""Applicable shared proof and native configuration compose through one product owner."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.gates import Gate
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.quality.tool_configuration import native_tool_configuration
from ethos.repository.profile import ProofPolicy
from ethos.repository.profile import RepositoryProfile
from ethos.repository.profile import RepositoryProfileDeclaration
from ethos.repository.profile import SourceContract

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


@pytest.mark.parametrize("mode", ["default", "full", "focused"])
def test_same_executor_preserves_the_complete_applicable_common_contract(
    tmp_path: Path, mode: str
) -> None:
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
    policy = compile_gate_policy(
        profile=profile,
        repository_paths=("README.md",),
        gate_ids=("markdown-lint",) if mode == "focused" else (),
        full=mode == "full",
    )
    expected = (
        load_gate_registry_declaration()
        .registry()["markdown-lint"]
        .model_copy(update={"profile": "repository", "tool_adapter": "ethos"})
    )
    assert policy.registry["markdown-lint"] == expected
    assert profile.declaration is not None
    assert profile.declaration.proof.gates[0].policy == "advisory"


@pytest.mark.parametrize("requested", [("native",), ("schemas",), ("native", "schemas")])
@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("selected_obligations", [False, True])
def test_gate_composition_retains_native_owner_and_exact_provider_sources(
    tmp_path: Path, requested: tuple[str, ...], *, full: bool, selected_obligations: bool
) -> None:
    """One selection preserves the target floor and binds only requested product providers."""
    native = Gate(
        id="native",
        kind="test",
        command=("tools/check.py",),
        verification_providers=("ethos.adapters.gates.python_quality:behavior_report",),
    )
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="target",
            proof=ProofPolicy(
                code_correctness_gates=("native",),
                code_correctness_map={"behavior": "native", "static-analysis": "native"},
                gates=(native,),
            ),
        ),
    )
    materials = {
        "tools/check.py": b"print('target check')\n",
        "@ethos/adapters/gates/python_quality.py": b"native verification\n",
        "@ethos/repository/policy/schema.py": b"installed schema provider\n",
    }
    baseline = compile_gate_policy(
        profile=profile, source_materials=materials, repository_python="python", full=True
    )
    selected = compile_gate_policy(
        profile=profile,
        source_materials=materials,
        repository_python="python",
        gate_ids=requested,
        full=full,
        selected_obligations=selected_obligations,
    )
    assert selected.profile is profile
    assert selected.declaration == baseline.declaration
    assert (selected.projection.get("obligation_scope") == "selected") is (
        selected_obligations and not full
    )
    document_diagnostic = selected_obligations and not full and requested == ("schemas",)
    if document_diagnostic:
        assert "code_correctness_map" not in selected.projection["owner"]
        assert selected.gaps == ()
        assert selected.digest != baseline.digest
    else:
        assert selected.projection["owner"] == baseline.projection["owner"]
    assert set(selected.gate_ids) == ({"native", *requested} if full else set(requested))
    assert set(selected.registry) == {"native", *requested}
    sources = dict(selected.sources)
    for name in requested:
        expected = (
            ("tools/check.py", "@ethos/adapters/gates/python_quality.py")
            if name == "native"
            else ("@ethos/repository/policy/schema.py",)
        )
        assert dict(sources[name]) == {
            path: hashlib.sha256(materials[path]).hexdigest() for path in expected
        }
    if "schemas" in requested:
        assert selected.registry["schemas"].profile == "repository"
        assert selected.registry["schemas"].tool_adapter == "ethos"
    if not full and requested == ("schemas",) and not selected_obligations:
        assert "quality_obligation_unproven:behavior" in selected.gaps
    elif not document_diagnostic:
        assert selected.gaps == baseline.gaps


@pytest.mark.parametrize("requested", [("docs-registry",), ("native-docs",), ("native",)])
def test_focused_obligations_preserve_source_integrity_for_selected_code(
    tmp_path: Path, requested: tuple[str, ...]
) -> None:
    """Document diagnosis excludes unrelated artifacts; a selected code check retains them."""
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="target",
            proof=ProofPolicy(
                code_correctness_gates=("native", "native-docs"),
                gates=(
                    Gate(id="native", kind="test", command=("tools/check.py",)),
                    Gate(
                        id="native-docs",
                        kind="docs",
                        providers=("ethos.surface.cli.root.reference:docs_registry_report",),
                    ),
                ),
                code_correctness_map={"behavior": "native", "static-analysis": "native"},
                source_contracts=(
                    SourceContract(
                        kind="upstream",
                        input_refs=("package-lock.json#packages/node_modules/example",),
                        members={
                            "tools/upstream.js": (
                                "package-lock.json#packages/node_modules/example",
                                "package/index.js",
                            )
                        },
                        integrity_gate="native",
                    ),
                ),
            ),
        ),
    )
    policy = compile_gate_policy(
        profile=profile,
        gate_ids=requested,
        selected_obligations=True,
        repository_paths=(
            "README.md",
            "tools/check.py",
            "tools/upstream.js",
            "src/ethos/surface/cli/root/reference.py",
        ),
        source_materials={
            "tools/check.py": b"print('native')\n",
            "@ethos/surface/cli/root/reference.py": b"document provider\n",
            "src/ethos/surface/cli/root/reference.py": b"document provider\n",
        },
        repository_python="python",
    )
    owner = policy.projection["owner"]
    assert isinstance(owner, dict)
    if requested != ("native",):
        assert policy.gaps == ()
        assert "source_contracts" not in owner
    else:
        assert "source_integrity_gate_unbound:native" in policy.gaps
        assert owner["source_contracts"]
