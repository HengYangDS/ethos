"""Qualify one native Go attempt without a verifier replay or lost failures."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("fault", ["none", "failure", "unexecuted", "opaque"])
def test_verified_go_command_has_one_effect_owner(tmp_path: Path, fault: str) -> None:
    """The declared native test is the sole attempt; opaque commands stop before effects."""
    executable = shutil.which("go")
    if executable is None:
        pytest.skip("native Go is unavailable")
    test_body = 'if Answer() != 42 { t.Fatal("wrong answer") }'
    if fault == "failure":
        test_body = 't.Fatal("distinguishable native failure")'
    elif fault == "unexecuted":
        test_body = 't.Skip("no execution evidence")'
    root = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module example.invalid/quality\n\ngo 1.20\n",
            "answer.go": "package quality\n\nfunc Answer() int { return 42 }\n",
            "answer_test.go": (
                'package quality\n\nimport ("os"; "testing")\n\n'
                "func TestAnswer(t *testing.T) {\n"
                'f, err := os.OpenFile("attempt-count", os.O_CREATE|os.O_WRONLY|os.O_APPEND,\n'
                "0600)\nif err != nil { t.Fatal(err) }\n"
                'if _, err := f.WriteString("x"); err != nil { t.Fatal(err) }; f.Close()\n'
                + test_body
                + "\n}\n"
            ),
        },
    )
    command = (executable, "test", "-count=1", "./...")
    if fault == "opaque":
        command = (executable, "version")
    gate = Gate(
        id="go-tests",
        kind="test",
        command=command,
        verification_providers=("ethos.adapters.gates.code_quality:behavior_report",),
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))

    result = LocalGateRunner().run(node, gate, root=root)

    assert result.verdict == ("pass" if fault == "none" else "block"), result.diagnostics
    if fault == "opaque":
        assert result.exit_code is None
        assert not (root / "attempt-count").exists()
    else:
        assert (root / "attempt-count").read_text() == "x"
    if fault == "failure":
        assert "distinguishable native failure" in result.stdout
        assert any("TestAnswer" in str(diagnostic) for diagnostic in result.diagnostics), (
            result.diagnostics
        )


def test_public_adopter_proof_reports_native_go_test_failure(tmp_path: Path) -> None:
    """The public gate keeps a failing Go test's command and native output."""
    if shutil.which("go") is None:
        pytest.skip("go is unavailable on this runner")
    repo = init_git_repo(tmp_path / "adopter")
    behavior = Gate(
        id="behavior", kind="test", providers=("ethos.adapters.gates.code_quality:behavior_report",)
    )
    static = Gate(
        id="static", kind="static", providers=("ethos.adapters.gates.code_quality:static_report",)
    )
    write_test_profile(
        repo,
        proof={
            "code_correctness_gates": ("behavior", "static"),
            "code_correctness_map": {"behavior": "behavior", "static-analysis": "static"},
            "gates": (behavior, static),
        },
    )
    (repo / "go.mod").write_text("module example.invalid/quality\n\ngo 1.20\n")
    (repo / "answer.go").write_text("package quality\nfunc Answer() int { return 41 }\n")
    (repo / "answer_test.go").write_text(
        'package quality\nimport "testing"\n'
        'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong answer") } }\n'
        "func TestLaterOutput(t *testing.T) { for i := 0; i < 128; i++ { "
        't.Log("unrelated output after the failed test") } }\n'
    )
    subprocess.run(["gofmt", "-w", "answer.go", "answer_test.go"], cwd=repo, check=True)
    head = commit_fixture(repo, "bind failing native Go test")

    completed = run_ethos_raw(
        "prove",
        "--host",
        "--execute",
        "--full",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
        subprocess_only=True,
    )
    payload = json.loads(completed.stdout)
    checks = {check["action_id"]: check for check in payload["data"]["checks"]}
    report = json.loads(checks["behavior"]["stdout"])["providers"][0]["report"]

    assert completed.returncode != 0
    assert payload["verdict"] == "block"
    assert report["required_gaps"] == ["quality_behavior_go_tests_failed"]
    failure = report["diagnostics"][0]
    assert failure["code"] == "go_tests_failed"
    assert failure["observation"]["exit_code"] != 0
    assert "wrong answer" not in failure["observation"]["stdout_tail"]
    assert failure["observation"]["go_test_report_valid"] is True
    assert {"package": "example.invalid/quality", "test": "TestAnswer"} in failure["observation"][
        "go_test_failures"
    ]
