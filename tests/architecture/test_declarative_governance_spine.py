from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.assistants.playbooks import playbooks_report
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.plan import PlanNode
from ethos.repository.evidence.freshness import evidence_freshness_report
from ethos.repository.evidence.topology import evidence_topology_report
from ethos.repository.policy.gates import gate_execution_identity

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[2]
CORE_SOURCE = ROOT / "src/ethos"
WHEEL_PROJECTIONS = (
    ("system/gates.toml", "gates.toml"),
    ("system/policies/evidence-layout.toml", "evidence_layout.toml"),
    (
        "system/policies/generated-artifact-topology.toml",
        "generated_artifact_topology.toml",
    ),
)
_PROCESS_CALLS = frozenset({"run", "Popen", "call", "check_call", "check_output"})


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_python_process_execution_uses_argv_without_a_shell() -> None:
    findings = []
    for root in (ROOT / "src", ROOT / "tests", ROOT / "tools", ROOT / ".agents" / "skills"):
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if not isinstance(node.func.value, ast.Name):
                    continue
                if node.func.value.id != "subprocess" or node.func.attr not in _PROCESS_CALLS:
                    continue
                first = node.args[0] if node.args else None
                shell = next((item.value for item in node.keywords if item.arg == "shell"), None)
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:string-command")
                if isinstance(shell, ast.Constant) and shell.value is True:
                    findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:shell-true")

    assert findings == []


def test_git_executable_resolution_and_process_spawn_have_one_owner() -> None:
    owner = CORE_SOURCE / "adapters" / "repo" / "git.py"
    findings = []
    for path in CORE_SOURCE.rglob("*.py"):
        if path == owner:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = ast.unparse(node.func)
            if function in {"shutil.which", "which"} and any(
                isinstance(argument, ast.Constant) and argument.value == "git"
                for argument in node.args
            ):
                findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:git-resolver")
            if function != "subprocess.run":
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            if "git" in literals:
                findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:git-spawn")

    assert findings == []


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


def test_git_ref_mutation_has_one_declared_execution_owner() -> None:
    references: set[str] = set()
    executions: list[str] = []
    intent_writers: list[str] = []
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and "update-ref" in node.value
            ):
                references.add(relative)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "run_git"
                and any(
                    isinstance(argument, ast.Constant) and argument.value == "update-ref"
                    for argument in node.args
                )
            ):
                executions.append(relative)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "write_ref_intent"
            ):
                intent_writers.append(relative)
    assert references == {
        "adapters/repo/git_effect_attestation.py",
        "adapters/repo/git_effects.py",
        "contracts/plan.py",
    }
    assert executions == ["adapters/repo/git_effects.py"]
    assert intent_writers == ["adapters/repo/git_effects.py"]


def test_effect_attestation_has_one_semantic_owner() -> None:
    parallel_owner = CORE_SOURCE / "adapters/repo/native_effect_attestation.py"
    assert not parallel_owner.exists()

    imports = {
        path.relative_to(CORE_SOURCE).as_posix()
        for path in CORE_SOURCE.rglob("*.py")
        if "native_effect_attestation" in path.read_text(encoding="utf-8")
    }
    assert imports == set()


def test_git_worktree_mutation_has_one_declared_execution_owner() -> None:
    owner = "adapters/repo/worktree_effects.py"
    executions: set[str] = set()
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func.id if isinstance(node.func, ast.Name) else ""
            if function not in {"run", "run_git"}:
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            if "worktree" in literals and literals & {"add", "remove"}:
                executions.add(relative)

    source = _read(f"src/ethos/{owner}")
    assert executions == set()
    assert '("worktree", "add"' in source
    assert '("worktree", "remove"' in source


def test_git_worktree_index_mutation_has_one_declared_execution_owner() -> None:
    executions: set[str] = set()
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func.id if isinstance(node.func, ast.Name) else ""
            if function not in {"run", "run_git", "runner"}:
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            if "read-tree" in literals:
                executions.add(relative)

    assert executions == {"adapters/repo/worktree_effects.py"}


