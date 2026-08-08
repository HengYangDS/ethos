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
CORE = ROOT / "src/ethos"
PROCESS_CALLS = {"run", "Popen", "call", "check_call", "check_output"}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _sources(root: Path = CORE):
    for path in root.rglob("*.py"):
        yield path, path.relative_to(CORE).as_posix(), ast.parse(path.read_text(encoding="utf-8"))


def _call(node: ast.Call) -> str:
    return node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")


def _literals(node: ast.Call) -> set[str]:
    return {
        item.value
        for argument in node.args
        for item in ast.walk(argument)
        if isinstance(item, ast.Constant) and isinstance(item.value, str)
    }


def test_python_process_execution_uses_argv_without_a_shell() -> None:
    findings = []
    for root in (ROOT / "src", ROOT / "tests", ROOT / "tools", ROOT / ".agents/skills"):
        for path in root.rglob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if not isinstance(node.func.value, ast.Name) or node.func.value.id != "subprocess":
                    continue
                if node.func.attr not in PROCESS_CALLS:
                    continue
                first = node.args[0] if node.args else None
                shell = next((item.value for item in node.keywords if item.arg == "shell"), None)
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:string-command")
                if isinstance(shell, ast.Constant) and shell.value is True:
                    findings.append(f"{path.relative_to(ROOT)}:{node.lineno}:shell-true")
    assert findings == []


def test_git_executable_resolution_and_process_spawn_have_one_owner() -> None:
    owner, findings = CORE / "adapters/repo/git.py", []
    for path, relative, tree in _sources():
        if path == owner:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = ast.unparse(node.func)
            if function in {"shutil.which", "which"} and "git" in _literals(node):
                findings.append(f"{relative}:{node.lineno}:git-resolver")
            if function == "subprocess.run" and "git" in _literals(node):
                findings.append(f"{relative}:{node.lineno}:git-spawn")
    assert findings == []


def test_transition_plan_uses_stdlib_graphlib_without_parallel_graph_owners() -> None:
    source = _read("src/ethos/contracts/plan.py")
    assert "from graphlib import" in source
    assert "TopologicalSorter" in source
    assert [
        relative
        for path, relative, _ in _sources()
        if path != CORE / "contracts/plan.py" and "TopologicalSorter" in path.read_text()
    ] == []


def test_reference_and_entrypoint_scanners_share_one_carrier_declaration_owner() -> None:
    owner = _read("src/ethos/repository/policy/references/carriers.py")
    observation = _read("src/ethos/repository/policy/references/observation.py")
    entrypoints = _read("src/ethos/repository/policy/artifact_entrypoints.py")

    assert "REFERENCE_CARRIERS" in owner
    assert "reference_carrier" in observation
    assert "declaration_files" in _read("src/ethos/repository/policy/references/declarations.py")
    assert "entrypoint_files" in entrypoints
    assert "REFERENCE_FILE_SUFFIXES" not in observation
    assert "_ENTRYPOINT_EXPLICIT_FILES" not in entrypoints
    assert "_ENTRYPOINT_GLOB_PATTERNS" not in entrypoints


def test_git_ref_mutation_has_one_declared_execution_owner() -> None:
    references, executions, intents = set(), [], []
    for _path, relative, tree in _sources():
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Constant)
                and isinstance(node.value, str)
                and "update-ref" in node.value
            ):
                references.add(relative)
            if (
                isinstance(node, ast.Call)
                and _call(node) == "run_git"
                and "update-ref" in _literals(node)
            ):
                executions.append(relative)
            if isinstance(node, ast.Call) and _call(node) == "write_ref_intent":
                intents.append(relative)
    assert references == {
        "adapters/repo/git_effect_attestation.py",
        "adapters/repo/git_effects.py",
        "contracts/plan.py",
    }
    assert executions == ["adapters/repo/git_effects.py"]
    assert intents == ["adapters/repo/git_effects.py"]


def test_effect_attestation_has_one_semantic_owner() -> None:
    parallel_owner = CORE / "adapters/repo/native_effect_attestation.py"
    assert not parallel_owner.exists()
    assert {
        relative
        for path, relative, _ in _sources()
        if "native_effect_attestation" in path.read_text()
    } == set()


