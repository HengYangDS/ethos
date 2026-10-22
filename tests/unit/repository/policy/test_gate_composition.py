"""Applicable shared proof and native configuration compose through one product owner."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

import pytest
import tomli_w
from pydantic import ValidationError

from ethos.contracts.gates import Gate
from ethos.contracts.gates import GateProofSets
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import bind_gate_source_digests
from ethos.repository.policy.gates import resolve_gate_policy as compile_gate_policy
from ethos.repository.policy.gates import source_paths_for_gate
from ethos.repository.policy.quality.gate_composition import select_gate_declaration
from ethos.repository.policy.quality.obligations import INTEGRITY_PROVIDER
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
    common = {
        "config-quality",
        "docs-registry",
        "markdown-lint",
        "markdown-links",
        "openspec",
        "prose",
        "schemas",
        "source-format",
    }
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


@pytest.mark.parametrize(
    ("requested", "refused"),
    [
        (("dependency-vulnerabilities",), "dependency-vulnerabilities"),
        (("native", "ruff"), "ruff"),
        (("generated-artifacts",), "(ruff|unit-architecture)"),
    ],
)
def test_adopter_selection_refuses_a_product_toolchain_command(
    tmp_path: Path, requested: tuple[str, ...], refused: str
) -> None:
    """An adopter imports provider-backed packaged gates only, never a product command."""
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
    with pytest.raises(ValueError, match=f"^proof_gate_not_importable:{refused}$"):
        compile_gate_policy(profile=profile, gate_ids=requested, repository_python="python")
    imported = compile_gate_policy(
        profile=profile, gate_ids=("external-links",), repository_python="python"
    )
    assert imported.registry["external-links"].tool_adapter == "ethos"


def test_product_registry_keeps_its_native_floor_declarations() -> None:
    """The product declares the shared floors natively; composition rewrites only adopters."""
    shipped = load_gate_registry_declaration()
    floor = shipped.registry()["markdown-lint"].model_copy(update={"required_for_paths": ("*.md",)})
    packaged = shipped.model_copy(
        update={"gates": tuple(floor if gate.id == floor.id else gate for gate in shipped.gates)}
    )
    paths = ("README.md",)
    product = select_gate_declaration(
        shipped, (), packaged, repository_paths=paths, full=True, product_source=True
    )
    assert product is shipped
    adopted = select_gate_declaration(shipped, (), packaged, repository_paths=paths, full=True)
    assert adopted.registry()["markdown-lint"].profile == "repository"


def test_native_configuration_uses_one_shared_directory_shape() -> None:
    """Historical alternative paths cannot silently select a second policy owner."""
    with pytest.raises(ValueError, match="native_tool_configuration_location_invalid:lychee"):
        native_tool_configuration((".config/checks/links/lychee.toml",), "lychee")
    expected = ".config/checks/lychee/lychee.toml"
    assert native_tool_configuration((expected,), "lychee") == expected

    assert native_tool_configuration((".config/checks/ruff/ruff.toml",), "ruff") == (
        ".config/checks/ruff/ruff.toml"
    )
    with pytest.raises(ValueError, match="native_tool_configuration_location_invalid:ruff"):
        native_tool_configuration(("ruff.toml",), "ruff")
    with pytest.raises(ValueError, match="native_tool_configuration_ambiguous:ruff"):
        native_tool_configuration(("ruff.toml", ".config/checks/ruff/ruff.toml"), "ruff")


def test_invalid_configuration_is_reported_not_admitted_policy(tmp_path: Path) -> None:
    """An ambiguous carrier is a policy gap; only the carrier the tool reads binds as a source."""
    paths = (
        ".config/checks/markdownlint-cli2/.markdownlint-cli2.yaml",
        ".config/checks/markdownlint-cli2/.markdownlint-cli2.jsonc",
    )
    gate = Gate(
        id="markdown-lint",
        kind="lint",
        profile="repository",
        tool_adapter="ethos",
        providers=("ethos.adapters.gates.tool:markdown_lint_report",),
        tools=("prettier", "prettier-ignore", "markdownlint-cli2"),
    )
    declaration = load_gate_registry_declaration().model_copy(
        update={"gates": (gate,), "proof_sets": GateProofSets(default=(gate.id,), full=(gate.id,))}
    )
    profile = RepositoryProfile(
        root=tmp_path,
        exists=True,
        declaration=RepositoryProfileDeclaration(
            profile_id="configuration-observation",
            proof=ProofPolicy(gate_registry="system/gates.toml"),
        ),
    )
    sources = source_paths_for_gate(gate, repository_paths=paths)
    assert set(paths) & set(sources) == {paths[0]}
    materials = {path: path.encode() for path in sources}
    policy = compile_gate_policy(
        profile=profile,
        gate_registry_source=tomli_w.dumps(
            declaration.model_dump(mode="json", exclude_none=True)
        ).encode(),
        repository_paths=paths,
        source_materials=materials,
        repository_python="python",
        gate_ids=(gate.id,),
        selected_obligations=True,
    )
    assert policy.gaps == (
        "gate_policy_source_invalid:markdown-lint:native_tool_configuration_ambiguous:markdownlint-cli2",
    )
    assert dict(dict(policy.sources)[gate.id]) == {
        path: hashlib.sha256(value).hexdigest() for path, value in materials.items()
    }


@pytest.mark.parametrize(
    ("tools", "carrier"),
    [
        ((), ".config/checks/lychee/lychee.toml"),
        (("lychee",), ".config/checks/lychee/lychee.toml"),
        (("vale",), ".config/checks/vale/styles/plain/concise.yml"),
    ],
)
def test_declared_tools_bind_their_native_policy_carriers(
    tools: tuple[str, ...], carrier: str
) -> None:
    """Only the registry's declared tools bind their policy carriers, nested trees included."""
    gate = Gate(
        id="markdown-links",
        kind="lint",
        profile="repository",
        providers=("ethos.adapters.gates.tool:markdown_links_report",),
        tools=tools,
    )
    sources = source_paths_for_gate(gate, repository_paths=(carrier, "README.md"))
    assert (carrier in sources) is bool(tools)
    assert "README.md" not in sources
    assert ("tools" in gate.to_dict()) is bool(tools)
    bound, gaps = bind_gate_source_digests(
        (gate,), {path: b"" for path in sources if path != carrier}, repository_paths=(carrier,)
    )
    assert (f"gate_policy_source_missing:markdown-links:{carrier}" in gaps) is bool(tools)
    assert carrier not in dict(dict(bound)[gate.id])


