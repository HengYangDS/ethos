"""Installed ETHOS command invocation for package acceptance."""

from __future__ import annotations

import hashlib
import json
import shlex
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import TYPE_CHECKING
from uuid import uuid4

from ethos.adapters.process import run_command
from ethos.repository.release.resources import GUIDANCE_RESOURCE
from ethos.repository.release.resources import packaged_resource
from ethos.result import EthosResult

if TYPE_CHECKING:
    from collections.abc import Generator
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class AcceptanceObservation:
    """Bind append-only performance events to one exact package attempt."""

    path: Path
    epoch: float
    lock: Lock


_OBSERVATION: ContextVar[AcceptanceObservation | None] = ContextVar(
    "acceptance_observation", default=None
)
_PARENT_SPAN: ContextVar[str | None] = ContextVar("acceptance_parent_span", default=None)


@contextmanager
def acceptance_observation(path: Path, *, head: str, wheel_sha256: str) -> Generator[None]:
    """Keep partial events outside disposable work and reset invocation context."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "kind": "package_acceptance_events",
                "head": head,
                "wheel_sha256": wheel_sha256,
                "claim": "execution_timing_only",
                "duration_semantics": "inclusive_nested_non_additive",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    token = _OBSERVATION.set(AcceptanceObservation(path, monotonic(), Lock()))
    parent = _PARENT_SPAN.set(None)
    try:
        yield
    finally:
        _PARENT_SPAN.reset(parent)
        _OBSERVATION.reset(token)


@contextmanager
def observe_stage(name: str, *, kind: str = "stage", target: str = "") -> Generator[None]:
    """Record start before work; nested spans are inclusive, never additive."""
    observation = _OBSERVATION.get()
    if observation is None:
        yield
        return
    started = monotonic()
    span = uuid4().hex
    event = {
        "span": span,
        "parent_span": _PARENT_SPAN.get(),
        "name": name,
        "kind": kind,
        "target": target,
        "started_after_seconds": started - observation.epoch,
    }

    def append(state: str, **fields: object) -> None:
        with observation.lock, observation.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({**event, "state": state, **fields}) + "\n")

    append("running")
    token = _PARENT_SPAN.set(span)
    try:
        yield
    except BaseException as error:
        append("failed", duration_seconds=monotonic() - started, error_type=type(error).__name__)
        raise
    else:
        append("completed", duration_seconds=monotonic() - started)
    finally:
        _PARENT_SPAN.reset(token)


def command_label(command: tuple[str, ...]) -> str:
    """Identify native operations without recording probe code, paths or secrets."""
    executable = Path(command[0]).stem
    if "ethos.cli" in command:
        arguments = command[command.index("ethos.cli") + 1 :]
    elif executable == "ethos":
        arguments = command[1:]
    else:
        return executable
    count = 2 if arguments[:1] in (("hook",), ("lane",), ("attestation",)) else 1
    return " ".join(("ethos", *arguments[:count]))


def require_installed_guidance(status_json: str, origin: str) -> None:
    """Bind status guidance to the exact installed package, never a source checkout."""
    try:
        payload = json.loads(status_json)
        guidance = payload["governance_context"]["agent_guidance"]
        package = Path(origin).resolve(strict=True).parent
        expected = packaged_resource(GUIDANCE_RESOURCE, package=package).resolve(strict=True)
        observed = Path(guidance["path"]).resolve(strict=True)
        valid = (
            guidance["authority"] == "product_projection"
            and guidance["media_type"] == "text/markdown"
            and expected.is_relative_to(package)
            and observed == expected
            and guidance["sha256"] == hashlib.sha256(expected.read_bytes()).hexdigest()
        )
    except (KeyError, OSError, TypeError, ValueError):
        valid = False
    if not valid:
        message = "installed_agent_guidance_invalid"
        raise RuntimeError(message)


def invoke(
    root: Path,
    command: tuple[str, ...],
    *,
    environment: Mapping[str, str],
) -> tuple[int, dict[str, object], str]:
    """Run one installed CLI request and preserve its result and stderr.

    The deadline bounds a hung request: a hosted Windows runner can need minutes to copy,
    seal and hash a runtime while it installs a hook.
    """
    with observe_stage(command_label(command), kind="process", target=root.name):
        completed = run_command(
            root, command, env=environment, inherit_environment=False, timeout=600
        )
    try:
        result = EthosResult.from_payload(json.loads(completed.stdout))
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        message = f"package_cli_result_invalid:{shlex.join(command)}:{completed.stderr.strip()}"
        raise RuntimeError(message) from error
    if "Traceback" in completed.stdout + completed.stderr:
        message = f"package_cli_traceback:{shlex.join(command)}"
        raise RuntimeError(message)
    payload = result.to_dict()
    diagnostic = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    if stderr := completed.stderr.strip():
        diagnostic = f"{diagnostic}\nstderr:{stderr}"
    return completed.returncode, payload, diagnostic
