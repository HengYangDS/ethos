"""Hosted focused-gate execution without Work Lane mutation authority."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

import ethos.adapters.gates.ty as ty_gate
import ethos.surface.cli.root.proof as proof_command
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize("verdict", ["pass", "block"])
def test_host_focused_gate_executes_without_lease_or_proof_attestation(
    monkeypatch, tmp_path: Path, verdict: str
) -> None:
    """Hosted quality checks share gate owners without minting repository proof."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    monkeypatch.setattr(
        ty_gate,
        "ty_gate_report",
        lambda _root: {
            "verdict": verdict,
            "state": "clean" if verdict == "pass" else "failed",
            "required_gaps": [] if verdict == "pass" else ["type_error"],
            "stderr": "exact-provider-error" if verdict == "block" else "",
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

    assert completed.returncode == (0 if verdict == "pass" else 1), completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["verdict"] == verdict
    assert payload["state"] == ("observed" if verdict == "pass" else "gapped")
    assert payload["summary"] == {
        "boundary": "host",
        "gate_count": 1,
        "proof_attestation_issued": False,
    }
    assert payload["data"]["host_probe"]["satisfies_repository_proof"] is False
    assert payload["data"]["checks"][0]["action_id"] == "python-types"
    if verdict == "block":
        report = json.loads(payload["data"]["checks"][0]["stdout"])
        assert report["providers"][0]["report"]["stderr"] == "exact-provider-error"
    assert payload["data"]["attestation"] == {}
    assert not any((repo / ".ethos" / "state").glob("attestations*/**/*.json"))


@pytest.mark.parametrize("full", [False, True])
@pytest.mark.parametrize("missing", ["none", "empty", "partial", "reordered", "duplicate"])
def test_host_default_selection_preserves_the_declared_gate_floor(
    monkeypatch, tmp_path: Path, *, full: bool, missing: str
) -> None:
    """Changing the evidence plane never silently reduces the declared quality set."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    observed = []

    def run(_runner, nodes, _registry, **_kwargs):
        observed.extend(node.id for node in nodes)
        selected = (
            ()
            if missing == "empty"
            else nodes[:1]
            if missing == "partial"
            else nodes[::-1]
            if missing == "reordered"
            else (*nodes[:-1], nodes[0])
            if missing == "duplicate"
            else nodes
        )
        return tuple(ActionRunResult(node.id, node.command, "pass", 0) for node in selected)

    monkeypatch.setattr(proof_command, "run_gate_waves", run)
    completed = run_ethos_raw(
        "prove",
        "--host",
        "--execute",
        *(("--full",) if full else ()),
        "--expect-head",
        head,
        "--json",
        cwd=repo,
    )

    policy = resolve_gate_policy(repo, tree_ref=head, full=full)
    assert observed == [node.id for node in policy.nodes]
    assert observed
    payload = json.loads(completed.stdout)
    complete = missing in {"none", "reordered"}
    assert payload["verdict"] == ("pass" if complete else "block")
    assert payload["required_gaps"] == ([] if complete else ["host_gate_results_incomplete"])
