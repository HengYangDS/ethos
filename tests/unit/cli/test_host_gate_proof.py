"""Hosted focused-gate execution without Work Lane mutation authority."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import ethos.adapters.gates.ty as ty_gate
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def test_host_focused_gate_executes_without_lease_or_proof_attestation(
    monkeypatch, tmp_path: Path
) -> None:
    """Hosted quality checks share gate owners without minting repository proof."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(
        ty_gate,
        "ty_gate_report",
        lambda _root: {
            "verdict": "pass",
            "state": "clean",
            "required_gaps": [],
            "packages": {},
        },
    )

    completed = run_ethos_raw(
        "prove",
        "--host",
        "--execute",
        "--gate",
        "python-types",
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["verdict"] == "pass"
    assert payload["state"] == "observed"
    assert payload["summary"] == {
        "boundary": "host",
        "gate_count": 1,
        "proof_attestation_issued": False,
    }
    assert payload["data"]["host_probe"]["satisfies_repository_proof"] is False
    assert payload["data"]["checks"][0]["action_id"] == "python-types"
    assert payload["data"]["attestation"] == {}
    assert not any((repo / ".ethos" / "state").glob("attestations*/**/*.json"))
