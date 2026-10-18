"""Validate rule models and deterministic matching without redundant projections."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest
import tomli_w
from pydantic import ValidationError

from ethos.adapters.process import run_command
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.contracts.gates import load_gate_registry_declaration
from ethos.contracts.rules import Rule
from ethos.contracts.rules import RuleSet
from ethos.domain.plan import matching_rule_gates
from ethos.repository.policy.rules.compile import compile_rules
from ethos.repository.policy.rules.config import resolve_profile_stack
from ethos.repository.policy.schema import validate_schema_instance
from tests.support.ethos_cli_runner import result_data
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import declare_fixture_documentation_proof
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_active_commitment

if TYPE_CHECKING:
    from pathlib import Path


def _rule(**updates: object) -> dict[str, object]:
    return {
        "id": "custom.docs",
        "owner": "docs-team",
        "authority_ref": "docs/governance/docs.md",
        "contract_ref": "docs/governance/docs.md",
        "path_globs": ["docs/**"],
        "severity": "advisory",
        "required_gates": ["docs-registry"],
        "stop_condition": "docs_gap",
    } | updates


def _write_rules(root: Path, *rules: dict[str, object], **extra: object) -> None:
    path = root / ".ethos/rules.toml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(tomli_w.dumps({"rule": list(rules)} | extra), encoding="utf-8")


def test_rule_contract_schemas_validate_minimal_payloads() -> None:
    assert validate_schema_instance("rule.schema.json", _rule())["verdict"] == "pass"


def test_rule_contracts_serialize_to_schema_payloads_without_handwritten_conversion() -> None:
    rule = Rule.model_validate(_rule())
    rule_set = RuleSet(id="custom", profile_layers=("generic",), rules=(rule,))
    assert rule_set.model_dump(mode="json") == {
        "schema_version": 1,
        "id": "custom",
        "profile_layers": ["generic"],
        "rules": [_rule(version=1)],
    }
    with pytest.raises(ValidationError):
        Rule.model_validate(_rule(non_waivable=1))


@pytest.mark.parametrize(
    "updates", [{}, {"owner": "other"}, {"version": 2}, {"non_waivable": False}]
)
def test_rule_set_rejects_duplicate_resolved_identity(updates: dict[str, object]) -> None:
    """A version or native-owner difference cannot create two active meanings for one id."""
    first = Rule.model_validate(_rule(non_waivable=True))
    second = Rule.model_validate(_rule(non_waivable=True) | updates)
    with pytest.raises(ValidationError, match=r"rule_identity_conflict:custom\.docs"):
        RuleSet(id="custom", profile_layers=("generic",), rules=(first, second))


@pytest.mark.parametrize("identity", ["custom.docs", "starter.governance"])
def test_rule_conflict_reaches_selection_without_partial_policy(
    tmp_path: Path, identity: str
) -> None:
    """Both repository duplicates and baseline collisions block the real compiler consumer."""
    first = _rule(id=identity, non_waivable=True)
    records = (first, _rule(id=identity)) if identity == "custom.docs" else (first,)
    _write_rules(tmp_path, *records)
    expected = [f"rule_identity_conflict:{identity}"]
    compiled = compile_rules(tmp_path)
    assert compiled["compile_gaps"] == expected
    assert compiled["rules"] == []
    assert matching_rule_gates(tmp_path, ("docs",)) == ([], [], expected)


def test_compiled_rule_projection_omits_unconsumed_digests(tmp_path: Path) -> None:
    compiled = compile_rules(tmp_path)
    assert "rule_set_digest" not in compiled
    assert "compiled_policy_digest" not in compiled


def test_compile_rules_rejects_retired_rule_keys_without_normalization(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        {
            "id": "legacy.docs",
            "risk": "docs",
            "paths": ["docs/**"],
            "requires": ["docs-registry"],
            "evidence": ["governance-proof"],
        },
    )
    compiled = compile_rules(tmp_path)
    assert any(
        gap.startswith("rule_schema_invalid:legacy.docs:") for gap in compiled["compile_gaps"]
    )


def test_noncanonical_profile_fails_closed_without_alias_normalization() -> None:
    profiles, gaps = resolve_profile_stack({"profiles": {"active": ["python-package"]}})
    assert profiles == ["generic"]
    assert gaps == ["rules_profile_invalid:unknown_profile:python-package"]


def test_unknown_rule_gate_is_a_compile_gap_without_synthetic_plan_gate(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        _rule(
            id="custom.notes",
            path_globs=["notes/**"],
            required_gates=["missing-gate"],
            stop_condition="notes_gap",
        ),
    )
    compiled = compile_rules(tmp_path)
    matched_rules, required_gates, plan_gaps = matching_rule_gates(tmp_path, ("notes",))
    assert "unknown_rule_gate:custom.notes:missing-gate" in compiled["compile_gaps"]
    assert matched_rules == [
        {
            "id": "custom.notes",
            "subject": "",
            "matched_paths": ["notes"],
            "required_gates": [],
            "evidence_requirements": [],
        }
    ]
    assert required_gates == []
    assert "unknown_rule_gate:custom.notes:missing-gate" in plan_gaps


def test_rules_cannot_define_parallel_gate_commands(tmp_path: Path) -> None:
    _write_rules(
        tmp_path,
        _rule(
            id="custom.notes",
            path_globs=["notes/**"],
            severity="blocking",
            required_gates=["shadow"],
            stop_condition="notes_gap",
        ),
        gates={"shadow": {"command": "python shadow.py", "blocking": True}},
    )
    compiled = compile_rules(tmp_path)
    assert "shadow" not in compiled["gate_definitions"]
    assert "unknown_rule_gate:custom.notes:shadow" in compiled["compile_gaps"]


def test_compiled_rule_matching_treats_trailing_glob_as_its_directory(tmp_path: Path) -> None:
    _write_rules(tmp_path, _rule(id="custom.first"), _rule(id="custom.second"))
    matched_rules, required_gates, plan_gaps = matching_rule_gates(tmp_path, ("docs",))
    assert plan_gaps == []
    assert {rule["id"] for rule in matched_rules} == {
        "starter.docs",
        "custom.first",
        "custom.second",
    }
    assert [gate["id"] for gate in required_gates] == ["docs-registry"]


@pytest.mark.parametrize("registry_file", [False, True], ids=["profile", "registry"])
def test_compile_rules_uses_selected_root_gate_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, registry_file: bool
) -> None:
    """Rule selection uses the target's native owner, never ambient or packaged gates."""
    target = tmp_path / "target"
    target.mkdir()
    _write_rules(
        target,
        _rule(id="custom.native", path_globs=["notes/**"], required_gates=["native-quality"]),
    )
    gate_ids = ["docs-registry", "schemas", "skills", "native-quality"]
    gates = [
        {"id": gate_id, "kind": "check", "command": ["target-quality", gate_id]}
        for gate_id in gate_ids
    ]
    proof = (
        {"gate_registry": ".config/checks/gates.toml"}
        if registry_file
        else {
            "code_correctness_gates": gate_ids,
            "code_correctness_map": {
                "behavior": "native-quality",
                "static-analysis": "native-quality",
            },
            "gates": gates,
        }
    )
    (target / ".ethos/profile.toml").write_text(
        tomli_w.dumps({"profile_id": "target", "proof": proof}), encoding="utf-8"
    )
    if registry_file:
        registry = target / ".config/checks/gates.toml"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            tomli_w.dumps(
                {
                    "id": "target",
                    "proof_sets": {"default": gate_ids, "full": gate_ids},
                    "gates": gates,
                }
            ),
            encoding="utf-8",
        )
    ambient = tmp_path / "ambient"
    ambient.mkdir()
    (ambient / ".ethos").mkdir()
    (ambient / ".ethos/profile.toml").write_text(
        tomli_w.dumps({"profile_id": "ambient"}), encoding="utf-8"
    )
    monkeypatch.chdir(ambient)

    compiled = compile_rules(target)
    expected = {
        "id": "native-quality",
        "gate_source": "repository",
        "command": "target-quality native-quality",
        "blocking": True,
    }
    assert compiled["compile_gaps"] == []
    assert set(compiled["gate_definitions"]) == set(gate_ids)
    assert compiled["gate_definitions"]["native-quality"] == expected
    matched, selected, gaps = matching_rule_gates(target, ("notes",))
    assert [rule["id"] for rule in matched] == ["custom.native"]
    assert selected == [expected]
    assert gaps == []

    _write_rules(
        target,
        _rule(id="custom.missing", path_globs=["notes/**"], required_gates=["unit-architecture"]),
    )
    matched, selected, gaps = matching_rule_gates(target, ("notes",))
    assert [rule["id"] for rule in matched] == ["custom.missing"]
    assert selected == []
    assert gaps == ["unknown_rule_gate:custom.missing:unit-architecture"]


