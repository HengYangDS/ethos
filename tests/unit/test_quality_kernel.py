from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_quality_package_is_focused_and_importable() -> None:
    import ethos_quality.docs_profile
    import ethos_quality.gates
    import ethos_quality.models
    import ethos_quality.profiles
    import ethos_quality.proof_policy

    init_path = ROOT / "packages/ethos-quality/src/ethos_quality/__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    assert ethos_quality.models.__name__ == "ethos_quality.models"
    assert ethos_quality.profiles.__name__ == "ethos_quality.profiles"
    assert ethos_quality.gates.__name__ == "ethos_quality.gates"
    assert ethos_quality.docs_profile.__name__ == "ethos_quality.docs_profile"
    assert ethos_quality.proof_policy.__name__ == "ethos_quality.proof_policy"


def test_quality_profile_covers_repository_asset_classes() -> None:
    from ethos_quality.profiles import product_quality_profile

    profile = product_quality_profile()
    asset_classes = {asset["class"] for asset in profile["asset_classes"]}
    dimensions = {
        dimension for asset in profile["asset_classes"] for dimension in asset["dimensions"]
    }

    assert {
        "python-code",
        "markdown-docs",
        "shell-scripts",
        "toml-config",
        "json-contracts",
        "yaml-config",
        "evidence",
        "release-artifacts",
        "adopter-profile",
    } <= asset_classes
    assert {
        "format",
        "lint",
        "schema",
        "links",
        "anchors",
        "command-examples",
        "determinism",
        "freshness",
        "provenance",
    } <= dimensions


def test_gate_plan_uses_quality_descriptors_not_commands_only() -> None:
    from ethos_quality.gates import product_gate_plan

    plan = product_gate_plan()
    gates = {gate["id"]: gate for gate in plan["gates"]}

    assert gates["markdown-links"]["asset_classes"] == ["markdown-docs"]
    assert gates["toml-config"]["tool_adapter"] == "taplo"
    assert gates["shell-lint"]["tool_adapter"] == "shellcheck"
    assert gates["python-lint"]["tool_adapter"] == "ruff"
    assert gates["schema-contracts"]["evidence_class"] == "contract"
    assert gates["proof-policy"]["trust_bearing"] is True
    assert all("network_policy" in gate for gate in gates.values())


def test_docs_profile_models_faithful_expressive_elegant_docs() -> None:
    from ethos_quality.docs_profile import docs_quality_profile

    profile = docs_quality_profile()
    checks = {check["id"]: check for check in profile["checks"]}

    assert checks["front-matter"]["required"] == ["subject", "role", "state", "relations"]
    assert checks["reader-purpose"]["dimensions"] == ["status", "purpose", "see_also"]
    assert checks["link-integrity"]["tool_adapter"] == "lychee"
    assert checks["command-examples"]["tool_adapter"] == "ethos-command-registry"
    assert profile["style_goals"] == ["faithful", "expressive", "elegant"]


def test_proof_policy_has_trust_bearing_lattice() -> None:
    from ethos_quality.proof_policy import proof_lattice

    lattice = proof_lattice()
    states = {state["state"]: state for state in lattice["states"]}

    assert set(states) == {
        "planned",
        "readiness",
        "executed",
        "proven",
        "blocked",
        "accepted-risk",
        "waived_nonblocking",
    }
    assert states["planned"]["trust_bearing"] is False
    assert states["readiness"]["trust_bearing"] is False
    assert states["executed"]["trust_bearing"] is False
    assert states["proven"]["trust_bearing"] is True
    assert lattice["trust_consumers"] == [
        "claim",
        "land",
        "publish",
        "release",
        "repository-governance",
    ]
