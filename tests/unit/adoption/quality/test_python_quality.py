"""Qualify the public quality floor with real locked native Python checks."""

from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

import pytest
import tomli_w

from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import git
from tests.support.proof import declare_quality_profile
from tests.support.proof import run_quality_proof


def _declare_unlocked_dependency(project: Path, dependency: str) -> None:
    """Construct actual dependency drift without relying on serialized formatting."""
    preimage = project.read_bytes()
    declaration = tomllib.loads(preimage.decode("utf-8"))
    dependencies = declaration["dependency-groups"]["dev"]
    assert dependency not in dependencies
    dependencies.append(dependency)
    project.write_text(tomli_w.dumps(declaration), encoding="utf-8")
    assert project.read_bytes() != preimage
    assert tomllib.loads(project.read_text())["dependency-groups"]["dev"] == dependencies


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
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitignore": ".venv/\n__pycache__/\n",
            "pyproject.toml": (fixture / "pyproject.toml").read_text(),
            "src/sample/__init__.py": "def answer() -> int:\n    return 41\n"
            if defect == "wrong-result"
            else "import os\n\ndef answer() -> int:\n    return 42\n"
            if defect == "lint-error"
            else "def answer() -> int:\n    return 42\n",
            "tests/test_sample.py": "import pytest\n\nfrom sample import answer\n\n\n"
            '@pytest.mark.skip(reason="not executed")\n'
            "def test_answer() -> None:\n    assert answer() == 42\n"
            if defect == "all-skipped"
            else "from sample import answer\n\n\n"
            "def test_answer() -> None:\n    assert answer() == 42\n",
            **(
                {
                    "pytest.toml": '[pytest]\naddopts = ["--strict-config"]\n'
                    'cache_dir = ".cache/pytest"\n'
                }
                if defect == "strict-config"
                else {}
            ),
        },
    )
    if defect == "unused-source":
        (repo / "src/sample/unused.py").write_text(
            "def never_called() -> int:\n    return 0\n", encoding="utf-8"
        )
    declare_quality_profile(repo, "profile" if gate_owner == "inline" else "registry")
    if gate_owner == "inline":
        profile = repo / ".ethos/profile.toml"
        declaration = tomllib.loads(profile.read_text(encoding="utf-8"))
        declaration["proof"]["code_correctness_gates"] = ["checks", "static"]
        declaration["proof"]["gates"].append(
            {
                "id": "checks",
                "kind": "test",
                "command": [sys.executable, "-c", 'print("root executed")'],
                "depends_on": ["behavior"],
            }
        )
        profile.write_text(tomli_w.dumps(declaration), encoding="utf-8")
    if defect != "missing-lock":
        (repo / "uv.lock").write_bytes((fixture / "uv.lock").read_bytes())
    if defect == "lock-drift":
        _declare_unlocked_dependency(repo / "pyproject.toml", "pytest-timeout")
    head = commit_fixture(repo, "bind real native quality", format_paths=(".ethos/profile.toml",))
    if defect == "plugin-disabled":
        monkeypatch.setenv("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")

    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)

    if defect in {"none", "strict-config", "plugin-disabled"}:
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        assert payload["required_gaps"] == []
        if gate_owner == "inline":
            checks = {check["action_id"]: check for check in payload["data"]["checks"]}
            assert {"behavior", "checks", "static", "config-quality", "source-format"} <= set(
                checks
            )
            assert "optional" not in checks
            assert all(check["verdict"] == "pass" for check in checks.values())
            assert tuple(checks).index("behavior") < tuple(checks).index("checks")
            assert checks["checks"]["stdout"].strip() == "root executed"
            report = json.loads(checks["behavior"]["stdout"])["providers"][0]["report"]["native"][0]
            assert report["tests"]["total"] == 1
            assert report["coverage"]["covered"] > 0
            command = report["native"]["command"]
            assert any(arg.startswith("--junitxml=") for arg in command)
            assert "--cov=." in command
        if defect == "strict-config":
            assert not (repo / ".cache/pytest").exists()
    else:
        assert result.returncode != 0
        assert payload["verdict"] == "block"
        axis = "static-analysis" if defect == "lint-error" else "behavior"
        assert f"quality_obligation_unproven:{axis}" in payload["required_gaps"]
    if defect != "missing-lock":
        assert (repo / "uv.lock").read_bytes() == (fixture / "uv.lock").read_bytes()
    assert payload["summary"]["proof_attestation_issued"] is False


@pytest.mark.parametrize("evidence_case", ["missing", "complete"])
def test_one_gate_can_supply_both_code_axes(tmp_path: Path, evidence_case: str) -> None:
    """One native gate may supply both axes; a missing axis remains blocked."""
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    providers = ["ethos.adapters.gates.python_quality:behavior_report"]
    if evidence_case == "complete":
        providers.append("ethos.adapters.gates.python_quality:static_report")
    profile = (
        'profile_id = "combined-quality"\n\n[openspec]\nmaterial_paths = ["**"]\n\n'
        '[proof]\ncode_correctness_gates = ["quality"]\n\n'
        '[proof.code_correctness_map]\nbehavior = "quality"\n'
        'static-analysis = "quality"\n\n'
        '[[proof.gates]]\nid = "quality"\nkind = "test"\n'
        f"providers = {json.dumps(providers)}\n\n"
        '[[proof.gates]]\nid = "optional"\nkind = "lint"\n'
        f"command = {json.dumps([sys.executable, '-c', 'print("optional executed")'])}\n"
    )
    repo = committed_source_repo(
        tmp_path,
        {
            ".gitignore": ".venv/\n__pycache__/\n",
            ".ethos/profile.toml": profile,
            "pyproject.toml": (fixture / "pyproject.toml").read_text(),
            "uv.lock": (fixture / "uv.lock").read_text(),
            "src/sample/__init__.py": "def answer() -> int:\n    return 42\n",
            "tests/test_sample.py": (
                "from sample import answer\n\n\ndef test_answer() -> None:\n"
                "    assert answer() == 42\n"
            ),
        },
    )
    head = git(repo, "rev-parse", "HEAD")
    result = run_quality_proof(repo, head)
    payload = json.loads(result.stdout)
    if evidence_case == "complete":
        assert result.returncode == 0, payload["required_gaps"]
        assert payload["verdict"] == "pass"
        checks = {check["action_id"]: check for check in payload["data"]["checks"]}
        providers = json.loads(checks["quality"]["stdout"])["providers"]
        assert {item["report"]["quality_evidence"]["axis"] for item in providers} == {
            "behavior",
            "static-analysis",
        }
        assert all(check["verdict"] == "pass" for check in checks.values())
        selected = run_ethos_raw(
            "prove",
            "--host",
            "--execute",
            "--gate",
            "quality",
            "--gate",
            "optional",
            "--expect-head",
            head,
            "--json",
            cwd=repo,
        )
        explicit = json.loads(selected.stdout)
        assert selected.returncode == 0, explicit["required_gaps"]
        checks = {check["action_id"]: check for check in explicit["data"]["checks"]}
        assert set(checks) == {"quality", "optional"}
        assert checks["optional"]["stdout"].strip() == "optional executed"
    else:
        assert result.returncode != 0
        assert "quality_gate_verifier_missing:static-analysis:quality" in payload["required_gaps"]
        assert payload["data"]["checks"] == []