@pytest.mark.parametrize(
    ("profile", "registry", "error"),
    [
        ("profile_id = 1\n", None, "repository_profile_invalid"),
        (
            'profile_id = "target"\n[proof]\ngate_registry = ".config/gates.toml"\n',
            None,
            "gate_registry_invalid:.config/gates.toml",
        ),
        (
            'profile_id = "target"\n[proof]\ngate_registry = ".config/gates.toml"\n',
            "id = 1\n",
            "gate_registry_invalid:.config/gates.toml",
        ),
    ],
    ids=["invalid-profile", "missing-registry", "invalid-registry"],
)
def test_compile_rules_rejects_unavailable_native_gate_authority(
    tmp_path: Path, profile: str, registry: str | None, error: str
) -> None:
    """An invalid explicit native owner cannot fall back to the product registry."""
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos/profile.toml").write_text(profile, encoding="utf-8")
    if registry is not None:
        (tmp_path / ".config").mkdir()
        (tmp_path / ".config/gates.toml").write_text(registry, encoding="utf-8")
    with pytest.raises(ValueError, match=error):
        compile_rules(tmp_path)


def test_product_starter_rules_keep_product_gates_beside_target_authority(tmp_path: Path) -> None:
    """Rules reuse product-owned checks while native descriptors retain target authority."""
    gate = {"id": "native-quality", "kind": "check", "command": ["target-quality"]}
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos/profile.toml").write_text(
        tomli_w.dumps({"profile_id": "target", "proof": {"gate_registry": "gates.toml"}}),
        encoding="utf-8",
    )
    (tmp_path / "gates.toml").write_text(
        tomli_w.dumps(
            {
                "id": "target",
                "proof_sets": {"default": ["native-quality"], "full": ["native-quality"]},
                "gates": [gate],
            }
        ),
        encoding="utf-8",
    )
    packaged = {
        name: descriptor | {"gate_source": "product"}
        for name, descriptor in compile_rules(tmp_path.parent / "absent")[
            "gate_definitions"
        ].items()
    }

    compiled = compile_rules(tmp_path)
    assert compiled["compile_gaps"] == []
    assert compiled["gate_definitions"]["schemas"] == packaged["schemas"]
    assert compiled["gate_definitions"]["native-quality"]["command"] == "target-quality"
    assert "unit-architecture" not in compiled["gate_definitions"]
    matched, selected, gaps = matching_rule_gates(tmp_path, ("openspec/changes/x/tasks.md",))
    assert [rule["id"] for rule in matched] == ["starter.governance"]
    assert selected == [packaged["schemas"]]
    assert gaps == []

    _write_rules(
        tmp_path,
        _rule(id="custom.governance", required_gates=["openspec", "schemas"]),
    )
    compiled = compile_rules(tmp_path)
    assert compiled["compile_gaps"] == []
    assert compiled["gate_definitions"]["openspec"] == packaged["openspec"]
    assert compiled["gate_definitions"]["schemas"] == packaged["schemas"]
    assert "unit-architecture" not in compiled["gate_definitions"]
    matched, selected, gaps = matching_rule_gates(tmp_path, ("docs/guide.md",))
    assert {rule["id"] for rule in matched} == {"starter.docs", "custom.governance"}
    assert {gate["id"] for gate in selected} == {"docs-registry", "openspec", "schemas"}
    assert gaps == []


