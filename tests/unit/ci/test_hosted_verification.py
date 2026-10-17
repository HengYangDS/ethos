"""The hosted receipt owner cannot turn stale or partial output into proof."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

from ethos.contracts.gates import load_gate_registry_declaration
from ethos.repository.policy.gates import gate_execution_identity
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tools.ci import hosted_verification

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="module")
def hosted_proof_transport(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Keep executable code stable while every invocation owns its case data."""
    binary = tmp_path_factory.mktemp("hosted-proof-transport") / "uv"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, subprocess, sys\n"
        "with pathlib.Path('commands.jsonl').open('a') as stream:\n"
        " stream.write(json.dumps(sys.argv[1:])+'\\n')\n"
        "case = json.loads(pathlib.Path('proof-case.json').read_text())\n"
        "assert pathlib.Path('.syft-prepared').is_file()\n"
        "scanner = subprocess.check_output(['gitleaks', 'version'], text=True)\n"
        "assert scanner.strip() == 'fixture-scanner'\n"
        "expected = 'run --frozen --offline python -B -I -m ethos.cli prove'.split()\n"
        "if sys.argv[1:10] != expected:\n"
        " print('unexpected lifecycle transport', file=sys.stderr); sys.exit(9)\n"
        "for name, content in case['reports'].items():\n"
        " path = pathlib.Path('build/evidence/quality/tests') / name\n"
        " path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content)\n"
        "print(case['output'])\n"
        "print('exact-child-diagnostic', file=sys.stderr)\n"
        "sys.exit(case['exit_code'])\n"
    )
    binary.chmod(0o555)
    scanner = binary.parent / "supply" / "gitleaks"
    scanner.parent.mkdir()
    scanner.write_text("#!/bin/sh\nprintf fixture-scanner\n")
    scanner.chmod(0o555)
    supply = binary.with_name("prepare")
    supply.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, subprocess, sys\n"
        "bodies = json.loads(pathlib.Path('supply-case.json').read_text())\n"
        "assert sys.argv[1:] == ['--root', os.getcwd(), '--mise', 'gitleaks', 'scc', 'syft']\n"
        "for body in bodies:\n"
        " result = subprocess.run(['/bin/sh', '-c', body])\n"
        " if result.returncode: sys.exit(result.returncode)\n"
        "print(pathlib.Path(os.path.realpath(__file__)).parent / 'supply')\n"
    )
    supply.chmod(0o555)
    return binary


def _report_contents(reports: str) -> dict[str, str]:
    """Keep per-case report data separate from the shared executable fixture."""
    contents = {
        "pytest/junit.xml": (
            ('<testsuite tests="3">' if reports == "contradictory" else "<testsuite>")
            + ("<testcase><skipped/></testcase>" if reports == "skipped" else "<testcase/>")
            + (
                "<testcase><failure/></testcase>"
                if reports == "failed"
                else "<testcase><skipped/></testcase>"
                if reports == "skipped"
                else "<testcase/>"
            )
            + "</testsuite>"
        ),
        "coverage/coverage.xml": (
            '<coverage lines-covered="96" lines-valid="100" '
            'branches-covered="95" branches-valid="100"/>'
        ),
    }
    return (
        {}
        if reports == "missing"
        else dict.fromkeys(contents, "{")
        if reports == "malformed"
        else contents
    )


def _hosted_supply(
    repo: Path,
    transport: Path,
    supply_script: str,
    scanner_script: str = "exit 0\n",
    sbom_script: str = "touch .syft-prepared\n",
) -> None:
    """Bind the repository runtime and native supply owner to isolated fixtures."""
    interpreter = repo / ".venv/bin/python"
    interpreter.parent.mkdir(parents=True)
    interpreter.symlink_to(sys.executable)
    path = repo / "tools/ci/toolchain/native.py"
    path.parent.mkdir(parents=True)
    path.symlink_to(transport.with_name("prepare"))
    (repo / "supply-case.json").write_text(json.dumps([scanner_script, supply_script, sbom_script]))


def _run_hosted(
    repo: Path,
    bins: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    *args: str,
    **environment: str,
) -> tuple[int, str, str]:
    """Run the receipt owner with explicit case-local tools and environment."""
    for name in [key for key in os.environ if key.startswith("ETHOS_TEST_")]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("PATH", f"{bins}{os.pathsep}{os.environ['PATH']}")
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    status = hosted_verification.run(repo, *args)
    captured = capsys.readouterr()
    return status, captured.out, captured.err


def _observation_payload(expected: str, fault: str) -> dict[str, object]:
    """Build a complete result and corrupt only the boundary under test."""
    coordinates = {"expected": expected, "current": expected, "matches": True}
    checks = [
        {
            "action_id": gate.id,
            "command": list(gate_execution_identity(gate)),
            "verdict": "pass",
            "exit_code": 0,
        }
        for gate in load_gate_registry_declaration(ROOT / "system/gates.toml").proof_gates(
            full=True, python_executable=sys.executable
        )
    ]
    payload = {
        "verdict": "pass",
        "state": "observed",
        "required_gaps": [],
        "summary": {
            "boundary": "host",
            "gate_count": len(checks),
            "proof_attestation_issued": False,
        },
        "data": {
            "executed": True,
            "boundary": "host",
            "attestation": {},
            "expected_head": coordinates,
            "checks": checks,
        },
    }
    data = payload["data"]
    if fault == "head":
        coordinates["current"] = "1" * 40
    elif fault == "gate":
        checks[0]["verdict"] = "block"
    elif fault == "gap":
        payload["required_gaps"] = ["gate_failed:coverage-floor"]
    elif fault == "empty":
        checks.clear()
    elif fault == "partial":
        checks[:] = [
            check
            for check in checks
            if check["action_id"] in {"unit-architecture", "coverage-floor"}
        ]
    elif fault == "duplicate":
        checks.append(checks[0].copy())
    elif fault == "unknown-gate":
        checks.append(checks[0] | {"action_id": "undeclared", "command": []})
    elif fault == "plane":
        data.update(boundary="repository", attestation={"id": "unrelated-proof"})
    elif fault == "unexecuted":
        data["executed"] = False
    payload["summary"]["gate_count"] = len(data["checks"])
    return payload


