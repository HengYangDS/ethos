"""Strict WCP admission binding at the ETHOS closeout boundary."""

from __future__ import annotations

import hashlib
import json
import os
import selectors
import signal
import subprocess
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING
from typing import BinaryIO
from typing import cast

if TYPE_CHECKING:
    from pathlib import Path

_WCP_SCHEMA_VERSION = "workstation.repo-family-governance.v1"
_SHA256 = frozenset("0123456789abcdef")
_SHA256_LENGTH = 64
_MAX_RESPONSE_BYTES = 1024 * 1024
_READ_CHUNK_BYTES = 64 * 1024
_ACTION = "worktree-closeout-check"

_MISSING = "lane_resolution_wcp_response_missing"
_INVALID = "lane_resolution_wcp_response_invalid"
_MISMATCH = "lane_resolution_wcp_response_mismatch"
_EXPECTATION_INVALID = "lane_resolution_wcp_expectation_invalid"
_RESPONSE_OVERSIZE = "lane_resolution_wcp_response_oversize"
_TIMEOUT = "lane_resolution_wcp_timeout"
_UNAVAILABLE = "lane_resolution_wcp_unavailable"
_PATH_INVALID = "lane_resolution_wcp_path_invalid"
_DECISION_STALE = "lane_resolution_wcp_decision_stale"
_REJECTED = "lane_resolution_wcp_rejected"
_INVALID_JSON = "lane_resolution_wcp_response_invalid_json"
_STDOUT_PIPE_UNAVAILABLE = "stdout pipe unavailable"


class WCPResponseError(ValueError):
    """Stable machine gap plus non-authoritative diagnostic detail."""

    def __init__(self, gap: str, detail: str = "") -> None:
        self.gap = gap
        self.detail = detail
        super().__init__(f"{gap}:{detail}" if detail else gap)


@dataclass(frozen=True, slots=True)
class WCPCloseoutExpectation:
    """Caller-owned values that one WCP response must bind exactly."""

    branch: str
    path: str
    head: str
    lane_id: str
    lane_layout: str
    executor_ref: str
    decision_bytes: bytes
    observation: Mapping[str, object]
    chronicle_ref: str
    accepted_branch: str
    accepted_head: str
    accepted_tree: str


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if value is None:
        raise WCPResponseError(_MISSING, field)
    if not isinstance(value, Mapping):
        raise WCPResponseError(_INVALID, field)
    return cast("Mapping[str, object]", value)


def _exact(container: Mapping[str, object], field: str, expected: object, prefix: str = "") -> None:
    name = f"{prefix}.{field}" if prefix else field
    if field not in container:
        raise WCPResponseError(_MISSING, name)
    actual = container[field]
    if type(actual) is not type(expected) or actual != expected:
        raise WCPResponseError(_MISMATCH, name)


def _required_string(container: Mapping[str, object], field: str, prefix: str = "") -> str:
    name = f"{prefix}.{field}" if prefix else field
    if field not in container:
        raise WCPResponseError(_MISSING, name)
    value = container[field]
    if not isinstance(value, str) or not value:
        raise WCPResponseError(_INVALID, name)
    return value


def _reject_unpublished_fields(
    container: Mapping[str, object], *, published: frozenset[str], prefix: str
) -> None:
    for field in container:
        if not isinstance(field, str) or field not in published:
            raise WCPResponseError(_INVALID, f"{prefix}.{field}")


def _sha256(value: str, field: str) -> str:
    if len(value) != _SHA256_LENGTH or any(character not in _SHA256 for character in value):
        raise WCPResponseError(_EXPECTATION_INVALID, field)
    return value


def _git_oid(value: str, field: str) -> str:
    if len(value) not in {40, 64} or any(character not in _SHA256 for character in value):
        raise WCPResponseError(_EXPECTATION_INVALID, field)
    return value