@pytest.mark.parametrize("native_id", ["docs-registry", "document-registry"])
def test_common_rule_preserves_product_gate_origin(tmp_path: Path, native_id: str) -> None:
    """Renaming an adopter gate cannot capture or alter a common-rule obligation."""
    (tmp_path / ".ethos").mkdir()
    (tmp_path / ".ethos/profile.toml").write_text(
        tomli_w.dumps(
            {
                "profile_id": "target",
                "proof": {
                    "code_correctness_gates": [native_id],
                    "gates": [{"id": native_id, "kind": "check", "command": ["target-check"]}],
                },
            }
        ),
        encoding="utf-8",
    )
    packaged = {
        name: descriptor | {"gate_source": "product"}
        for name, descriptor in compile_rules(tmp_path.parent / "absent")[
            "gate_definitions"
        ].items()
    }
    compiled = compile_rules(tmp_path)
    assert compiled["compile_gaps"] == []
    for name in ("docs-registry", "schemas"):
        assert compiled["gate_definitions"][name]["command"] == packaged[name]["command"]
    matched, selected, gaps = matching_rule_gates(
        tmp_path, ("docs/guide.md", "openspec/changes/x/tasks.md")
    )
    assert {rule["id"] for rule in matched} == {"starter.docs", "starter.governance"}
    assert {gate["id"] for gate in selected} == {"docs-registry", "schemas"}
    assert gaps == []


