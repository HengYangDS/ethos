"""The hosted shell transport cannot turn stale or partial output into proof."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ROOT = Path(__file__).resolve().parents[3]


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
def test_hosted_receipt_requires_exact_executed_observation(tmp_path: Path, fault: str) -> None:
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
    result_file = tmp_path / "result.json"
    result_file.write_text("{" if fault == "malformed" else json.dumps(payload))
    command_log = tmp_path / "commands.jsonl"
    binary = tmp_path / "bin/uv"
    binary.parent.mkdir()
    binary.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys\n"
        f"with pathlib.Path({str(command_log)!r}).open('a') as stream:\n"
        " stream.write(json.dumps(sys.argv[1:])+'\\n')\n"
        "if sys.argv[1:6] != ['run', '--frozen', '--offline', 'ethos', 'prove']:\n"
        " print('unexpected lifecycle transport', file=sys.stderr); sys.exit(9)\n"
        f"print(pathlib.Path({str(result_file)!r}).read_text())\n"
        "print('exact-child-diagnostic', file=sys.stderr)\n"
        f"sys.exit({7 if fault == 'process' else 0})\n"
    )
    binary.chmod(0o755)
    (binary.parent / "python3").symlink_to(sys.executable)
    completed = subprocess.run(
        ["bash", str(ROOT / "tools/ci/scripts/run-head-bound-proof.sh"), expected],
        cwd=repo,
        env=os.environ
        | {
            "PATH": f"{binary.parent}{os.pathsep}{os.environ['PATH']}",
            "ETHOS_RUNTIME_BOOTSTRAPPED": "1",
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
