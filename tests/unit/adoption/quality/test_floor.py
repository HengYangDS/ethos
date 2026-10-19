"""Reject native gate success that proves no applicable quality property."""

from __future__ import annotations

import json
import sys
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.repository.policy.quality.obligations import quality_obligation_gaps
from ethos.repository.policy.quality.obligations import quality_verifier_gaps
from ethos.repository.policy.quality.obligations import source_verifier_gaps
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.proof import run_quality_proof

if TYPE_CHECKING:
    from pathlib import Path


def test_success_only_commands_do_not_qualify_broken_code(tmp_path: Path) -> None:
    """Two successful commands cannot prove behavior or static correctness."""
    repo = init_git_repo(tmp_path / "adopter")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "false-gate-adopter"\n\n'
        '[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
        "[proof.code_correctness_map]\n"
        'behavior = "behavior"\nstatic-analysis = "static"\n\n'
        '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
        f"command = {json.dumps([sys.executable, '-c', 'pass'])}\n"
        'dimensions = ["behavior"]\nasset_classes = ["python-code"]\n'
        'evidence_class = "proof"\ntrust_bearing = true\n\n'
        '[[proof.gates]]\nid = "static"\nkind = "typing"\n'
        f"command = {json.dumps([sys.executable, '-c', 'print("ok")'])}\n"
        'dimensions = ["static-analysis"]\nasset_classes = ["python-code"]\n'
        'evidence_class = "proof"\ntrust_bearing = true\n',
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text('raise RuntimeError("broken")\n', encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests/test_app.py").write_text('raise AssertionError("not run")\n', encoding="utf-8")
    head = commit_fixture(repo, "declare native checks")

    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert payload["data"]["checks"] == []
    assert "quality_gate_verifier_missing:behavior:behavior" in payload["required_gaps"]
    assert "quality_gate_verifier_missing:static-analysis:static" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("source_path", "broken_source"),
    [
        ("main.go", "package main\nfunc main( {\n"),
        ("main.js", "function broken( {\n"),
        ("main.ts", "export const answer: = ;\n"),
        ("main.sh", "#!/bin/sh\nif then\n"),
    ],
)
def test_non_python_source_cannot_pass_on_success_only_commands(
    tmp_path: Path, source_path: str, broken_source: str
) -> None:
    """A native source language still needs real behavior and static evidence."""
    repo = init_git_repo(tmp_path / "adopter")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    declaration = (
        'profile_id = "non-python-quality-probe"\n\n'
        '[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
        '[proof.code_correctness_map]\nbehavior = "behavior"\n'
        'static-analysis = "static"\n'
    )
    for gate_id, kind, axis in (
        ("behavior", "test", "behavior"),
        ("static", "typing", "static-analysis"),
    ):
        declaration += (
            f'\n[[proof.gates]]\nid = "{gate_id}"\nkind = "{kind}"\n'
            f"command = {json.dumps([sys.executable, '-c', f'print({gate_id!r})'])}\n"
            f'dimensions = ["{axis}"]\nasset_classes = ["source-code"]\n'
            'evidence_class = "proof"\ntrust_bearing = true\n'
        )
    profile.write_text(declaration, encoding="utf-8")
    (repo / source_path).write_text(broken_source, encoding="utf-8")
    head = commit_fixture(repo, "declare native checks")

    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert payload["data"]["checks"] == []
    assert "quality_gate_verifier_missing:behavior:behavior" in payload["required_gaps"]
    assert "quality_gate_verifier_missing:static-analysis:static" in payload["required_gaps"]