def test_public_native_product_composition_binds_target_and_refuses_stale_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rules, public planning and actual CLI execution retain one target-bound selection."""
    monkeypatch.delenv("ETHOS_CHANGE", raising=False)
    monkeypatch.delenv("ETHOS_ACTOR", raising=False)
    root = init_git_repo(tmp_path / "repo")
    declare_fixture_documentation_proof(root)
    write_active_commitment(root, change_id="gate-composition")
    _write_rules(
        root,
        _rule(
            id="custom.native",
            path_globs=["openspec/**"],
            required_gates=["openspec-baseline"],
        ),
    )
    commit_fixture(root, "declare composed rule demand")
    tasks = root / "openspec/changes/gate-composition/tasks.md"
    tasks.write_text(tasks.read_text().replace("fixture lifecycle", "native composition"))
    plan = run_ethos("plan", "--changed", "--change", "gate-composition", "--json", cwd=root)
    assert plan["verdict"] == "pass"
    plan_data = result_data(plan)
    assert {gate["id"] for gate in plan_data["required_gates"]} == {
        "openspec-baseline",
        "schemas",
    }
    assert {node["id"] for node in plan_data["transition_plan"]["nodes"]} == {
        "openspec-baseline",
        "schemas",
    }
    head = commit_fixture(root, "bind composed rule demand")
    policy = resolve_gate_policy(
        root,
        tree_ref=head,
        gate_ids=("openspec-baseline", "schemas"),
        product_gate_ids=("schemas",),
    )
    assert policy.gaps == ()
    assert set(policy.registry) == {"openspec-baseline"}
    assert policy.product_gate_ids == ("schemas",)
    assert policy.declaration == load_gate_registry_declaration(root / "system/gates.toml")
    assert policy.registry["openspec-baseline"].command == (
        "git",
        "grep",
        "-q",
        "^### Requirement:",
        "HEAD",
        "--",
        "openspec/specs",
    )
    assert {path for path, _ in dict(policy.sources)["schemas"]} == {
        "@ethos/repository/policy/schema.py"
    }
    command = (
        sys.executable,
        "-B",
        "-I",
        "-m",
        "ethos.cli",
        "prove",
        "--root",
        str(root),
        "--host",
        "--execute",
        "--gate",
        "openspec-baseline",
        "--product-gate",
        "schemas",
        "--expect-head",
        head,
        "--json",
    )
    completed = run_command(root, command, timeout=60)
    report = json.loads(completed.stdout)
    assert completed.returncode == 0, completed.stderr
    assert report["verdict"] == "pass"
    assert report["data"]["policy_digest"] == policy.digest
    assert report["summary"]["proof_attestation_issued"] is False
    assert {check["action_id"] for check in report["data"]["checks"]} == set(policy.gate_ids)
    retired = root / "system/schemas/kernel/capability-profile.schema.json"
    retired.parent.mkdir(parents=True)
    retired.write_text("{}\n")
    successor = commit_fixture(root, "record target schema violation")
    stale = run_command(root, command, timeout=60)
    assert stale.returncode != 0
    assert "expected_head_mismatch" in json.loads(stale.stdout)["required_gaps"]
    current = run_command(
        root, tuple(successor if part == head else part for part in command), timeout=60
    )
    refused = json.loads(current.stdout)
    assert current.returncode != 0
    assert refused["verdict"] == "block"
    schema = next(check for check in refused["data"]["checks"] if check["action_id"] == "schemas")
    observation = json.loads(schema["stdout"])["providers"][0]["report"]
    assert observation["required_gaps"] == ["schema_retired:capability-profile.schema.json"]
    assert schema["verdict"] == "block"


@pytest.mark.parametrize("owner", ["command", "provider"])
def test_rule_sources_refuse_distinct_owners_for_the_same_gate(tmp_path: Path, owner: str) -> None:
    """Empty provider commands cannot hide a conflicting native/common rule meaning."""
    execution = (
        {"command": ["target-check"]}
        if owner == "command"
        else {"providers": ["ethos.adapters.gates.ty:ty_gate_report"]}
    )
    _write_rules(tmp_path, _rule())
    (tmp_path / ".ethos/profile.toml").write_text(
        tomli_w.dumps(
            {
                "profile_id": "target",
                "proof": {
                    "code_correctness_gates": ["docs-registry"],
                    "gates": [{"id": "docs-registry", "kind": "check", **execution}],
                },
            }
        ),
        encoding="utf-8",
    )
    _, _, gaps = matching_rule_gates(tmp_path, ("docs/guide.md",))
    assert "rule_gate_origin_conflict:custom.docs:docs-registry" in gaps


@pytest.mark.parametrize("registry_file", [False, True])
def test_rule_source_comparison_precedes_execution_remapping(
    tmp_path: Path, *, registry_file: bool
) -> None:
    """A complete equal source remains equal when execution adapts its repository boundary."""
    _write_rules(tmp_path, _rule(required_gates=["schemas"]))
    schema = load_gate_registry_declaration().registry()["schemas"]
    (tmp_path / ".ethos/profile.toml").write_text(
        tomli_w.dumps(
            {
                "profile_id": "target",
                "proof": {
                    "code_correctness_gates": ["native", "schemas"],
                    "gates": [
                        {"id": "native", "kind": "check", "command": ["target-check"]},
                        schema.model_dump(mode="json", exclude_none=True),
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    if registry_file:
        registry = tmp_path / ".config/checks/gates.toml"
        registry.parent.mkdir(parents=True)
        registry.write_text(
            tomli_w.dumps(
                {
                    "id": "target",
                    "proof_sets": {"default": ["schemas"], "full": ["schemas"]},
                    "gates": [schema.model_dump(mode="json", exclude_none=True)],
                }
            ),
            encoding="utf-8",
        )
        (tmp_path / ".ethos/profile.toml").write_text(
            tomli_w.dumps(
                {
                    "profile_id": "target",
                    "proof": {"gate_registry": ".config/checks/gates.toml"},
                }
            ),
            encoding="utf-8",
        )
    compiled = compile_rules(tmp_path)
    assert compiled["compile_gaps"] == []
    assert compiled["gate_definitions"]["schemas"]["gate_source"] == "product"
