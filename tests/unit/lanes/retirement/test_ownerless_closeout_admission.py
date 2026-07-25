from __future__ import annotations

import hashlib
import json
import os
import signal
import sys
import time
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

import ethos.adapters.mutation.resolution.closeout.wcp.core as wcp_adapter
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPCloseoutExpectation
from ethos.adapters.mutation.resolution.closeout.wcp.core import WCPResponseError
from ethos.adapters.mutation.resolution.closeout.wcp.core import run_worktree_closeout_check
from ethos.adapters.mutation.resolution.closeout.wcp.core import validate_worktree_closeout_response

_SCHEMA_VERSION = "workstation.repo-family-governance.v1"
_BRANCH = "work/20260722-ownerless"
_PATH = "/Users/test/projects/ethos-worktrees/20260722-ownerless"
_HEAD = "1" * 40
_ACCEPTED_HEAD = "2" * 40
_ACCEPTED_TREE = "4" * 40
_EXECUTOR = "agent:codex:thread:executor"
_CHRONICLE_REF = "evidence/chronicle/ownerless-closeout/2026-07-22.md"
_CHRONICLE_DIGEST = "3" * 64
_DECISION_ID = "lane-decision:00000000-0000-4000-8000-000000000001"
_LANE_ID = "20260722-ownerless"
_LANE_LAYOUT = "canonical"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _fixture(*, lane_path: str = _PATH) -> tuple[WCPCloseoutExpectation, dict[str, object]]:
    incarnation = 'git-worktree-registration:v1:{"fixture":"wcp"}'
    empty_digest = hashlib.sha256(b"").hexdigest()
    observation = {
        "lane_ref": _BRANCH,
        "head": _HEAD,
        "lane_incarnation_id": incarnation,
        "holder_ref": "",
        "path": lane_path,
        "dirty": False,
        "foreign": True,
        "orphan": True,
        "ambiguous": False,
        "tracked_digest": empty_digest,
        "untracked_digest": empty_digest,
    }
    decision = {
        "schema_version": 1,
        "decision_id": _DECISION_ID,
        "disposition": "retire",
        "observation": observation,
        "observation_digest": _digest(observation),
        "evidence_refs": ["evidence:review"],
        "chronicle_ref": _CHRONICLE_REF,
        "chronicle_digest": _CHRONICLE_DIGEST,
        "recovery_plan": "Retire only after exact preflight and effect-side fencing.",
        "reason": "The clean ownerless lane is an accepted ancestor.",
        "break_glass": True,
        "recompute_before_effect": True,
        "reusable_authorization": False,
        "mints_authority": False,
    }
    decision_bytes = (json.dumps(decision, indent=2, sort_keys=True) + "\n").encode()
    coordination = {
        "lease_state": "missing",
        "claim_binding": "missing",
        "claim_id": "",
    }
    normalized = {
        "branch": _BRANCH,
        "path": lane_path,
        "head": _HEAD,
        "accepted_head": _ACCEPTED_HEAD,
        "worktree_binding": "linked",
        "dirty": False,
        "relation_to_accepted": "ancestor_of_accepted",
        "lease_state": "missing",
        "lease_id": "",
        "holder_ref": "",
        "claim_binding": "missing",
        "claim_id": "",
    }
    coordination["binding_digest"] = _digest(normalized)
    response: dict[str, object] = {
        "ok": True,
        "schema_version": _SCHEMA_VERSION,
        "action": "worktree_closeout_check",
        "admission_mode": "ownerless_decision",
        "lane": {
            "id": _LANE_ID,
            "branch": _BRANCH,
            "path": lane_path,
            "head": _HEAD,
            "layout": _LANE_LAYOUT,
        },
        "decision_id": _DECISION_ID,
        "chronicle_ref": _CHRONICLE_REF,
        "decision_sha256": hashlib.sha256(decision_bytes).hexdigest(),
        "executor_ref": _EXECUTOR,
        "observation_digest": _digest(observation),
        "chronicle_digest": _CHRONICLE_DIGEST,
        "base": "dev",
        "control_branch": "dev",
        "source": {
            "base_branch": "dev",
            "base_kind": "ethos_accepted_root",
            "head": _ACCEPTED_HEAD,
            "tree": _ACCEPTED_TREE,
        },
        "integration": "ancestor",
        "coordination": coordination,
        "occupancy": {"state": "clear", "processes": []},
    }
    expected = WCPCloseoutExpectation(
        branch=_BRANCH,
        path=lane_path,
        head=_HEAD,
        lane_id=_LANE_ID,
        lane_layout=_LANE_LAYOUT,
        executor_ref=_EXECUTOR,
        decision_bytes=decision_bytes,
        observation=observation,
        chronicle_ref=_CHRONICLE_REF,
        accepted_branch="dev",
        accepted_head=_ACCEPTED_HEAD,
        accepted_tree=_ACCEPTED_TREE,
    )
    return expected, response