@pytest.mark.parametrize(
    ("fault", "reports"),
    [
        ("none", report)
        for report in ("missing", "malformed", "contradictory", "failed", "skipped", "valid")
    ]
    + [
        (fault, "valid")
        for fault in (
            "process",
            "gap",
            "head",
            "checkout",
            "malformed",
            "empty",
            "gate",
            "plane",
            "unexecuted",
            "partial",
            "duplicate",
            "unknown-gate",
        )
    ],
)
def test_hosted_receipt_requires_exact_executed_observation(
    tmp_path: Path,
    fault: str,
    reports: str,
    hosted_proof_transport: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """No local lane readiness or misleading passing field can authorize CI success."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    expected = "0" * 40 if fault == "checkout" else head
    payload = _observation_payload(expected, fault)
    binary = tmp_path / "bin/uv"
    binary.parent.mkdir()
    (repo / "proof-case.json").write_text(
        json.dumps(
            {
                "reports": _report_contents(reports),
                "output": "{" if fault == "malformed" else json.dumps(payload),
                "exit_code": 7 if fault == "process" else 0,
            }
        )
    )
    binary.symlink_to(hosted_proof_transport)
    assert binary.samefile(hosted_proof_transport)
    _hosted_supply(repo, hosted_proof_transport, "exit 0\n")
    assert (repo / "tools/ci/toolchain/native.py").samefile(
        hosted_proof_transport.with_name("prepare")
    )
    summary_file = tmp_path / "summary.md"
    if fault == "none" and reports == "valid":
        monkeypatch.setenv("ETHOS_TEST_EVIDENCE_DIR", str(tmp_path / "outer-evidence"))
    status, out, err = _run_hosted(
        repo, binary.parent, monkeypatch, capsys, expected, GITHUB_STEP_SUMMARY=str(summary_file)
    )
    expected_pass = fault == "none" and reports == "valid"
    assert (status == 0) is expected_pass, out + err
    receipt = json.loads(out)
    assert receipt["kind"] == "ethos_hosted_verification_receipt"
    assert receipt["satisfies_repository_proof"] is False
    assert receipt["verdict"] == ("pass" if expected_pass else "block")
    if reports == "contradictory":
        assert receipt["required_gaps"] == ["hosted_test_report_invalid:junit_suite_count_mismatch"]
    (command,) = map(json.loads, (repo / "commands.jsonl").read_text().splitlines())
    assert {"--host", "--execute", "--full"} <= set(command)
    assert "--gate" not in command
    assert command[command.index("--expect-head") + 1] == expected
    if not expected_pass:
        assert "exact-child-diagnostic" in err
    summary = summary_file.read_text()
    assert expected in summary
    assert receipt["verdict"] in summary
    expected_tests = (
        f"Tests: 2; failures: {int(reports == 'failed')}; errors: 0; "
        f"skipped: {2 * int(reports == 'skipped')}"
        if reports in {"valid", "failed", "skipped"}
        else "Tests: unavailable"
    )
    assert expected_tests in summary
    assert (
        "Coverage: 95.50%"
        if reports in {"valid", "failed", "skipped", "contradictory"}
        else "Coverage: unavailable"
    ) in summary


@pytest.mark.parametrize("failed_tool", ["scc", "gitleaks", "syft"])
def test_tool_supply_failure_precedes_proof_and_clears_stale_evidence(
    tmp_path: Path,
    failed_tool: str,
    hosted_proof_transport: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A failed prerequisite must not leave prior passing output or invoke proof."""
    repo = init_git_repo(tmp_path / "repo")
    failure = f"echo {failed_tool}_archive_checksum_mismatch >&2\nexit 23\n"
    _hosted_supply(
        repo,
        hosted_proof_transport,
        *(failure if name == failed_tool else "exit 0\n" for name in ("scc", "gitleaks", "syft")),
    )
    evidence = repo / "build/evidence/quality"
    stale = (
        evidence / "proof/executed-proof.json",
        *(evidence / "tests" / name for name in _report_contents("valid")),
    )
    for path in stale:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale passing output")
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "uv").symlink_to(hosted_proof_transport)
    status, out, err = _run_hosted(repo, bins, monkeypatch, capsys)
    assert status == 23, out + err
    assert f"{failed_tool}_archive_checksum_mismatch" in err
    assert not (repo / "commands.jsonl").exists()
    assert not any(path.exists() for path in stale)
    receipt = json.loads(out)
    assert receipt["verdict"] == "block"
    retained = json.loads((evidence / "proof/hosted-verification.json").read_text())
    assert retained == receipt
    assert retained["required_gaps"] == ["hosted_tool_supply_failed"]
    assert retained["supply_exit_code"] == 23
