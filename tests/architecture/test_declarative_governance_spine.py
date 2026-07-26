from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE_SOURCE = ROOT / "src/ethos"
WHEEL_PROJECTIONS = (
    ("system/gates.toml", "gates.toml"),
    ("system/invalid_states.toml", "invalid_states.toml"),
    ("system/lifecycle.toml", "lifecycle.toml"),
    ("system/coupling.toml", "coupling.toml"),
    ("system/standards.toml", "standards.toml"),
    ("system/policies/evidence-layout.toml", "evidence_layout.toml"),
    (
        "system/policies/generated-artifact-topology.toml",
        "generated_artifact_topology.toml",
    ),
)
WHEEL_SCHEMA_PROJECTIONS = (
    (
        "system/schemas/contracts/lifecycle.schema.json",
        "data/system/schemas/contracts/lifecycle.schema.json",
    ),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_plan_ir_uses_stdlib_graphlib_without_parallel_graph_owners() -> None:
    source = _read("src/ethos/contracts/plan.py")
    assert "from graphlib import" in source
    assert "TopologicalSorter" in source
    assert "GraphKernel" not in source
    assert "ActionGraph" not in source
    assert not (CORE_SOURCE / "graph").exists()
    assert not (CORE_SOURCE / "action_graph").exists()


def test_wheel_resources_are_native_projections_without_a_build_hook() -> None:
    package_config = tomllib.loads(_read("pyproject.toml"))
    build = package_config["tool"]["hatch"]["build"]
    wheel = build["targets"]["wheel"]["force-include"]
    sdist = build["targets"]["sdist"]["include"]

    assert "hooks" not in build
    assert "/src" in sdist
    assert "/system" in sdist
    for canonical, resource in WHEEL_PROJECTIONS:
        assert (ROOT / canonical).is_file()
        assert not (CORE_SOURCE / "data" / resource).exists()
        assert wheel[canonical] == f"ethos/data/{resource}"
    for canonical, resource in WHEEL_SCHEMA_PROJECTIONS:
        assert (ROOT / canonical).is_file()
        assert not (CORE_SOURCE / resource).exists()
        assert wheel[canonical] == f"ethos/{resource}"


def test_declaration_backed_policies_are_first_class() -> None:
    declaration = ROOT / "system/policies/generated-artifact-topology.toml"
    source = _read("src/ethos/contracts/artifacts/topology.py")

    assert declaration.exists()
    for token in (
        "GeneratedArtifactTopologyDeclaration",
        "TopologyCelRule",
        "system/policies/generated-artifact-topology.toml",
        "data/generated_artifact_topology.toml",
    ):
        assert token in source
    for token in (
        "_ALLOWED_PREFIXES",
        "_DENIED_ROOT_CACHE_PREFIXES",
        "build/runtime/tool-cache/",
        "_legacy_generated_policy",
        "_generated_denial_policy",
    ):
        assert token not in source
    cel = _read("src/ethos/contracts/policy/cel.py")
    assert "evaluate_cel_predicate" in cel
    assert "cel.NewEnv" in cel
    assert "celpy" not in cel
    declaration = ROOT / "system/policies/evidence-layout.toml"
    source = _read("src/ethos/contracts/evidence/layout.py")
    projection = _read("src/ethos/repository/evidence/topology.py")

    assert declaration.exists()
    assert "EvidenceLayoutDeclaration" in source
    assert "freshness_expression" in source
    assert "system/policies/evidence-layout.toml" in source
    assert "data/evidence_layout.toml" in source
    assert "_ALLOWED_ROOT_DIRS" not in projection
    assert "_CURATED_PROFILE_ALLOWED_ROOT_FILES" not in projection
    freshness = _read("src/ethos/repository/evidence/freshness.py")
    assert "freshness_ok" in freshness
    assert "and bool(" not in freshness
    assert 'allowed_root_dirs = ["claims", "chronicle", "parity"]' in declaration.read_text(
        encoding="utf-8"
    )
    declaration = ROOT / "system/gates.toml"
    contract = _read("src/ethos/contracts/gates.py")
    projection = _read("src/ethos/repository/policy/gates.py")
    quality = _read("src/ethos/quality/gates.py")

    assert declaration.exists()
    assert "GateRegistryDeclaration" in contract
    assert "system/gates.toml" in contract
    assert "data/gates.toml" in contract
    assert '"repository-audit": Gate(' not in projection
    assert "PRODUCT_DEFAULT_GATE_IDS = (" not in projection
    assert "QualityGateDescriptor(" not in quality
    assert "providers =" in declaration.read_text(encoding="utf-8")
    assert not (ROOT / "system/commands.toml").exists()
    assert not (CORE_SOURCE / "contracts/commands.py").exists()
    assert not any((CORE_SOURCE / "surface/cli/quality").rglob("*.py"))
    assert not (CORE_SOURCE / "surface/cli/_gate_runner.py").exists()