def test_git_worktree_cleanup_has_no_parallel_reset_or_clean_owner() -> None:
    executions: set[tuple[str, str]] = set()
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func.id if isinstance(node.func, ast.Name) else ""
            if function not in {"run", "run_git", "runner"}:
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            for command in literals & {"reset", "clean"}:
                executions.add((relative, command))

    assert executions == set()


def test_git_switch_mutation_has_one_declared_execution_owner() -> None:
    executions: set[str] = set()
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func.id if isinstance(node.func, ast.Name) else ""
            if function not in {"run", "run_git", "runner"}:
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            if "switch" in literals:
                executions.add(relative)

    assert executions == {"adapters/repo/worktree_effects.py"}


def test_git_rebase_mutation_has_one_declared_execution_owner() -> None:
    executions: set[str] = set()
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func.id if isinstance(node.func, ast.Name) else ""
            if function not in {"run", "run_git", "runner"}:
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            if "rebase" in literals:
                executions.add(relative)

    assert executions == {"adapters/mutation/lane_lifecycle/work_lane_refresh.py"}


def test_remaining_git_mutation_commands_have_one_declared_owner_each() -> None:
    owners = {
        "checkout": {"adapters/mutation/lane_start_carrier.py"},
        "index-add": {"adapters/repo/git_effects.py"},
        "commit-tree": {"adapters/mutation/lane_start_carrier.py"},
        "config-write": {"adapters/repo/config_effects.py"},
        "init": {"adapters/mutation/lane_lifecycle/handoff/destination_objects.py"},
        "bundle-create": {"adapters/mutation/lane_lifecycle/handoff/package.py"},
        "bundle-unbundle": {"adapters/mutation/lane_lifecycle/handoff/destination_objects.py"},
    }
    observed = {effect: set() for effect in owners}
    for path in CORE_SOURCE.rglob("*.py"):
        relative = path.relative_to(CORE_SOURCE).as_posix()
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = (
                node.func.id
                if isinstance(node.func, ast.Name)
                else node.func.attr
                if isinstance(node.func, ast.Attribute)
                else ""
            )
            if function not in {"run", "run_git", "runner"}:
                continue
            literals = {
                descendant.value
                for argument in node.args
                for descendant in ast.walk(argument)
                if isinstance(descendant, ast.Constant) and isinstance(descendant.value, str)
            }
            effects = {
                "checkout": "checkout" in literals,
                "index-add": "add" in literals and "worktree" not in literals,
                "commit-tree": "commit-tree" in literals,
                "config-write": "config" in literals and "--get" not in literals,
                "init": "init" in literals,
                "bundle-create": {"bundle", "create"} <= literals,
                "bundle-unbundle": {"bundle", "unbundle"} <= literals,
            }
            for effect, present in effects.items():
                if present:
                    observed[effect].add(relative)

    assert observed == owners


def test_gate_dependencies_are_declared_without_runtime_product_injection() -> None:
    registry = tomllib.loads(_read("system/gates.toml"))
    gates = {gate["id"]: gate for gate in registry["gates"]}

    assert gates["generated-artifacts"]["depends_on"] == ["unit-architecture", "ruff"]


