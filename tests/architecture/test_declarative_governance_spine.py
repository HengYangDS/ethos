from __future__ import annotations

import json
import re
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.assistants.playbooks import playbooks_report
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.repository.evidence.freshness import evidence_freshness_report
from ethos.repository.evidence.topology import evidence_topology_report

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[2]
CORE_SOURCE = ROOT / "src/ethos"
WHEEL_PROJECTIONS = (
    ("system/gates.toml", "gates.toml"),
    ("system/invalid_states.toml", "invalid_states.toml"),
    ("system/coupling.toml", "coupling.toml"),
    ("system/standards.toml", "standards.toml"),
    ("system/policies/evidence-layout.toml", "evidence_layout.toml"),
    (
        "system/policies/generated-artifact-topology.toml",
        "generated_artifact_topology.toml",
    ),
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _tracked_or_nonignored(relative: str) -> list[str]:
    paths = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", relative],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return [path for path in paths if (ROOT / path).exists()]


def test_canonical_decision_code_links_reference_existing_paths() -> None:
    text = _read("docs/decisions/decision-code-links.md")
    prefixes = (".config/", "docs/", "src/", "system/", "tests/", "tools/")
    missing = []
    for line in text.splitlines():
        if not line.startswith("|") or "Historical only" in line:
            continue
        for reference in re.findall(r"`([^`]+)`", line):
            path = reference.partition("::")[0]
            if (path.startswith(prefixes) or path == "pyproject.toml") and not (
                ROOT / path
            ).exists():
                missing.append(path)

    assert missing == []


def test_transition_plan_uses_stdlib_graphlib_without_parallel_graph_owners() -> None:
    source = _read("src/ethos/contracts/plan.py")
    assert "from graphlib import" in source
    assert "TopologicalSorter" in source
    parallel = [
        path.relative_to(ROOT).as_posix()
        for path in CORE_SOURCE.rglob("*.py")
        if path != CORE_SOURCE / "contracts" / "plan.py"
        and "TopologicalSorter" in path.read_text(encoding="utf-8")
    ]
    assert parallel == []
    assert "def _plan_closure(" not in _read("src/ethos/adapters/mutation/proof.py")
    assert "def _closure_plan(" not in _read("src/ethos/adapters/mutation/proof_validation.py")
    assert "def to_dict(" not in source
    assert "def normalized(" not in source
    assert "GraphKernel" not in source
    assert "ActionGraph" not in source
    assert not (CORE_SOURCE / "graph").exists()
    assert not (CORE_SOURCE / "action_graph").exists()


def test_gate_dependencies_are_declared_without_runtime_product_injection() -> None:
    registry = tomllib.loads(_read("system/gates.toml"))
    gates = {gate["id"]: gate for gate in registry["gates"]}
    source = _read("src/ethos/repository/policy/gates.py")

    assert gates["generated-artifacts"]["depends_on"] == ["unit-architecture", "ruff"]
    assert "effective_gate_dependencies" not in source


def test_declared_offline_providers_execute_through_one_runner() -> None:
    registry = load_gate_registry_declaration().registry("runtime")
    runner = LocalGateRunner()

    for gate_id in ("evidence-freshness", "docstrings", "module-layout", "python-types"):
        gate = registry[gate_id]
        assert gate.providers
        assert gate.network_policy == "offline"
        assert gate.writes_files is False

        result = runner.run(
            PlanNode(id=gate.id, kind="check", depends_on=gate.depends_on),
            gate,
            root=ROOT,
        )
        payload = json.loads(result.stdout)

        assert payload["gate"] == gate_id
        assert [entry["provider"] for entry in payload["providers"]] == list(gate.providers)
        assert result.verdict == payload["verdict"]
        assert result.exit_code == (0 if payload["verdict"] == "pass" else 1)


def test_playbooks_provider_publishes_closed_verdict() -> None:
    report = playbooks_report(ROOT)

    assert report["verdict"] == "pass", report["required_gaps"]
    assert "ok" not in report


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
    evidence_layout = declaration.read_text(encoding="utf-8")
    assert "component.verdict" in evidence_layout
    assert "component.ok" not in evidence_layout
    assert 'allowed_root_dirs = ["attestations"]' in evidence_layout
    assert 'historical_root_dirs = ["claims", "chronicle", "parity"]' in evidence_layout
    for token in ("chronicle_record_glob", "flat_chronicle_glob", "required_subroot"):
        assert token not in evidence_layout
    for token in ("historical_claims_root", "chronicle_root", "chronicle_records"):
        assert token not in source + projection
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


def test_evidence_topology_separates_current_attestations_from_historical_bytes(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    (evidence / "attestations").mkdir(parents=True)
    (evidence / "attestations" / "current.json").write_text("{}\n", encoding="utf-8")
    for root, name in (
        ("claims", "legacy.toml"),
        ("chronicle", "legacy.md"),
        ("parity", "generic-shadow.json"),
    ):
        directory = evidence / root
        directory.mkdir()
        (directory / name).write_text("historical\n", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["layout"]["attestation_root"] == "evidence/attestations"
    assert report["layout"]["historical_roots"] == [
        "evidence/claims",
        "evidence/chronicle",
        "evidence/parity",
    ]
    assert report["counts"] == {"attestation_files": 1, "historical_artifacts": 3}


def test_evidence_topology_blocks_invalid_or_missing_root(tmp_path: Path) -> None:
    missing = evidence_topology_report(tmp_path)
    assert missing["verdict"] == "block"
    assert "ok" not in missing

    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "unexpected.txt").write_text("invalid\n", encoding="utf-8")
    invalid = evidence_topology_report(tmp_path)

    assert invalid["verdict"] == "block"
    assert invalid["required_gaps"] == ["evidence_root_file_not_allowed:unexpected.txt"]


def test_evidence_freshness_preserves_unknown_topology(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ethos.repository.evidence.freshness.evidence_topology_report",
        lambda _root: {
            "verdict": "unknown",
            "required_gaps": ["evidence_topology_unavailable"],
            "warnings": [],
        },
    )

    report = evidence_freshness_report(tmp_path, current_head="abc123")

    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["evidence_topology_unavailable"]


def test_terminal_gate_owners_are_singular_and_hosted_logic_stays_in_tools() -> None:
    registry = tomllib.loads(_read("system/gates.toml"))
    gates = {gate["id"]: gate for gate in registry["gates"]}
    product_boundary = gates["product-boundary"]

    assert "no-compat" not in gates
    assert "no-compat" not in registry["proof_sets"]["default"]
    assert "no-compat" not in registry["proof_sets"]["full"]
    assert product_boundary["providers"] == [
        "ethos.repository.policy.boundary.product:product_boundary_report",
        "ethos.repository.policy.boundary.product:contributor_policy_report",
    ]
    assert "evidence-freshness" in gates
    assert "claims" not in gates
    assert "docs-registry" in gates
    assert "docs-topology" not in gates
    assert gates["docs-registry"]["dimensions"] == [
        "front-matter",
        "taxonomy",
        "visible-sections",
        "command-examples",
        "plan-discoverability",
    ]
    assert gates["markdown-links"]["network_policy"] == "offline"
    assert gates["external-links"]["network_policy"] == "required"
    assert gates["external-links"]["dimensions"] == ["external-reachability"]

    tools = tomllib.loads(_read("system/tools.toml"))["tool"]
    concerns = {tool["concern"] for tool in tools}
    assert "compatibility_residue" not in concerns
    assert "governance_kernel" not in concerns
    assert "product_boundary" in concerns
    assert "hosted_provider_observation" in concerns

    for relative in (
        "repository/policy/governance",
        "repository/policy/no_compat",
        "repository/evidence/hosted/core.py",
        "quality/docs/profile.py",
        "repository/registry/standards.py",
    ):
        assert _tracked_or_nonignored(f"src/ethos/{relative}") == []

    local_ci = _read("tools/ci/scripts/run-local-ci.sh")
    for relative in (
        "tools/ci/scripts/run-no-compat.sh",
        "tools/ci/scripts/run-governance-kernel.sh",
    ):
        assert _tracked_or_nonignored(relative) == []
        assert Path(relative).name not in local_ci


def test_portable_docs_registry_has_no_parallel_topology_owner() -> None:
    """Portable semantics and product self-audit replace physical docs topology."""
    for relative in (
        "contracts/docs/topology.py",
        "repository/policy/docs/topology.py",
    ):
        assert not (CORE_SOURCE / relative).exists()

    links = _read("src/ethos/repository/registry/docs/links.py")
    for retired in (
        "link_integrity_report",
        "glossary_report",
        "stable_paths_report",
        "markdown_paths",
    ):
        assert retired not in links

    hosted_tool = _read("tools/ci/hosted_observation.py")
    for token in (
        "def provider_command(",
        "def provider_output_valid(",
        "def provider_facts(",
        "def observation_summary(",
    ):
        assert token in hosted_tool
    assert "ethos.repository.evidence.hosted.core" not in hosted_tool