def test_git_mutation_commands_have_one_declared_owner_each() -> None:
    predicates = {
        "read-tree": lambda x: "read-tree" in x,
        "reset": lambda x: "reset" in x,
        "clean": lambda x: "clean" in x,
        "switch": lambda x: "switch" in x,
        "rebase": lambda x: "rebase" in x,
        "checkout": lambda x: "checkout" in x,
        "index-add": lambda x: "add" in x and "worktree" not in x,
        "commit-tree": lambda x: "commit-tree" in x,
        "config-write": lambda x: "config" in x and "--get" not in x,
        "init": lambda x: "init" in x,
        "bundle-create": lambda x: {"bundle", "create"} <= x,
        "bundle-unbundle": lambda x: {"bundle", "unbundle"} <= x,
    }
    observed = {effect: set() for effect in predicates}
    for _path, relative, tree in _sources():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call(node) not in {"run", "run_git", "runner"}:
                continue
            literals = _literals(node)
            for effect, matches in predicates.items():
                if matches(literals):
                    observed[effect].add(relative)
    assert observed == {
        "read-tree": {"adapters/repo/worktree_effects.py"},
        "reset": set(),
        "clean": set(),
        "switch": {"adapters/repo/worktree_effects.py"},
        "rebase": {"adapters/mutation/lane_lifecycle/work_lane_refresh.py"},
        "checkout": {"adapters/mutation/lane_start_carrier.py"},
        "index-add": {"adapters/repo/git_effects.py"},
        "commit-tree": {"adapters/mutation/lane_start_carrier.py"},
        "config-write": {"adapters/repo/config_effects.py"},
        "init": {"adapters/mutation/lane_lifecycle/handoff/destination_objects.py"},
        "bundle-create": {"adapters/mutation/lane_lifecycle/handoff/package.py"},
        "bundle-unbundle": {"adapters/mutation/lane_lifecycle/handoff/destination_objects.py"},
    }


def test_git_worktree_add_and_remove_share_the_declared_effect_owner() -> None:
    source = _read("src/ethos/adapters/repo/worktree_effects.py")
    assert '("worktree", "add"' in source
    assert '("worktree", "remove"' in source


def test_gate_dependencies_are_declared_without_runtime_product_injection() -> None:
    gates = {gate["id"]: gate for gate in tomllib.loads(_read("system/gates.toml"))["gates"]}
    assert gates["generated-artifacts"]["depends_on"] == ["unit-architecture", "ruff"]


def test_declared_offline_providers_execute_through_one_runner() -> None:
    registry, runner = load_gate_registry_declaration().registry("runtime"), LocalGateRunner()
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
        assert (payload["gate"], [item["provider"] for item in payload["providers"]]) == (
            gate_id,
            list(gate.providers),
        )
        assert (result.verdict, result.exit_code) == (
            payload["verdict"],
            0 if payload["verdict"] == "pass" else 1,
        )


def test_playbooks_provider_publishes_closed_verdict() -> None:
    report = playbooks_report(ROOT)
    assert report["verdict"] == "pass", report["required_gaps"]
    assert "ok" not in report


def test_wheel_resources_are_native_projections_with_one_runtime_supply_hook() -> None:
    build = tomllib.loads(_read("pyproject.toml"))["tool"]["hatch"]["build"]
    wheel, sdist = build["targets"]["wheel"]["force-include"], build["targets"]["sdist"]["include"]
    assert build["targets"]["wheel"]["hooks"]["custom"] == {
        "path": "tools/ci/openspec_runtime_hook.py"
    }
    assert {"/src", "/system", "/package-lock.json", "/tools/ci/openspec_runtime_hook.py"} <= set(
        sdist
    )
    assert "force-include" not in build["targets"]["sdist"]
    for canonical, resource in (
        ("system/gates.toml", "gates.toml"),
        ("system/policies/evidence-layout.toml", "evidence_layout.toml"),
        ("system/policies/generated-artifact-topology.toml", "generated_artifact_topology.toml"),
    ):
        assert (ROOT / canonical).is_file()
        assert not (CORE / "data" / resource).exists()
        assert wheel[canonical] == f"ethos/data/{resource}"
    assert wheel["system/schemas/kernel"] == "ethos/data/schemas/kernel"
    assert wheel["package-lock.json"] == "ethos/data/supply-chain/package-lock.json"
    assert all(
        token in _read("tools/ci/openspec_runtime_hook.py")
        for token in (
            '"--omit=dev"',
            '"--offline"',
            '"--workspaces=false"',
            'build_data["force_include"]',
        )
    )