def test_declared_offline_providers_execute_through_one_runner() -> None:
    registry = load_gate_registry_declaration().registry("runtime")
    runner = LocalGateRunner()

    for gate_id in ("evidence-freshness", "docstrings", "module-layout", "python-types"):
        gate = registry[gate_id]
        assert gate.providers
        assert gate.network_policy == "offline"
        assert gate.writes_files is False

        result = runner.run(
            PlanNode(
                id=gate.id,
                kind="check",
                command=gate_execution_identity(gate),
                depends_on=gate.depends_on,
            ),
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


def test_wheel_resources_are_native_projections_with_one_runtime_supply_hook() -> None:
    package_config = tomllib.loads(_read("pyproject.toml"))
    build = package_config["tool"]["hatch"]["build"]
    wheel = build["targets"]["wheel"]["force-include"]
    sdist = build["targets"]["sdist"]["include"]

    assert build["targets"]["wheel"]["hooks"]["custom"] == {
        "path": "tools/ci/openspec_runtime_hook.py"
    }
    assert "/src" in sdist
    assert "/system" in sdist
    assert "/package-lock.json" in sdist
    assert "/tools/ci/openspec_runtime_hook.py" in sdist
    assert "force-include" not in build["targets"]["sdist"]
    for canonical, resource in WHEEL_PROJECTIONS:
        assert (ROOT / canonical).is_file()
        assert not (CORE_SOURCE / "data" / resource).exists()
        assert wheel[canonical] == f"ethos/data/{resource}"
    assert wheel["system/schemas/kernel"] == "ethos/data/schemas/kernel"
    assert wheel["package-lock.json"] == "ethos/data/supply-chain/package-lock.json"
    hook = _read("tools/ci/openspec_runtime_hook.py")
    assert '"--omit=dev"' in hook
    assert '"--offline"' in hook
    assert '"--workspaces=false"' in hook
    assert 'build_data["force_include"]' in hook


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
    cel = _read("src/ethos/contracts/policy/cel.py")
    assert "evaluate_cel_predicate" in cel
    assert "cel.NewEnv" in cel
    declaration = ROOT / "system/policies/evidence-layout.toml"
    source = _read("src/ethos/contracts/evidence/layout.py")

    assert declaration.exists()
    assert "EvidenceLayoutDeclaration" in source
    assert "freshness_expression" in source
    assert "system/policies/evidence-layout.toml" in source
    assert "data/evidence_layout.toml" in source
    freshness = _read("src/ethos/repository/evidence/freshness.py")
    assert "freshness_ok" in freshness
    evidence_layout = declaration.read_text(encoding="utf-8")
    assert "component.verdict" in evidence_layout
    assert 'allowed_root_dirs = ["attestations"]' in evidence_layout
    assert 'historical_root_dirs = ["claims", "chronicle", "parity"]' in evidence_layout
    declaration = ROOT / "system/gates.toml"
    contract = _read("src/ethos/contracts/gates.py")

    assert declaration.exists()
    assert "GateRegistryDeclaration" in contract
    assert "system/gates.toml" in contract
    assert "data/gates.toml" in contract
    assert "providers =" in declaration.read_text(encoding="utf-8")


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

    assert product_boundary["providers"] == [
        "ethos.repository.policy.boundary.product:product_boundary_report",
        "ethos.repository.policy.boundary.product:contributor_policy_report",
    ]
    assert "evidence-freshness" in gates
    assert "docs-registry" in gates
    assert gates["docs-registry"]["dimensions"] == [
        "front-matter",
        "taxonomy",
        "visible-sections",
        "command-examples",
        "plan-discoverability",
        "decision-records",
    ]
    assert gates["markdown-links"]["network_policy"] == "offline"
    assert gates["external-links"]["network_policy"] == "required"
    assert gates["external-links"]["dimensions"] == ["external-reachability"]

    tools = tomllib.loads(_read("system/tools.toml"))["tool"]
    concerns = {tool["concern"] for tool in tools}
    assert "product_boundary" in concerns
    assert "hosted_provider_observation" in concerns


def test_portable_docs_registry_and_hosted_observation_have_current_owners() -> None:
    """Portable documentation and hosted observation expose their current owners."""
    links = _read("src/ethos/repository/registry/docs/links.py")
    assert "def markdown_links(" in links

    hosted_tool = _read("tools/ci/hosted_observation.py")
    for token in (
        "def provider_command(",
        "def provider_output_valid(",
        "def provider_facts(",
        "def observation_summary(",
    ):
        assert token in hosted_tool
