"""The hosted shell transport cannot turn stale or partial output into proof."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


def _report_source(repo: Path, reports: str) -> str:
    """Have the child produce report artifacts after the wrapper removes stale files."""
    return (
        ""
        if reports == "missing"
        else "".join(
            f"p=pathlib.Path({str(repo / 'build/evidence/quality/tests' / relative)!r});"
            "p.parent.mkdir(parents=True,exist_ok=True);"
            f"p.write_text({('{' if reports == 'malformed' else content)!r})\n"
            for relative, content in {
                "pytest/junit.xml": (
                    "<testsuite><testcase/><testcase><failure/></testcase></testsuite>"
                ),
                "coverage/coverage.xml": (
                    '<coverage lines-covered="96" lines-valid="100" '
                    'branches-covered="95" branches-valid="100"/>'
                ),
            }.items()
        )
    )


def _hosted_scripts(repo: Path, supply_script: str, scanner_script: str = "exit 0\n") -> Path:
    """Keep the real wrapper with isolated external-tool preparation boundaries."""
    scripts = repo / "tools/ci/scripts"
    scripts.mkdir(parents=True)
    shutil.copy2(ROOT / "tools/ci/scripts/run-head-bound-proof.sh", scripts)
    supply = repo / "tools/ci/toolchain/native.py"
    supply.parent.mkdir()
    supply.write_text(
        "import subprocess, sys\n"
        "assert sys.argv[1:3] == ['--root', str(__import__('pathlib').Path.cwd())]\n"
        "assert sys.argv[3:] == ['gitleaks', 'scc']\n"
        f"for body in ({scanner_script!r}, {supply_script!r}):\n"
        " result = subprocess.run(['/bin/sh', '-c', body])\n"
        " if result.returncode: sys.exit(result.returncode)\n"
    )
    return scripts


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "process",
        "gap",
        "head",
        "checkout",
        "malformed",
        "empty",
        "gate",
        "plane",
        "unexecuted",
    ],
)
@pytest.mark.parametrize("reports", ["missing", "malformed", "valid"])
def test_hosted_receipt_requires_exact_executed_observation(
    tmp_path: Path, fault: str, reports: str
) -> None:
    """No local lane readiness or misleading passing field can authorize CI success."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    expected = "0" * 40 if fault == "checkout" else head
    coordinates = {"expected": expected, "current": expected, "matches": True}
    checks = [
        {"action_id": gate, "verdict": "pass", "exit_code": 0}
        for gate in ("unit-architecture", "coverage-floor", "openspec")
    ]
    payload = {
        "verdict": "pass",
        "state": "observed",
        "required_gaps": [],
        "summary": {"boundary": "host", "gate_count": 3, "proof_attestation_issued": False},
        "data": {
            "executed": True,
            "boundary": "host",
            "attestation": {},
            "expected_head": coordinates,
            "checks": checks,
        },
    }
    data = payload["data"]
    if fault == "gap":
        payload["required_gaps"] = ["gate_failed:coverage-floor"]
    elif fault == "head":
        coordinates["current"] = "1" * 40
    elif fault == "empty":
        data["checks"] = []
    elif fault == "gate":
        checks[0]["verdict"] = "block"
    elif fault == "plane":
        data["boundary"] = "repository"
        data["attestation"] = {"id": "unrelated-proof"}
    elif fault == "unexecuted":
        data["executed"] = False
    output = "{" if fault == "malformed" else json.dumps(payload)
    command_log = tmp_path / "commands.jsonl"
    binary = tmp_path / "bin/uv"
    binary.parent.mkdir()
    scanner = binary.parent / "gitleaks"
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, subprocess, sys\n"
        f"scanner = subprocess.check_output([{str(scanner)!r}, 'version'], text=True)\n"
        "assert scanner.strip() == 'fixture-scanner'\n"
        f"with pathlib.Path({str(command_log)!r}).open('a') as stream:\n"
        " stream.write(json.dumps(sys.argv[1:])+'\\n')\n"
        "if sys.argv[1:6] != ['run', '--frozen', '--offline', 'ethos', 'prove']:\n"
        " print('unexpected lifecycle transport', file=sys.stderr); sys.exit(9)\n"
        + _report_source(repo, reports)
        + f"print({output!r})\n"
        "print('exact-child-diagnostic', file=sys.stderr)\n"
        f"sys.exit({7 if fault == 'process' else 0})\n"
    )
    binary.chmod(0o755)
    for name in ("python", "python3"):
        (binary.parent / name).symlink_to(sys.executable)
    scripts = _hosted_scripts(
        repo,
        f"printf '%s\\n' '{binary.parent}'\n",
        f"printf '#!/bin/sh\\nprintf fixture-scanner\\n' > '{scanner}'\nchmod +x '{scanner}'\n",
    )
    summary_file = tmp_path / "summary.md"
    completed = subprocess.run(
        ["bash", str(scripts / "run-head-bound-proof.sh"), expected],
        cwd=repo,
        env=os.environ
        | {
            "PATH": f"{binary.parent}{os.pathsep}{os.environ['PATH']}",
            "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
            "GITHUB_STEP_SUMMARY": str(summary_file),
        },
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert (completed.returncode == 0) is (fault == "none"), completed.stdout + completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["kind"] == "ethos_hosted_verification_receipt"
    assert receipt["satisfies_repository_proof"] is False
    assert receipt["verdict"] == ("pass" if fault == "none" else "block")
    commands = [json.loads(line) for line in command_log.read_text().splitlines()]
    assert len(commands) == 1
    command = commands[0]
    assert {"--host", "--execute"} <= set(command)
    assert "--gate" not in command
    assert command[command.index("--expect-head") + 1] == expected
    if fault != "none":
        assert "exact-child-diagnostic" in completed.stderr
    summary = summary_file.read_text()
    assert expected in summary
    assert receipt["verdict"] in summary
    assert (
        "Tests: 2; failures: 1; errors: 0; skipped: 0"
        if reports == "valid"
        else "Tests: unavailable"
    ) in summary
    assert ("Coverage: 95.50%" if reports == "valid" else "Coverage: unavailable") in summary


@pytest.mark.parametrize("failed_tool", ["scc", "gitleaks"])
def test_tool_supply_failure_precedes_proof_and_clears_stale_evidence(
    tmp_path: Path, failed_tool: str
) -> None:
    """A failed prerequisite must not leave prior passing output or invoke proof."""
    repo = init_git_repo(tmp_path / "repo")
    failure = f"echo {failed_tool}_archive_checksum_mismatch >&2\nexit 23\n"
    scripts = _hosted_scripts(
        repo,
        failure if failed_tool == "scc" else "exit 0\n",
        failure if failed_tool == "gitleaks" else "exit 0\n",
    )
    evidence = repo / "build/evidence/quality"
    proof = evidence / "proof/executed-proof.json"
    old_test = evidence / "tests/pytest/junit.xml"
    for path in (proof, old_test):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stale passing output")
    bins = tmp_path / "bin"
    bins.mkdir()
    (bins / "python").symlink_to(sys.executable)
    (bins / "python3").symlink_to(sys.executable)
    invoked = tmp_path / "proof-invoked"
    uv = bins / "uv"
    uv.write_text(f"#!/bin/sh\ntouch '{invoked}'\nexit 99\n")
    uv.chmod(0o755)
    result = subprocess.run(
        ["bash", str(scripts / "run-head-bound-proof.sh")],
        cwd=repo,
        env=os.environ
        | {"PATH": f"{bins}{os.pathsep}{os.environ['PATH']}", "ETHOS_RUNTIME_BOOTSTRAPPED": "1"},
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 23, result.stdout + result.stderr
    assert f"{failed_tool}_archive_checksum_mismatch" in result.stderr
    assert not invoked.exists()
    assert not old_test.exists()
    assert not proof.exists() or "stale passing output" not in proof.read_text()
    receipt = json.loads(result.stdout)
    assert receipt["verdict"] == "block"
    retained = json.loads((evidence / "proof/hosted-verification.json").read_text())
    assert retained == receipt
    assert retained["required_gaps"] == ["hosted_tool_supply_failed"]
    assert retained["supply_exit_code"] == 23