def test_declaration_backed_policies_are_first_class() -> None:
    declarations = (
        (
            "system/policies/generated-artifact-topology.toml",
            "src/ethos/contracts/artifacts/topology.py",
            (
                "GeneratedArtifactTopologyDeclaration",
                "TopologyCelRule",
                "data/generated_artifact_topology.toml",
            ),
        ),
        (
            "system/policies/evidence-layout.toml",
            "src/ethos/contracts/evidence/layout.py",
            ("EvidenceLayoutDeclaration", "freshness_expression", "data/evidence_layout.toml"),
        ),
        (
            "system/gates.toml",
            "src/ethos/contracts/gates.py",
            ("GateRegistryDeclaration", "data/gates.toml"),
        ),
    )
    for declaration, owner, tokens in declarations:
        assert (ROOT / declaration).exists()
        assert all(token in _read(owner) for token in tokens)
    assert all(
        token in _read("src/ethos/contracts/policy/cel.py")
        for token in ("evaluate_cel_predicate", "cel.NewEnv")
    )
    assert "freshness_ok" in _read("src/ethos/repository/evidence/freshness.py")
    layout = _read("system/policies/evidence-layout.toml")
    assert all(
        token in layout
        for token in (
            "component.verdict",
            'allowed_root_dirs = ["attestations"]',
            'historical_root_dirs = ["claims", "chronicle", "parity"]',
        )
    )
    assert "providers =" in _read("system/gates.toml")


def test_evidence_topology_separates_current_attestations_from_historical_bytes(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "evidence"
    (evidence / "attestations").mkdir(parents=True)
    (evidence / "attestations/current.json").write_text("{}\n")
    for root, name in (
        ("claims", "legacy.toml"),
        ("chronicle", "legacy.md"),
        ("parity", "shadow.json"),
    ):
        (evidence / root).mkdir()
        (evidence / root / name).write_text("historical\n")
    report = evidence_topology_report(tmp_path)
    assert (report["verdict"], report["counts"]) == (
        "pass",
        {"attestation_files": 1, "historical_artifacts": 3},
    )
    assert report["layout"]["attestation_root"] == "evidence/attestations"
    assert report["layout"]["historical_roots"] == [
        "evidence/claims",
        "evidence/chronicle",
        "evidence/parity",
    ]


def test_evidence_topology_blocks_invalid_or_missing_root(tmp_path: Path) -> None:
    assert evidence_topology_report(tmp_path)["verdict"] == "block"
    (tmp_path / "evidence").mkdir()
    (tmp_path / "evidence/unexpected.txt").write_text("invalid\n")
    report = evidence_topology_report(tmp_path)
    assert (report["verdict"], report["required_gaps"]) == (
        "block",
        ["evidence_root_file_not_allowed:unexpected.txt"],
    )


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
    assert (report["verdict"], report["required_gaps"]) == (
        "unknown",
        ["evidence_topology_unavailable"],
    )


def test_terminal_gate_owners_are_singular_and_hosted_logic_stays_in_tools() -> None:
    gates = {gate["id"]: gate for gate in tomllib.loads(_read("system/gates.toml"))["gates"]}
    assert gates["product-boundary"]["providers"] == [
        "ethos.repository.policy.boundary.product:product_boundary_report",
        "ethos.repository.policy.boundary.product:contributor_policy_report",
    ]
    assert gates["docs-registry"]["dimensions"] == [
        "front-matter",
        "taxonomy",
        "visible-sections",
        "command-examples",
        "plan-discoverability",
        "decision-records",
    ]
    assert (
        gates["markdown-links"]["network_policy"],
        gates["external-links"]["network_policy"],
        gates["external-links"]["dimensions"],
    ) == ("offline", "required", ["external-reachability"])
    concerns = {tool["concern"] for tool in tomllib.loads(_read("system/tools.toml"))["tool"]}
    assert {"product_boundary", "hosted_provider_observation"} <= concerns


def test_portable_docs_registry_and_hosted_observation_have_current_owners() -> None:
    assert "def markdown_links(" in _read("src/ethos/repository/registry/docs/links.py")
    assert all(
        token in _read("tools/ci/hosted_observation.py")
        for token in (
            "def provider_command(",
            "def provider_output_valid(",
            "def provider_facts(",
            "def observation_summary(",
        )
    )