@pytest.mark.parametrize(
    ("source_path", "source_text", "asset_class", "mode", "role_attr"),
    [
        ("src/app.py", 'raise RuntimeError("broken")\n', "python-code", 0o644, ""),
        ("run", "#!/bin/sh\nif then\n", "documentation", 0o755, ""),
        ("main.ts", "export const answer: = ;\n", "documentation", 0o644, "*.ts ethos-role=code\n"),
    ],
)
def test_registry_cannot_omit_common_code_obligations(
    tmp_path: Path,
    source_path: str,
    source_text: str,
    asset_class: str,
    mode: int,
    role_attr: str,
) -> None:
    """A registry label cannot remove observed code quality obligations."""
    repo = init_git_repo(tmp_path / "adopter")
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        'profile_id = "registry-adopter"\n\n'
        '[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ngate_registry = "system/gates.toml"\n',
        encoding="utf-8",
    )
    registry = repo / "system/gates.toml"
    registry.parent.mkdir()
    marker = repo / "executed-marker"
    command = f'from pathlib import Path; Path({marker.name!r}).write_text("x")'
    registry.write_text(
        'schema_version = 1\nid = "false-quality"\n\n'
        '[proof_sets]\ndefault = ["claimed-tests"]\nfull = ["claimed-tests"]\n\n'
        '[[gates]]\nid = "claimed-tests"\nkind = "test"\n'
        f"command = {json.dumps([sys.executable, '-c', command])}\n"
        'dimensions = ["test", "coverage", "static-analysis"]\n'
        f'asset_classes = ["{asset_class}"]\n',
        encoding="utf-8",
    )
    source = repo / source_path
    source.parent.mkdir(exist_ok=True)
    source.write_text(source_text, encoding="utf-8")
    source.chmod(mode)
    if role_attr:
        (repo / ".gitattributes").write_text(role_attr, encoding="utf-8")
    if source_path.endswith(".py"):
        (repo / "tests").mkdir()
        (repo / "tests/test_app.py").write_text(
            'raise AssertionError("not run")\n', encoding="utf-8"
        )
    head = commit_fixture(repo, "claim quality without execution")

    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert payload["data"]["checks"] == []
    assert not marker.exists()
    assert any(
        str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
    )
    assert "quality_obligation_unproven:behavior" in payload["required_gaps"]
    assert "quality_obligation_unproven:static-analysis" in payload["required_gaps"]


def test_historical_policy_without_the_new_floor_keeps_its_recorded_meaning() -> None:
    """A successor floor cannot retroactively rewrite an old proof statement."""
    policy = {
        "owner": {
            "kind": "profile",
            "code_correctness_map": {"behavior": "tests"},
        },
        "gates": [{"id": "tests", "command": ["check"]}],
    }

    assert quality_obligation_gaps(policy, (), source_tree="a" * 40) == ()


def test_unknown_quality_floor_version_cannot_remove_obligations() -> None:
    """An unknown version is not permission to skip a declared quality floor."""
    policy = {
        "owner": {
            "kind": "profile",
            "quality_floor_version": 99,
            "code_correctness_map": {"behavior": "tests"},
        },
        "gates": [{"id": "tests", "command": ["check"]}],
    }

    assert quality_obligation_gaps(policy, (), source_tree="a" * 40) == (
        "quality_floor_version_unsupported:99",
    )


def test_policy_selected_provider_report_must_cover_observed_subjects() -> None:
    """Validate declared report shape and scope, not provenance of a caller-supplied check."""
    reference = "ethos.adapters.gates.python_quality:behavior_report"
    evidence = {
        "axis": "behavior",
        "source_tree": "a" * 40,
        "selected_paths": ["src/app.py"],
    }
    payload = {
        "gate": "behavior",
        "providers": [
            {
                "provider": reference,
                "report": {"verdict": "pass", "quality_evidence": evidence},
            }
        ],
    }
    check = {"action_id": "behavior", "stdout": json.dumps(payload)}
    owner: dict[str, object] = {
        "kind": "profile",
        "quality_floor_version": 1,
        "code_correctness_map": {"behavior": "behavior"},
    }
    policy = {
        "owner": owner,
        "gates": [
            {
                "id": "behavior",
                "execution_identity": ["provider", reference],
                "execution_mode": "subprocess",
                "tool_adapter": "repository-native",
            }
        ],
    }

    assert quality_obligation_gaps(policy, (check,), source_tree="a" * 40) == (
        "quality_obligation_unproven:behavior",
    )
    policy["gates"] = [
        {
            "id": "behavior",
            "execution_identity": ["provider", reference],
            "execution_mode": "provider",
            "tool_adapter": "ethos",
        }
    ]
    assert quality_obligation_gaps(policy, (check,), source_tree="a" * 40) == ()
    owner["quality_subjects"] = {"behavior": ["src/app.py", "src/other.py"]}
    assert quality_obligation_gaps(policy, (check,), source_tree="a" * 40) == (
        "quality_obligation_unproven:behavior",
    )
    evidence["selected_paths"].append("src/other.py")
    check["stdout"] = json.dumps(payload)
    assert quality_obligation_gaps(policy, (check,), source_tree="a" * 40) == ()

    assert quality_obligation_gaps(policy, None, source_tree="a" * 40) == (
        "quality_obligation_unproven:behavior",
    )
    for malformed in ("{}", '{"gate":"behavior","providers":{}}'):
        check["stdout"] = malformed
        assert quality_obligation_gaps(policy, (check,), source_tree="a" * 40) == (
            "quality_obligation_unproven:behavior",
        )


