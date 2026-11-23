"""Hosted focused-gate execution without Work Lane mutation authority."""

from __future__ import annotations

import json
import sys
from functools import partial
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from ethos.repository.policy.gates import ResolvedGatePolicy

import dataclasses

import ethos.adapters.gates.child_environment as child_environment
import ethos.adapters.gates.host_admission as host_admission
import ethos.application.proof.host as gate_execution
import ethos.application.proof.operation as proof_operation
from ethos.adapters.gates.runner import ActionRunResult
from ethos.adapters.gates.runner import readiness_tier
from ethos.adapters.repo.gate_policy import resolve_gate_policy
from ethos.application.docs_registry import DOCS_REGISTRY_PROVIDER
from ethos.contracts.gates import Gate
from ethos.result import EthosResult
from tests.support.clock import ReleasingClock
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_script_gate_policy


def _host(root: Path, head: str, *selection: str):
    """Exercise the public host protocol with one exact source identity."""
    return run_ethos_raw(
        "prove", "--host", "--execute", *selection, "--expect-head", head, "--json", cwd=root
    )


@pytest.mark.parametrize("verdict", ["pass", "block"])
def test_host_focused_gate_executes_without_lease_or_proof_attestation(
    monkeypatch, tmp_path: Path, verdict: str
) -> None:
    """Hosted quality checks share gate owners without minting repository proof."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    # The gate resolves the provider `system/gates.toml` names, so the fake replaces exactly that.
    monkeypatch.setattr(
        DOCS_REGISTRY_PROVIDER.replace(":", "."),
        lambda _root: {
            "verdict": verdict,
            "state": "clean" if verdict == "pass" else "failed",
            "required_gaps": [] if verdict == "pass" else ["quality_gate_failed:docs-registry"],
            "stderr": "exact-provider-error" if verdict == "block" else "",
        },
    )
    unread = Mock(side_effect=ValueError("locked_toolchain_missing"))
    monkeypatch.setattr(child_environment, "repository_mise_files", unread)

    completed = _host(repo, head, "--gate", "docs-registry")

    assert completed.returncode == (0 if verdict == "pass" else 1), completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["verdict"] == verdict
    assert payload["state"] == ("observed" if verdict == "pass" else "gapped")
    summary = dict(payload["summary"])
    assert summary.pop("runtime")["source_commit"]
    # A lock that cannot be read is a state of the report; the verdict stays the provider's own.
    environment = summary.pop("environment")
    assert environment["locked_toolchain"] == "unread:locked_toolchain_missing"
    # An unread lock names no tool, and the member holds its seven declared names and no other.
    assert (environment["mode"], environment["outside_lock"]) == ("inherited", [])
    names = "mode names outside_allow_list credential_classes locked_toolchain outside_lock"
    assert set(environment) == {*names.split(), "git_overlay_keys"}
    assert summary == {"boundary": "host", "gate_count": 1, "proof_attestation_issued": False}
    assert payload["data"]["host_probe"]["satisfies_repository_proof"] is False
    assert payload["data"]["checks"][0]["action_id"] == "docs-registry"
    assert not payload["data"]["checks"][0]["supplier"]
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
    """Missing source and absent quality verification both block before execution."""
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
    assert report["data"]["checks"] == []
    assert report["data"]["executed"] is False
    assert "environment" not in report["summary"]
    if missing:
        assert report["required_gaps"] == ["gate_policy_source_missing:check:tools/check.sh"]
    else:
        assert report["required_gaps"] == [
            "quality_obligation_unproven:behavior",
            "quality_obligation_unproven:static-analysis",
        ]
    assert git(repo, "status", "--short") == before


def test_host_document_diagnostic_does_not_require_unselected_code_proof(tmp_path: Path) -> None:
    """A real shared document provider executes independently of the native code floor."""
    repo = init_git_repo(tmp_path / "repo")
    write_script_gate_policy(repo, full=True)
    (repo / "tools/check.sh").chmod(0o700)
    head = commit_fixture(repo, "declare separate code and document obligations")
    before = git(repo, "status", "--short")

    completed = _host(repo, head, "--gate", "docs-registry")

    payload = json.loads(completed.stdout)
    assert completed.returncode == 0, payload
    assert payload["verdict"] == "pass"
    assert payload["required_gaps"] == []
    assert payload["data"]["executed"] is True
    assert [check["action_id"] for check in payload["data"]["checks"]] == ["docs-registry"]
    assert payload["data"]["host_probe"]["satisfies_repository_proof"] is False
    assert payload["data"]["attestation"] == {}
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


@pytest.mark.parametrize("verdict", ["block", "unknown"])
def test_an_executing_full_host_proof_exits_one_unless_it_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, verdict: str
) -> None:
    """Adopter CI gates on this exit, so a blocked or unknown full host proof never exits 0."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    observed = EthosResult(
        command="prove",
        verdict=verdict,
        state="observed",
        required_gaps=("gate_failed:docs-registry",),
    )
    monkeypatch.setattr(proof_operation, "host_gate_observation", lambda **_kwargs: observed)

    completed = _host(repo, head, "--full")

    assert (completed.returncode, json.loads(completed.stdout)["verdict"]) == (1, verdict)