def _set(payload: dict[str, object], dotted: str, value: object) -> None:
    target = payload
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[part]  # type: ignore[assignment,index]
    target[parts[-1]] = value


def _delete(payload: dict[str, object], dotted: str) -> None:
    target = payload
    parts = dotted.split(".")
    for part in parts[:-1]:
        target = target[part]  # type: ignore[assignment,index]
    del target[parts[-1]]


def _process_is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    stat = Path(f"/proc/{pid}/stat")
    if stat.exists():
        try:
            return stat.read_text(encoding="utf-8").split()[2] != "Z"
        except (IndexError, OSError):
            return True
    return True


def _wait_for_process_exit(pid: int) -> bool:
    deadline = time.monotonic() + 2
    while _process_is_running(pid) and time.monotonic() < deadline:
        time.sleep(0.01)
    return not _process_is_running(pid)


@pytest.mark.parametrize(
    ("field", "bad"),
    [
        ("ok", False),
        ("schema_version", 1),
        ("action", "other"),
        ("admission_mode", "owner_bound"),
        ("lane.id", "other"),
        ("lane.layout", "legacy_ownerless"),
        ("lane.branch", "work/other"),
        ("lane.path", "/tmp/other"),
        ("lane.head", "9" * 40),
        ("decision_id", "lane-decision:other"),
        ("chronicle_ref", "evidence/chronicle/other.md"),
        ("decision_sha256", "0" * 64),
        ("executor_ref", "agent:other"),
        ("observation_digest", "0" * 64),
        ("chronicle_digest", "0" * 64),
        ("base", "main"),
        ("control_branch", "main"),
        ("source.base_branch", "main"),
        ("source.base_kind", "generic_main"),
        ("source.head", "9" * 40),
        ("source.tree", "8" * 40),
        ("integration", "tree_represented"),
        ("coordination.lease_state", "active"),
        ("coordination.claim_binding", "bound"),
        ("coordination.claim_id", "claim"),
        ("coordination.binding_digest", "0" * 64),
        ("occupancy.state", "occupied"),
    ],
)
def test_wcp_response_fails_closed_on_binding_mismatch(field: str, bad: object) -> None:
    expected, response = _fixture()
    _set(response, field, bad)

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response(response, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_mismatch"
    assert raised.value.detail == field


@pytest.mark.parametrize(
    "field",
    [
        "schema_version",
        "action",
        "admission_mode",
        "lane",
        "decision_id",
        "chronicle_ref",
        "decision_sha256",
        "executor_ref",
        "observation_digest",
        "chronicle_digest",
        "base",
        "control_branch",
        "source",
        "integration",
        "coordination",
        "occupancy",
    ],
)
def test_wcp_response_fails_closed_when_required_binding_is_missing(field: str) -> None:
    expected, response = _fixture()
    del response[field]

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response(response, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_missing"
    assert raised.value.detail == field


@pytest.mark.parametrize(
    "field",
    [
        "coordination.lease_state",
        "coordination.claim_binding",
        "coordination.claim_id",
        "coordination.binding_digest",
    ],
)
def test_wcp_response_requires_every_published_coordination_field(field: str) -> None:
    expected, response = _fixture()
    _delete(response, field)

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response(response, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_missing"
    assert raised.value.detail == field


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("lease_id", "lease:forged"),
        ("holder_ref", "agent:test:case:forged"),
        ("lease", {"lease_id": "lease:forged"}),
    ],
)
def test_wcp_response_rejects_unpublished_coordination_fields(field: str, value: object) -> None:
    expected, response = _fixture()
    coordination = response["coordination"]
    assert isinstance(coordination, dict)
    coordination[field] = value

    with pytest.raises(WCPResponseError) as raised:
        validate_worktree_closeout_response(response, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_invalid"
    assert raised.value.detail == f"coordination.{field}"


def test_wcp_response_accepts_the_exact_expected_binding() -> None:
    expected, response = _fixture()

    assert validate_worktree_closeout_response(deepcopy(response), expected=expected) == response


def test_wcp_error_exposes_stable_gap_and_separate_detail() -> None:
    error = WCPResponseError("lane_resolution_wcp_timeout", "worktree-closeout-check")

    assert error.gap == "lane_resolution_wcp_timeout"
    assert error.detail == "worktree-closeout-check"
    assert str(error) == "lane_resolution_wcp_timeout:worktree-closeout-check"


def test_bounded_runner_rejects_timeout() -> None:
    with pytest.raises(WCPResponseError) as raised:
        wcp_adapter._run_bounded_output(  # noqa: SLF001, RUF100 - bounded-runner contract
            [sys.executable, "-c", "import time; time.sleep(1)"],
            timeout_seconds=0.01,
        )

    assert raised.value.gap == "lane_resolution_wcp_timeout"


def test_bounded_runner_rejects_oversize(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wcp_adapter, "_MAX_RESPONSE_BYTES", 32)

    with pytest.raises(WCPResponseError) as raised:
        wcp_adapter._run_bounded_output(  # noqa: SLF001, RUF100 - bounded-runner contract
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 64)"],
            timeout_seconds=2,
        )

    assert raised.value.gap == "lane_resolution_wcp_response_oversize"


@pytest.mark.parametrize(
    ("failure", "expected_gap"),
    [
        ("timeout", "lane_resolution_wcp_timeout"),
        ("oversize", "lane_resolution_wcp_response_oversize"),
    ],
)
def test_bounded_runner_terminates_descendant_process_group(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    expected_gap: str,
) -> None:
    monkeypatch.setattr(wcp_adapter, "_MAX_RESPONSE_BYTES", 32)
    pid_path = tmp_path / "descendant.pid"
    trigger = (
        "sys.stdout.buffer.write(b'x' * 64); sys.stdout.flush(); time.sleep(60)"
        if failure == "oversize"
        else "raise SystemExit(0)"
    )
    startup_delay = "time.sleep(0.3); " if failure == "timeout" else ""
    script = (
        "import pathlib, subprocess, sys, time; "
        f"{startup_delay}"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)']); "
        f"pathlib.Path({pid_path.as_posix()!r}).write_text(str(child.pid), encoding='utf-8'); "
        f"{trigger}"
    )

    with pytest.raises(WCPResponseError) as raised:
        wcp_adapter._run_bounded_output(  # noqa: SLF001, RUF100 - process-group contract
            [sys.executable, "-c", script],
            timeout_seconds=2,
        )

    assert raised.value.gap == expected_gap
    descendant_pid = int(pid_path.read_text(encoding="utf-8"))
    try:
        assert _wait_for_process_exit(descendant_pid)
    finally:
        if _process_is_running(descendant_pid):
            os.kill(descendant_pid, signal.SIGKILL)


