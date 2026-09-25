"""Reject native gate success that proves no applicable quality property."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.gates import quality_obligation_gaps
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo

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

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert any(
        str(gap).startswith("quality_obligation_unproven:") for gap in payload["required_gaps"]
    )


def test_registry_cannot_omit_common_code_obligations(tmp_path: Path) -> None:
    """A registry representation cannot make observed Python code quality optional."""
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
        'asset_classes = ["python-code"]\n',
        encoding="utf-8",
    )
    (repo / "src").mkdir()
    (repo / "src/app.py").write_text('raise RuntimeError("broken")\n', encoding="utf-8")
    (repo / "tests").mkdir()
    (repo / "tests/test_app.py").write_text('raise AssertionError("not run")\n', encoding="utf-8")
    head = commit_fixture(repo, "claim quality without execution")

    result = run_ethos_raw(
        "prove", "--host", "--execute", "--full", "--expect-head", head, "--json", cwd=repo
    )
    payload = json.loads(result.stdout)

    assert result.returncode != 0
    assert payload["verdict"] == "block"
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
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "quality-sample"\nversion = "0.1.0"\n'
        'requires-python = ">=3.12"\n\n'
        '[dependency-groups]\ndev = ["pytest>=9.1.1", "pytest-cov>=7.1.0"]\n\n'
        '[build-system]\nrequires = ["hatchling>=1.32.3"]\n'
        'build-backend = "hatchling.build"\n\n'
        '[tool.hatch.build.targets.wheel]\npackages = ["src/sample"]\n',
        encoding="utf-8",
    )
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
        locked = subprocess.run(
            (sys.executable, "-m", "uv", "lock", "--offline"),
            cwd=repo,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        assert locked.returncode == 0, locked.stderr
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