def _policy_with_a_test_gate(repo: Path, head: str) -> object:
    """Return the default full policy plus one test gate, so a host proof has a tier to admit."""
    resolved = resolve_gate_policy(repo, tree_ref=head, full=True)
    gates = (*resolved.gates, Gate(id="check", kind="test", command=("tools/check.sh",)))
    return dataclasses.replace(resolved, gates=gates)


def _entries(repo: Path) -> list[dict[str, object]]:
    """Return the host queue's live entries as a reader in `repo` sees them."""
    return host_admission.host_queue()[0].entries(reader=repo)


def _passing_graph(monkeypatch, policy: ResolvedGatePolicy | None = None, observe=len) -> list:
    """Pass every node of each graph run under `policy`; return what `observe` saw of each run."""
    seen: list = []

    def run(_runner, nodes, _registry, **_kwargs):
        seen.append(observe(nodes))
        return tuple(ActionRunResult(node.id, node.command, "pass", 0) for node in nodes)

    monkeypatch.setattr(gate_execution, "run_gate_graph", run)
    if policy is not None:
        monkeypatch.setattr(gate_execution, "resolve_gate_policy", lambda *_a, **_k: policy)
    return seen


def _identities(nodes) -> tuple[str, ...]:
    return tuple(node.id for node in nodes)


def test_a_host_proof_holds_the_ticket_for_its_test_and_package_gates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The readiness tier runs without waiting; the test and package gates run under one ticket."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    policy = _policy_with_a_test_gate(repo, head)
    seen = _passing_graph(monkeypatch, policy, lambda nodes: (_identities(nodes), _entries(repo)))

    completed = _host(repo, head, "--full")

    # The first graph run is the readiness tier, which holds no ticket; the second runs every gate
    # with the tier settled, under the ticket.
    assert seen[0] == (readiness_tier(policy.nodes, policy.registry), [])
    assert seen[1][0] == _identities(policy.nodes)
    (entry,) = seen[1][1]
    assert (entry["state"], entry["operation"]) == ("holding", "proof.host")
    assert entry["owner"] == "agent:test:case:agent-test"
    assert entry["same_repository"] is True
    payload = json.loads(completed.stdout)
    assert payload["data"]["admission"] == {"waited_seconds": 0.0, "joined": False}
    assert not any(gap.startswith("host_admission") for gap in payload["required_gaps"])
    assert not _entries(repo)


def test_a_readiness_only_host_plan_takes_no_ticket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A plan of readiness gates alone passes as a short unit, without waiting for the host."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    # The default full policy is all readiness gates, so this plan never waits.
    seen = _passing_graph(monkeypatch, observe=lambda _nodes: _entries(repo))

    completed = _host(repo, head, "--full")

    assert seen == [[]]
    payload = json.loads(completed.stdout)
    assert "admission" not in payload["data"]
    assert completed.returncode == 0, completed.stderr


