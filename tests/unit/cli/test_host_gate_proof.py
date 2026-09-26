"""Hosted focused-gate execution without Work Lane mutation authority."""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

import ethos.adapters.gates.runner as gate_execution
import ethos.adapters.gates.ty as ty_gate
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_script_gate_policy


def _host(root: Path, head: str, *selection: str):
    """Exercise the public host protocol with one exact source identity."""
    return run_ethos_raw(
        "prove",
        "--host",
        "--execute",
        *selection,
        "--expect-head",
        head,
        "--json",
        cwd=root,
    )


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

    completed = _host(repo, head, "--gate", "python-types")

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
    assert payload["data"]["checks"][0]["duration_seconds"] >= 0
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
    runtime = repo / ".venv/bin/python"
    runtime.parent.mkdir(parents=True)
    runtime.symlink_to(sys.executable)
    (repo / ".gitignore").write_text(".venv/\n")
    head = commit_fixture(repo, "declare isolated runtime")
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

    monkeypatch.setattr(gate_execution, "run_gate_graph", run)
    completed = _host(repo, head, *(("--full",) if full else ()))

    policy = resolve_gate_policy(repo, tree_ref=head, full=full)
    assert observed == [node.id for node in policy.nodes]
    assert observed
    payload = json.loads(completed.stdout)
    complete = missing in {"none", "reordered"}
    assert payload["verdict"] == ("pass" if complete else "block")
    expected_gaps = {
        "none": [],
        "reordered": [],
        "empty": ["gate_results_empty", *(f"gate_missing:{name}" for name in sorted(observed))],
        "partial": [f"gate_missing:{name}" for name in sorted(observed[1:])],
        "duplicate": [f"gate_missing:{observed[-1]}", f"gate_duplicate:{observed[0]}"],
    }
    assert payload["required_gaps"] == expected_gaps[missing]


@pytest.mark.parametrize("missing", [False, True])
def test_host_admission_requires_committed_executable_source(tmp_path: Path, *, missing: bool):
    """Committed execution and repository code-quality proof remain distinct."""
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo, full=True)
    script = repo / "tools/check.sh"
    script.write_text("#!/bin/sh\nprintf 'executed native check\\n'\n")
    script.chmod(0o700)
    body = script.read_bytes()
    if missing:
        script.unlink()
    head = commit_fixture(repo, "source obligation")
    if missing:
        script.write_bytes(body)
        script.chmod(0o700)
    before = git(repo, "status", "--short")
    result = _host(repo, head, "--gate", "check")
    report = json.loads(result.stdout)
    assert (report["verdict"], result.returncode) == ("block", 1)
    assert bool(report["data"]["checks"]) is not missing
    if missing:
        assert report["required_gaps"] == ["gate_policy_source_missing:check:tools/check.sh"]
    else:
        assert report["required_gaps"] == [
            "quality_obligation_unproven:behavior",
            "quality_obligation_unproven:static-analysis",
        ]
        assert report["data"]["checks"][0]["stdout"] == "executed native check\n"
    assert git(repo, "status", "--short") == before


@pytest.mark.parametrize("full", [False, True])
def test_host_invalid_policy_is_a_reported_nonexecution(tmp_path: Path, *, full: bool) -> None:
    """Malformed committed policy blocks without a traceback or executing checks."""
    root = init_git_repo(tmp_path / "repo")
    policy = root / ".ethos/profile.toml"
    policy.parent.mkdir(exist_ok=True)
    policy.write_text("not valid [")
    head = commit_fixture(root, "invalid policy")
    result = _host(root, head, *(("--full",) if full else ()))
    payload = json.loads(result.stdout)
    assert result.returncode != 0
    assert payload["verdict"] == "block"
    assert payload["required_gaps"] == ["repository_profile_invalid:.ethos/profile.toml"]
    assert payload["data"]["checks"] == []
    assert payload["data"]["executed"] is False