def test_wcp_command_rejects_non_json_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    decision_path = tmp_path / "decision.json"
    expected, _response = _fixture()
    decision_path.write_bytes(expected.decision_bytes)
    monkeypatch.setattr(wcp_adapter, "_run_bounded_output", lambda *_args, **_kwargs: (0, b"no"))

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(
            repo=repo,
            decision_path=decision_path,
            expected=expected,
        )

    assert raised.value.gap == "lane_resolution_wcp_response_invalid_json"


@pytest.mark.parametrize(
    "output",
    [
        pytest.param(b"1" * 5000, id="integer-conversion-limit"),
        pytest.param(b"[" * 400_000 + b"]" * 400_000, id="nesting-limit"),
    ],
)
def test_wcp_command_maps_json_parser_resource_errors_to_stable_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, output: bytes
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    decision_path = tmp_path / "decision.json"
    expected, _response = _fixture()
    decision_path.write_bytes(expected.decision_bytes)
    monkeypatch.setattr(wcp_adapter, "_run_bounded_output", lambda *_args, **_kwargs: (0, output))

    with pytest.raises(WCPResponseError) as raised:
        run_worktree_closeout_check(repo=repo, decision_path=decision_path, expected=expected)

    assert raised.value.gap == "lane_resolution_wcp_response_invalid_json"


def test_wcp_command_uses_canonical_absolute_repo_and_decision_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    decision_target = tmp_path / "records" / "decision.json"
    decision_target.parent.mkdir()
    expected, response = _fixture()
    decision_target.write_bytes(expected.decision_bytes)
    decision_link = tmp_path / "decision-link.json"
    decision_link.symlink_to(decision_target)
    commands: list[list[str]] = []

    def run(command: list[str], *, timeout_seconds: float) -> tuple[int, bytes]:
        del timeout_seconds
        commands.append(command)
        return 0, json.dumps(response).encode()

    monkeypatch.setattr(wcp_adapter, "_run_bounded_output", run)

    report = run_worktree_closeout_check(
        repo=repo / ".",
        decision_path=decision_link,
        expected=replace(expected),
    )

    assert report == response
    command = commands[0]
    assert command[command.index("--repo") + 1] == repo.resolve().as_posix()
    assert (
        command[command.index("--ownerless-decision") + 1] == decision_target.resolve().as_posix()
    )