def test_a_host_proof_under_a_live_admission_takes_no_second_ticket(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A host gate inside an admitted full proof joins that admission instead of queueing."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    _passing_graph(monkeypatch, _policy_with_a_test_gate(repo, head))

    with host_admission.admitted_host_work(
        repo, "ethos prove", operation="proof.run", seconds=0
    ) as live:
        issued = _entries(repo)
        with host_admission.exported(live.environment):
            observed = gate_execution.observe_gate_execution(repo, full=True)
            # The outer admission's own ticket still stands; no second one was taken.
            (outer_entry,) = _entries(repo)

    assert (outer_entry["state"], outer_entry["operation"]) == ("holding", "proof.run")
    assert len(issued) == 1
    assert observed["admission"] == {"waited_seconds": 0.0, "joined": True}
    assert _entries(repo) == []


def test_a_host_proof_keeps_its_place_behind_a_live_holder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A holder that outlasts the repository's admission bound ends no host proof's wait."""
    repo = init_git_repo(tmp_path / "repo")
    _passing_graph(monkeypatch, _policy_with_a_test_gate(repo, git(repo, "rev-parse", "HEAD")))
    queue = host_admission.host_queue()[0]
    held = queue.enter(init_git_repo(tmp_path / "busy"), "renderer", operation="host.run")
    clock = ReleasingClock(6400, lambda: queue.leave(held))
    timed = partial(gate_execution.admitted_host_work, clock=lambda: clock.now, sleep=clock.sleep)
    monkeypatch.setattr(host_admission, "_POLL_SECONDS", 400.0)
    monkeypatch.setattr(gate_execution, "admitted_host_work", timed)

    observed = gate_execution.observe_gate_execution(repo, full=True)

    assert (observed["verdict"], observed["required_gaps"]) == ("pass", [])
    assert observed["admission"] == {"waited_seconds": 6400.0, "joined": False}


def test_a_contended_host_proof_blocks_with_no_path_of_the_holder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bounded wait runs no gate, exits 1, and names the holder without its path."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    policy = _policy_with_a_test_gate(repo, head)
    busy = init_git_repo(tmp_path / "busy")
    queue = host_admission.host_queue()[0]
    holder = queue.enter(busy, "renderer", operation="host.run", owner="agent:test:h")
    seen = _passing_graph(monkeypatch, policy, _identities)
    monkeypatch.setattr(gate_execution, "admitted_host_work", _bounded(gate_execution, 0.0))

    completed = _host(repo, head, "--full")

    payload = json.loads(completed.stdout)
    assert (completed.returncode, payload["verdict"]) == (1, "block")
    # Readiness ran; no test or package gate did.
    assert seen == [readiness_tier(policy.nodes, policy.registry)]
    contended = (
        f"host_admission_contended:host.run:{holder.name.split('-')[1]}:{_since(queue, holder)}"
    )
    assert payload["required_gaps"] == [contended]
    assert str(tmp_path) not in completed.stdout
    # The refusal keeps the readiness results that ran and names the gate that did not run.
    assert tuple(check["action_id"] for check in payload["data"]["checks"]) == seen[0]
    assert (payload["data"]["executed"], payload["data"]["not_run"]) == (True, ["check"])
    assert payload["summary"]["gate_count"] == len(seen[0])
    queue.leave(holder)


@pytest.mark.parametrize(
    ("absolute", "gap"),
    [(False, "host_root_unavailable"), (True, "host_admission_unavailable")],
)
def test_a_host_proof_without_a_usable_host_root_keeps_its_readiness_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, absolute: bool, gap: str
) -> None:
    """A relative data home or an unwritable queue blocks by name; the readiness results stay."""
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    policy = _policy_with_a_test_gate(repo, head)
    root = tmp_path / "blocked-data/ethos"
    if absolute:
        # A file where the queue's directory belongs: the ticket cannot be written.
        root.mkdir(parents=True)
        (root / "host-admission").write_text("", encoding="utf-8")
    # The host root follows the data home, as it does for every test of this suite.
    monkeypatch.setenv("XDG_DATA_HOME", str(root.parent) if absolute else "relative-data")
    seen = _passing_graph(monkeypatch, policy, _identities)

    completed = _host(repo, head, "--full")

    payload = json.loads(completed.stdout)
    assert (completed.returncode, payload["required_gaps"]) == (1, [gap])
    assert tuple(check["action_id"] for check in payload["data"]["checks"]) == seen[0]
    assert (payload["data"]["executed"], payload["data"]["not_run"]) == (True, ["check"])


def _bounded(module, seconds: float):
    """Return the real admission with its bound replaced, so a contended wait ends at once."""
    original = module.admitted_host_work

    def admit(*args, **kwargs):
        return original(*args, **{**kwargs, "seconds": seconds, "sleep": lambda _seconds: None})

    return admit


def _since(queue, ticket) -> str:
    """Return one ticket's recorded start time."""
    recorded = json.loads((queue.directory / f"{ticket.name}.json").read_text(encoding="utf-8"))
    return str(recorded["since"])
