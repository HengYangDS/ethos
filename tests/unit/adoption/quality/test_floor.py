"""Reject native gate success that proves no applicable quality property."""

from __future__ import annotations

import json
import sys
from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING

import pytest

from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.repository.policy.gates import quality_obligation_gaps
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.proof import declare_quality_fixture
from tests.support.proof import python_quality_files

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    ("source_path", "broken_source"),
    [
        ("src/app.py", 'raise RuntimeError("broken")\n'),
        ("main.go", "package main\nfunc main( {\n"),
        ("main.js", "function broken( {\n"),
        ("main.ts", "export const answer: = ;\n"),
        ("main.sh", "#!/bin/sh\nif then\n"),
    ],
)
def test_success_only_commands_do_not_qualify_broken_code(
    tmp_path: Path, source_path: str, broken_source: str
) -> None:
    """Every native code language requires evidence, not two successful commands."""
    repo = init_git_repo(tmp_path / "adopter")
    python_source = source_path.endswith(".py")
    declare_quality_fixture(
        repo,
        gates=tuple(
            Gate(
                id=name,
                kind=kind,
                command=(sys.executable, "-c", command if python_source else f"print({name!r})"),
                dimensions=(axis,),
                asset_classes=("python-code" if python_source else "source-code",),
                evidence_class="proof",
                trust_bearing=True,
            )
            for name, kind, command, axis in (
                ("behavior", "test", "pass", "behavior"),
                ("static", "typing", 'print("ok")', "static-analysis"),
            )
        ),
    )
    source = repo / source_path
    source.parent.mkdir(exist_ok=True)
    source.write_text(broken_source, encoding="utf-8")
    if python_source:
        (repo / "tests").mkdir()
        (repo / "tests/test_app.py").write_text(
            'raise AssertionError("not run")\n', encoding="utf-8"
        )
    head = commit_fixture(repo, "declare native checks")

    payload = run_ethos_blocked(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )

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

    payload = run_ethos_blocked(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )

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


@pytest.mark.parametrize(
    "defect",
    [
        "none",
        "strict-config",
        "plugin-disabled",
        "wrong-result",
        "unused-source",
        "lint-error",
        "all-skipped",
        "missing-lock",
        "lock-drift",
    ],
)
@pytest.mark.parametrize("gate_owner", ["inline", "registry"])
def test_real_locked_python_checks_qualify_the_selected_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str, gate_owner: str
) -> None:
    """Native tests and static diagnostics can satisfy the same public floor."""
    repo = committed_source_repo(tmp_path, python_quality_files(defect=defect))
    declare_quality_fixture(repo, provider="python_quality", registry=gate_owner == "registry")
    head = commit_fixture(repo, "bind real native quality")
    if defect == "plugin-disabled":
        monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert payload["summary"]["proof_attestation_issued"] is False
    if defect == "strict-config":
        assert not (repo / ".cache/pytest").exists()
    if defect in {"none", "strict-config", "plugin-disabled"}:
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert payload["required_gaps"] == []
        return
    assert result.returncode != 0
    assert payload["verdict"] == "block"
    axis = "static-analysis" if defect == "lint-error" else "behavior"
    assert f"quality_obligation_unproven:{axis}" in payload["required_gaps"]


@pytest.mark.parametrize("evidence_case", ["missing", "complete"])
def test_one_gate_can_supply_both_code_axes(tmp_path: Path, evidence_case: str) -> None:
    """One native gate may supply both axes; a missing axis remains blocked."""
    providers = ["ethos.adapters.gates.python_quality:behavior_report"]
    if evidence_case == "complete":
        providers.append("ethos.adapters.gates.python_quality:static_report")
    repo = committed_source_repo(tmp_path, python_quality_files())
    declare_quality_fixture(
        repo, gates=(Gate(id="quality", kind="test", providers=tuple(providers)),)
    )
    commit_fixture(repo, "declare one native quality gate")
    result = run_ethos_raw(
        "prove",
        "--host",
        "--execute",
        "--full",
        "--expect-head",
        git(repo, "rev-parse", "HEAD"),
        "--json",
        cwd=repo,
    )
    payload = json.loads(result.stdout)
    if evidence_case == "complete":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert len(payload["data"]["checks"]) == 1
    else:
        assert result.returncode != 0
        assert "quality_gate_verifier_missing:static-analysis:quality" in payload["required_gaps"]
        assert payload["data"]["checks"] == []
