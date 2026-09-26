"""Reject native gate success that proves no applicable quality property."""

from __future__ import annotations

import json
import sys
from datetime import UTC
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.gates.python_quality as native_quality
from ethos.contracts.plan import PlanNode
from ethos.contracts.plan import compile_plan
from ethos.contracts.semantic import Facts
from ethos.repository.policy.gates import quality_obligation_gaps
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo


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

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert any(
        str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
    )


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

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert any(
        str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
    )


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
    registry.write_text(
        'schema_version = 1\nid = "false-quality"\n\n'
        '[proof_sets]\ndefault = ["claimed-tests"]\nfull = ["claimed-tests"]\n\n'
        '[[gates]]\nid = "claimed-tests"\nkind = "test"\n'
        f"command = {json.dumps([sys.executable, '-c', 'pass'])}\n"
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

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
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
    policy = {
        "owner": {
            "kind": "profile",
            "quality_floor_version": 1,
            "code_correctness_map": {"behavior": "behavior"},
        },
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
    policy["owner"]["quality_subjects"] = {"behavior": ["src/app.py", "src/other.py"]}
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
    tmp_path: Path, defect: str, gate_owner: str
) -> None:
    """Native tests and static diagnostics can satisfy the same public floor."""
    repo = init_git_repo(tmp_path / "adopter")
    (repo / ".gitignore").write_text(".venv/\n__pycache__/\n", encoding="utf-8")
    fixture = Path(__file__).resolve().parents[2] / "fixtures/quality-sample"
    (repo / "pyproject.toml").write_bytes((fixture / "pyproject.toml").read_bytes())
    source = repo / "src/sample/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def answer() -> int:\n    return 41\n"
        if defect == "wrong-result"
        else "import os\n\ndef answer() -> int:\n    return 42\n"
        if defect == "lint-error"
        else "def answer() -> int:\n    return 42\n",
        encoding="utf-8",
    )
    if defect == "unused-source":
        (repo / "src/sample/unused.py").write_text(
            "def never_called() -> int:\n    return 0\n", encoding="utf-8"
        )
    test = repo / "tests/test_sample.py"
    test.parent.mkdir()
    test.write_text(
        "import pytest\n\nfrom sample import answer\n\n\n"
        '@pytest.mark.skip(reason="not executed")\n'
        "def test_answer() -> None:\n    assert answer() == 42\n"
        if defect == "all-skipped"
        else "from sample import answer\n\n\n"
        "def test_answer() -> None:\n    assert answer() == 42\n",
        encoding="utf-8",
    )
    profile = repo / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile_header = 'profile_id = "qualified-adopter"\n\n[openspec]\nmaterial_paths = ["**"]\n\n'
    if gate_owner == "registry":
        profile.write_text(
            profile_header + '[proof]\ngate_registry = "system/gates.toml"\n',
            encoding="utf-8",
        )
        registry = repo / "system/gates.toml"
        registry.parent.mkdir()
        registry.write_text(
            'schema_version = 1\nid = "qualified-adopter"\n\n'
            '[proof_sets]\ndefault = ["behavior", "static"]\n'
            'full = ["behavior", "static"]\n\n'
            '[[gates]]\nid = "behavior"\nkind = "test"\n'
            'profile = "repository"\nexecution_mode = "provider"\ntool_adapter = "ethos"\n'
            'providers = ["ethos.adapters.gates.python_quality:behavior_report"]\n\n'
            '[[gates]]\nid = "static"\nkind = "lint"\n'
            'profile = "repository"\nexecution_mode = "provider"\ntool_adapter = "ethos"\n'
            'providers = ["ethos.adapters.gates.python_quality:static_report"]\n',
            encoding="utf-8",
        )
    else:
        profile.write_text(
            profile_header + '[proof]\ncode_correctness_gates = ["behavior", "static"]\n\n'
            '[proof.code_correctness_map]\nbehavior = "behavior"\nstatic-analysis = "static"\n\n'
            '[[proof.gates]]\nid = "behavior"\nkind = "test"\n'
            'providers = ["ethos.adapters.gates.python_quality:behavior_report"]\n\n'
            '[[proof.gates]]\nid = "static"\nkind = "lint"\n'
            'providers = ["ethos.adapters.gates.python_quality:static_report"]\n',
            encoding="utf-8",
        )
    if defect != "missing-lock":
        (repo / "uv.lock").write_bytes((fixture / "uv.lock").read_bytes())
    if defect == "lock-drift":
        project = repo / "pyproject.toml"
        project.write_text(
            project.read_text(encoding="utf-8").replace(
                '"pytest-cov>=7.1.0"]', '"pytest-cov>=7.1.0", "pytest-timeout>=2.4.0"]'
            ),
            encoding="utf-8",
        )
    head = commit_fixture(repo, "bind real native quality")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    if defect == "none":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert payload["required_gaps"] == []
    else:
        assert result.returncode != 0
        assert payload["verdict"] == "block"
        axis = "static-analysis" if defect == "lint-error" else "behavior"
        assert f"quality_obligation_unproven:{axis}" in payload["required_gaps"]
    assert payload["summary"]["proof_attestation_issued"] is False


def test_native_quality_requires_committed_python_scope(tmp_path: Path) -> None:
    """No HEAD or selected Python file must not become an empty success."""
    untracked = tmp_path / "untracked"
    untracked.mkdir()
    assert native_quality.static_report(untracked)["required_gaps"] == [
        "quality_static_source_head_missing"
    ]

    repo = init_git_repo(tmp_path / "repo")
    assert native_quality.static_report(repo)["required_gaps"] == [
        "quality_static_python_sources_missing"
    ]


def test_native_behavior_requires_source_tests_and_a_lock(tmp_path: Path) -> None:
    """An unrecognized or unlocked scope cannot claim behavior coverage."""
    repo = init_git_repo(tmp_path / "repo")
    source = repo / "src/app.py"
    source.parent.mkdir()
    source.write_text("def answer(): return 42\n", encoding="utf-8")
    commit_fixture(repo, "add source without tests")
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_scope_unrecognized"
    ]

    test = repo / "tests/test_app.py"
    test.parent.mkdir()
    test.write_text("def test_answer(): assert True\n", encoding="utf-8")
    commit_fixture(repo, "add tests without lock")
    assert native_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_locked_toolchain_missing"
    ]


@pytest.mark.parametrize(
    ("stdout", "returncode", "gap"),
    [
        ("{", 0, "quality_static_report_invalid"),
        ("{}", 0, "quality_static_report_invalid"),
        ("[]", 1, "quality_static_diagnostics"),
        ('[{"code":"E999"}]', 1, "quality_static_diagnostics"),
    ],
)
def test_native_static_adapter_distinguishes_report_from_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    returncode: int,
    gap: str,
) -> None:
    """A malformed tool report differs from a valid report containing findings."""
    monkeypatch.setattr(native_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        native_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=stdout, returncode=returncode),
    )
    assert native_quality.static_report(tmp_path)["required_gaps"] == [gap]