def test_frozen_transition_plan_policy_preserves_quality_subject_match() -> None:
    """Proof issuance must judge the same paths before and after plan freezing."""
    tree = "a" * 40
    reference = "ethos.adapters.gates.code_quality:behavior_report"
    policy = {
        "owner": {
            "quality_floor_version": 2,
            "code_correctness_map": {"behavior": "behavior"},
            "quality_subjects": {"behavior": ["src/app.mjs"]},
        },
        "gates": [
            {
                "id": "behavior",
                "execution_identity": ["node", "check"],
                "execution_mode": "verified-command",
                "tool_adapter": "ethos",
                "verification_providers": [reference],
            }
        ],
    }
    plan = compile_plan(
        None,
        Facts(
            repository="test:quality",
            head="b" * 40,
            tree=tree,
            observed_at=datetime.now(UTC),
            values={"execution_source": {"worktree": tree, "index": tree}},
        ),
        (PlanNode(id="behavior", kind="check", command=("node", "check")),),
        policy=policy,
    )
    evidence = {
        "axis": "behavior",
        "source_tree": tree,
        "selected_paths": ["src/app.mjs"],
    }
    check = {
        "action_id": "behavior",
        "command": ["node", "check"],
        "verification": {
            "gate": "behavior",
            "providers": [
                {
                    "provider": reference,
                    "report": {
                        "verdict": "pass",
                        "quality_evidence": evidence,
                    },
                }
            ],
        },
    }

    assert isinstance(plan.policy["owner"]["quality_subjects"]["behavior"], tuple)
    assert quality_obligation_gaps(policy, (check,), source_tree=tree) == ()
    assert quality_obligation_gaps(plan.policy, (check,), source_tree=tree) == ()
    evidence["selected_paths"] = ["src/other.mjs"]
    assert quality_obligation_gaps(plan.policy, (check,), source_tree=tree) == (
        "quality_obligation_unproven:behavior",
    )
    evidence["selected_paths"] = ["src/app.mjs"]
    evidence["source_tree"] = "c" * 40
    assert quality_obligation_gaps(plan.policy, (check,), source_tree=tree) == (
        "quality_obligation_unproven:behavior",
    )


def test_absent_or_empty_quality_owner_declares_no_code_axes() -> None:
    """No owner or an empty versioned map adds no obligation beyond source integrity."""
    assert quality_obligation_gaps({"owner": None}, (), source_tree="a" * 40) == ()
    empty = {"owner": {"quality_floor_version": 1, "code_correctness_map": {}}}
    assert quality_obligation_gaps(empty, (), source_tree="a" * 40) == ()


def test_versioned_floor_requires_exact_nonempty_subjects() -> None:
    """Version 2 cannot prove an axis whose declared subjects are empty."""
    owner = {
        "quality_floor_version": 2,
        "code_correctness_map": {"behavior": "tests"},
        "quality_subjects": {"behavior": []},
    }
    assert quality_obligation_gaps({"owner": owner, "gates": []}, (), source_tree="a" * 40) == (
        "quality_obligation_unproven:behavior",
    )


def test_selected_verifiers_must_name_product_quality_providers() -> None:
    """A malformed provider list or a non-provider identity cannot verify an axis."""
    gates = (
        {
            "id": "tests",
            "tool_adapter": "ethos",
            "execution_mode": "verified-command",
            "verification_providers": "not-a-list",
        },
        {
            "id": "lint",
            "tool_adapter": "ethos",
            "execution_mode": "provider",
            "execution_identity": ["command"],
            "dimensions": ["behavior"],
        },
    )
    assert quality_verifier_gaps({"code_correctness_map": {"behavior": "tests"}}, gates) == (
        "quality_gate_verifier_missing:behavior:tests",
        "quality_gate_verifier_missing:behavior:lint",
    )


@pytest.mark.parametrize("prerequisites", ["not-a-list", ["", "gap"]])
def test_source_binding_prerequisites_are_exact_gap_names(prerequisites: object) -> None:
    """Serialized binding prerequisites cannot smuggle blank or scalar gap evidence."""
    assert source_verifier_gaps({"source_binding_gaps": prerequisites}, ()) == (
        "source_binding_observation_invalid",
    )
