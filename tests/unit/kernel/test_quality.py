from __future__ import annotations

import ast
from pathlib import Path

import ethos_core.quality.docs.profile
import ethos_core.quality.gates
import ethos_core.quality.models
import ethos_core.quality.profiles
import ethos_core.quality.proof.policy
from ethos_core.quality.docs.profile import docs_quality_profile
from ethos_core.quality.gates import product_gate_plan
from ethos_core.quality.profiles import product_quality_profile
from ethos_core.quality.proof.policy import proof_lattice

ROOT = Path(__file__).resolve().parents[3]


def test_quality_package_is_focused_and_importable() -> None:
    init_path = ROOT / "packages/ethos-core/src/ethos_core/quality/__init__.py"
    tree = ast.parse(init_path.read_text(encoding="utf-8"))

    assert not any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree))
    assert ethos_core.quality.models.__name__ == "ethos_core.quality.models"
    assert ethos_core.quality.profiles.__name__ == "ethos_core.quality.profiles"
    assert ethos_core.quality.gates.__name__ == "ethos_core.quality.gates"
    assert ethos_core.quality.docs.profile.__name__ == "ethos_core.quality.docs.profile"
    assert ethos_core.quality.proof.policy.__name__ == "ethos_core.quality.proof.policy"
    assert not (ROOT / "packages/ethos-core/src/ethos_core/quality/proof_policy.py").exists()
    assert not (ROOT / "packages/ethos-core/src/ethos_core/quality/docs_profile.py").exists()


def test_quality_profile_covers_repository_asset_classes() -> None:
    profile = product_quality_profile(ROOT)
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
    plan = product_gate_plan()
    gates = {gate["id"]: gate for gate in plan["gates"]}

    assert gates["markdown-links"]["asset_classes"] == ["markdown-docs"]
    assert gates["toml-config"]["tool_adapter"] == "taplo"
    assert gates["toml-config"]["command"] == ["tools/ci/scripts/run-config-lint.sh"]
    assert gates["yaml-config"]["command"] == ["tools/ci/scripts/run-config-lint.sh"]
    assert gates["shell-lint"]["tool_adapter"] == "shellcheck"
    assert gates["shell-lint"]["command"] == ["tools/ci/scripts/run-shell-lint.sh"]
    assert gates["python-lint"]["tool_adapter"] == "ruff"
    assert gates["module-layout"]["command"] == ["tools/ci/scripts/run-module-layout.sh"]
    assert gates["module-layout"]["tool_adapter"] == "ethos-module-layout"
    assert gates["schema-contracts"]["evidence_class"] == "contract"
    assert gates["proof-policy"]["trust_bearing"] is True
    assert all("network_policy" in gate for gate in gates.values())


def test_docs_profile_models_faithful_expressive_elegant_docs() -> None:
    profile = docs_quality_profile()
    checks = {check["id"]: check for check in profile["checks"]}

    assert checks["front-matter"]["required"] == ["subject", "role", "state", "relations"]
    assert checks["reader-purpose"]["dimensions"] == ["status", "purpose", "see_also"]
    assert checks["link-integrity"]["tool_adapter"] == "lychee"
    assert checks["command-examples"]["tool_adapter"] == "ethos-command-registry"
    assert profile["style_goals"] == ["faithful", "expressive", "elegant"]


def test_proof_policy_has_trust_bearing_lattice() -> None:
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
