"""Use standard native reports from a repository command without replaying its effects."""

from __future__ import annotations

import json
import shutil
import sys
from typing import TYPE_CHECKING

import pytest

from ethos.adapters.gates.runner import LocalGateRunner
from ethos.adapters.process import run_command
from ethos.contracts.gates import Gate
from ethos.contracts.plan import PlanNode
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import committed_source_repo

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("fault", ["none", "failed", "source-changed"])
def test_declared_native_reports_preserve_one_real_go_attempt(tmp_path: Path, fault: str) -> None:
    """The selected native producer runs once with bound output and unchanged inputs."""
    go = shutil.which("go")
    if go is None:
        pytest.skip("native Go is unavailable")
    body = 't.Fatal("native failure identity")' if fault == "failed" else "Answer()"
    if fault == "source-changed":
        body += ';os.WriteFile("package.json",[]byte("{}"),0600)'
    root = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module fixture.invalid/reports\n\ngo 1.26\n",
            "answer.go": "package reports\nfunc Answer() int { return 42 }\n",
            "answer_test.go": (
                'package reports\nimport("os";"testing")\nfunc TestAnswer(t *testing.T){\n'
                'f,e:=os.OpenFile("attempt-count",os.O_CREATE|os.O_APPEND|os.O_WRONLY,0600)\n'
                'if e!=nil{t.Fatal(e)};f.WriteString("x");f.Close()\n' + body + "\n}\n"
            ),
            "package.json": '{"devEngines":{"packageManager":{"name":"npm","version":"12.1.0"}}}\n',
        },
    )
    gate = Gate.model_validate(
        {
            "id": "native-reports",
            "kind": "test",
            "command": (
                go,
                "test",
                "-json",
                "-count=1",
                "-coverpkg=./...",
                "-coverprofile={reports}/coverage.out",
                "./...",
            ),
            "verification_providers": ("ethos.adapters.gates.code_quality:behavior_report",),
            "source_inputs": ("go.mod", "package.json"),
            "native_reports": (
                {"format": "go-test-json", "channel": "stdout"},
                {"format": "go-coverage", "channel": "file", "path": "coverage.out"},
            ),
        }
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))

    result = LocalGateRunner().run(node, gate, root=root)

    assert result.verdict == ("pass" if fault == "none" else "block"), result.diagnostics
    assert (root / "attempt-count").read_text() == "x"
    assert result.verification is not None
    if fault == "failed":
        assert "TestAnswer" in json.dumps(result.diagnostics)


@pytest.mark.parametrize("origin", ["invented", "replayed"])
def test_native_report_format_cannot_authorize_an_opaque_producer(
    tmp_path: Path, origin: str
) -> None:
    """Valid report bytes do not prove a new native test attempt happened."""
    root = committed_source_repo(
        tmp_path,
        {
            "go.mod": "module fixture.invalid/reports\n\ngo 1.26\n",
            "answer.go": "package reports\nfunc Answer() int { return 42 }\n",
            "answer_test.go": (
                'package reports\nimport "testing"\n'
                'func TestAnswer(t *testing.T) { if Answer() != 42 { t.Fatal("wrong") } }\n'
            ),
        },
    )
    events = '{"Action":"pass","Package":"fixture.invalid/reports","Test":"TestAnswer"}\n'
    coverage = "mode: set\nfixture.invalid/reports/answer.go:2.19,2.32 1 1\n"
    if origin == "replayed":
        go = shutil.which("go")
        if go is None:
            pytest.skip("native Go is unavailable")
        previous = tmp_path / "previous-coverage.out"
        attempt = run_command(
            root,
            (
                go,
                "test",
                "-json",
                "-count=1",
                "-coverpkg=./...",
                f"-coverprofile={previous}",
                "./...",
            ),
            timeout=60,
        )
        assert attempt.returncode == 0, attempt.stderr
        events, coverage = attempt.stdout, previous.read_text()
    script = (
        "import sys\nfrom pathlib import Path\n"
        "Path('opaque-producer-started').write_text('x')\n"
        f"Path(sys.argv[1]).write_text({coverage!r})\n"
        f"sys.stdout.write({events!r})\n"
    )
    gate = Gate.model_validate(
        {
            "id": "opaque-reports",
            "kind": "test",
            "command": (sys.executable, "-c", script, "{reports}/coverage.out"),
            "verification_providers": ("ethos.adapters.gates.code_quality:behavior_report",),
            "source_inputs": ("go.mod",),
            "native_reports": (
                {"format": "go-test-json", "channel": "stdout"},
                {"format": "go-coverage", "channel": "file", "path": "coverage.out"},
            ),
        }
    )
    node = PlanNode(id=gate.id, kind="check", command=gate_execution_identity(gate))

    result = LocalGateRunner().run(node, gate, root=root)

    assert result.verdict == "block", result.verification
    assert not (root / "opaque-producer-started").exists()
    assert "go_native_command_unsupported" in json.dumps(result.diagnostics)