@pytest.mark.parametrize("tools", [("lychee", "lychee"), ("undeclared-tool",)])
def test_gate_tools_name_each_paradigm_tool_once(tools: tuple[str, ...]) -> None:
    """A gate cannot bind a repeated native owner or one the paradigm does not declare."""
    with pytest.raises(ValidationError, match="gate tools invalid"):
        Gate(
            id="markdown-links",
            kind="lint",
            providers=("ethos.adapters.gates.tool:markdown_links_report",),
            tools=tools,
        )


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


def test_generated_common_policy_binds_product_compiler_and_native_supply_inputs():
    """A common-model or compiler-input change invalidates the same gate execution identity."""
    reference = ".config/checks/ci-projection/policy.toml"
    declaration = {
        "schema": "ethos-ci-template-consistency-v1",
        "compiler": {
            "source": ".config/ci/pipeline.cue",
            "common": ".config/ci/verification.cue",
            "inputs": {"ci": "parameters.toml"},
        },
        "projection": [
            {"kind": "cue", "provider": "github", "projection": ".github/workflows/ci.yml"}
        ],
    }
    contract = SourceContract(
        kind="generated",
        input_refs=(reference,),
        members={".github/workflows/ci.yml": (reference, ".github/workflows/ci.yml")},
        integrity_gate="source-integrity",
    )
    gate = Gate(
        id="source-integrity",
        kind="policy",
        profile="repository",
        tool_adapter="ethos",
        providers=(INTEGRITY_PROVIDER,),
    )
    materials = {reference: tomli_w.dumps(declaration).encode()}
    paths = source_paths_for_gate(gate, source_contracts=(contract,), source_materials=materials)
    required = {
        "@ethos/adapters/projections/cue.py",
        "@ethos/repository/policy/projections.py",
        "@ethos/resources/.config/ci/verification.cue",
        "@ethos/resources/.config/mise/config.toml",
        "@ethos/resources/.config/mise/mise.lock",
    }
    assert required <= set(paths)
    assert ".config/ci/verification.cue" not in paths
    materials.update({path: b"original product input" for path in paths if path != reference})
    original, gaps = bind_gate_source_digests((gate,), materials, source_contracts=(contract,))
    assert not gaps
    for path in required:
        updated, gaps = bind_gate_source_digests(
            (gate,),
            {**materials, path: b"changed product input"},
            source_contracts=(contract,),
        )
        assert not gaps
        assert updated != original