def _decision_binding(expected: WCPCloseoutExpectation) -> tuple[str, str, str]:
    try:
        decision = json.loads(expected.decision_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WCPResponseError(_EXPECTATION_INVALID, "decision_bytes.json") from exc
    decision = _mapping(decision, "expected.decision_bytes")
    decision_id = _required_string(decision, "decision_id", "expected.decision_bytes")
    chronicle_digest = _sha256(
        _required_string(decision, "chronicle_digest", "expected.decision_bytes"),
        "expected.decision_bytes.chronicle_digest",
    )
    observation_digest = _digest(expected.observation)
    _exact(decision, "observation", dict(expected.observation), "expected.decision_bytes")
    _exact(decision, "observation_digest", observation_digest, "expected.decision_bytes")
    _exact(decision, "chronicle_ref", expected.chronicle_ref, "expected.decision_bytes")
    return decision_id, observation_digest, chronicle_digest


def _coordination_digest(expected: WCPCloseoutExpectation) -> str:
    return _digest(
        {
            "branch": expected.branch,
            "path": expected.path,
            "head": expected.head,
            "accepted_head": expected.accepted_head,
            "worktree_binding": "linked",
            "dirty": False,
            "relation_to_accepted": "ancestor_of_accepted",
            "lease_state": "missing",
            "lease_id": "",
            "holder_ref": "",
            "claim_binding": "missing",
            "claim_id": "",
        }
    )


def validate_worktree_closeout_response(
    response: Mapping[str, object], *, expected: WCPCloseoutExpectation
) -> dict[str, object]:
    """Validate every security-relevant WCP field against caller-owned truth."""
    payload = _mapping(response, "response")
    decision_id, observation_digest, chronicle_digest = _decision_binding(expected)
    _git_oid(expected.accepted_tree, "expected.accepted_tree")
    for field, value in (
        ("ok", True),
        ("schema_version", _WCP_SCHEMA_VERSION),
        ("action", "worktree_closeout_check"),
        ("admission_mode", "ownerless_decision"),
        ("decision_id", decision_id),
        ("chronicle_ref", expected.chronicle_ref),
        ("decision_sha256", hashlib.sha256(expected.decision_bytes).hexdigest()),
        ("executor_ref", expected.executor_ref),
        ("observation_digest", observation_digest),
        ("chronicle_digest", chronicle_digest),
        ("base", expected.accepted_branch),
        ("control_branch", expected.accepted_branch),
        ("integration", "ancestor"),
    ):
        _exact(payload, field, value)

    lane = _mapping(payload.get("lane"), "lane")
    for field, value in (
        ("id", expected.lane_id),
        ("branch", expected.branch),
        ("path", expected.path),
        ("head", expected.head),
        ("layout", expected.lane_layout),
    ):
        _exact(lane, field, value, "lane")

    source = _mapping(payload.get("source"), "source")
    for field, value in (
        ("base_branch", expected.accepted_branch),
        ("base_kind", "ethos_accepted_root"),
        ("head", expected.accepted_head),
        ("tree", expected.accepted_tree),
    ):
        _exact(source, field, value, "source")

    coordination = _mapping(payload.get("coordination"), "coordination")
    for field, value in (
        ("lease_state", "missing"),
        ("claim_binding", "missing"),
        ("claim_id", ""),
        ("binding_digest", _coordination_digest(expected)),
    ):
        _exact(coordination, field, value, "coordination")
    _reject_unpublished_fields(
        coordination,
        published=frozenset({"lease_state", "claim_binding", "claim_id", "binding_digest"}),
        prefix="coordination",
    )

    occupancy = _mapping(payload.get("occupancy"), "occupancy")
    _exact(occupancy, "state", "clear", "occupancy")
    _exact(occupancy, "processes", [], "occupancy")
    return dict(payload)


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        if process.poll() is None:
            process.kill()
    try:
        process.wait(timeout=1)
    except (OSError, subprocess.TimeoutExpired):
        return


def _stdout_pipe(process: subprocess.Popen[bytes]) -> BinaryIO:
    stdout = process.stdout
    if stdout is None:
        raise OSError(_STDOUT_PIPE_UNAVAILABLE)  # noqa: TRY003, RUF100 - stable adapter fault detail
    return cast("BinaryIO", stdout)


def _remaining_or_timeout(deadline: float, command: list[str], timeout_seconds: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise subprocess.TimeoutExpired(command, timeout_seconds)
    return remaining


def _read_bounded_stdout(
    stdout,
    *,
    command: list[str],
    deadline: float,
    timeout_seconds: float,
) -> bytes:
    output = bytearray()
    with selectors.DefaultSelector() as selector:
        selector.register(stdout, selectors.EVENT_READ)
        while True:
            remaining = _remaining_or_timeout(deadline, command, timeout_seconds)
            if not selector.select(remaining):
                raise subprocess.TimeoutExpired(command, timeout_seconds)
            chunk = os.read(
                stdout.fileno(),
                min(_READ_CHUNK_BYTES, _MAX_RESPONSE_BYTES + 1 - len(output)),
            )
            if not chunk:
                return bytes(output)
            output.extend(chunk)
            if len(output) > _MAX_RESPONSE_BYTES:
                raise WCPResponseError(_RESPONSE_OVERSIZE, str(_MAX_RESPONSE_BYTES))


def _run_bounded_output(command: list[str], *, timeout_seconds: float) -> tuple[int, bytes]:
    """Run one command while bounding time and captured stdout before allocation."""
    process: subprocess.Popen[bytes] | None = None
    stdout = None
    try:
        process = subprocess.Popen(  # noqa: S603, RUF100 - bounded exact argv, no shell
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        stdout = _stdout_pipe(process)
        deadline = time.monotonic() + timeout_seconds
        output = _read_bounded_stdout(
            stdout,
            command=command,
            deadline=deadline,
            timeout_seconds=timeout_seconds,
        )
        remaining = _remaining_or_timeout(deadline, command, timeout_seconds)
        return process.wait(timeout=remaining), output
    except WCPResponseError:
        if process is not None:
            _stop_process(process)
        raise
    except subprocess.TimeoutExpired as exc:
        if process is not None:
            _stop_process(process)
        raise WCPResponseError(_TIMEOUT, _ACTION) from exc
    except OSError as exc:
        if process is not None:
            _stop_process(process)
        raise WCPResponseError(_UNAVAILABLE, type(exc).__name__) from exc
    finally:
        if stdout is not None:
            stdout.close()


def _canonical_path(path: Path, *, kind: str, directory: bool) -> Path:
    try:
        canonical = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise WCPResponseError(_PATH_INVALID, kind) from exc
    valid = canonical.is_dir() if directory else canonical.is_file()
    if not valid:
        raise WCPResponseError(_PATH_INVALID, kind)
    return canonical


def run_worktree_closeout_check(
    *,
    repo: Path,
    decision_path: Path,
    expected: WCPCloseoutExpectation,
    workstation: str = "workstation",
    timeout_seconds: float = 20.0,
) -> dict[str, object]:
    """Run the read-only WCP check with bounded time/output, then validate it."""
    canonical_repo = _canonical_path(repo, kind="repo", directory=True)
    canonical_decision = _canonical_path(decision_path, kind="decision", directory=False)
    try:
        current_decision_bytes = canonical_decision.read_bytes()
    except OSError as exc:
        raise WCPResponseError(_PATH_INVALID, "decision") from exc
    if current_decision_bytes != expected.decision_bytes:
        raise WCPResponseError(_DECISION_STALE, "decision")
    command = [
        workstation,
        "repo-family",
        "worktree-closeout-check",
        "--repo",
        canonical_repo.as_posix(),
        "--branch",
        expected.branch,
        "--path",
        expected.path,
        "--ownerless-decision",
        canonical_decision.as_posix(),
        "--executor-ref",
        expected.executor_ref,
        "--control-branch",
        expected.accepted_branch,
        "--base",
        expected.accepted_branch,
        "--expect-head",
        expected.head,
    ]
    returncode, output = _run_bounded_output(command, timeout_seconds=timeout_seconds)
    if returncode != 0:
        raise WCPResponseError(_REJECTED, str(returncode))
    try:
        response = json.loads(output)
    except (RecursionError, ValueError) as exc:
        raise WCPResponseError(_INVALID_JSON, _ACTION) from exc
    return validate_worktree_closeout_response(_mapping(response, "response"), expected=expected)
