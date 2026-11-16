"""The process actor: the one reader of `ETHOS_ACTOR`, its flag and the steps that supply it.

The actor is the executor's own identity. An invocation names it with `--actor`, and `ETHOS_ACTOR`
is the declared fallback. A result that lacks one continues to an instruction that asks for it, and
a result whose actor is not the holder continues to the handoff, never to the holder's name.
"""

from __future__ import annotations

import os
import shlex
from typing import TYPE_CHECKING

from ethos.adapters.process import process_input
from ethos.normalization.coercion import integer_value

if TYPE_CHECKING:
    from collections.abc import Mapping
    from contextlib import AbstractContextManager
    from pathlib import Path

ACTOR_VARIABLE = "ETHOS_ACTOR"
ACTOR_FLAG = "--actor"
ACTOR_HELP = "The executor's own identity, such as `agent:<id>`; `ETHOS_ACTOR` is the fallback."
# Prose, so the step is an instruction; the invocation names the flag as the step's input.
ACTOR_STEP = f"rerun the command with {ACTOR_FLAG} <your own identity>"
LOCAL_ISSUER = "agent:local:process:ethos"


def process_actor() -> str:
    """Return the actor this process declares, stripped; empty when it declares none."""
    return os.environ.get(ACTOR_VARIABLE, "").strip()


def process_issuer() -> str:
    """Return the actor that issues this process's records, or the local process default."""
    return process_actor() or LOCAL_ISSUER


def invocation_actor(actor: str | None) -> AbstractContextManager[None]:
    """Let a given actor win over the fallback for one invocation and its children."""
    return process_input(ACTOR_VARIABLE, (actor or "").strip() or None)


def handoff_step(root: Path, branch: str, lease: Mapping[str, object], target: str) -> str:
    """Render the preview that moves one held Lease generation to the target, in the lane.

    A Lease without a readable generation, expiry or holder names nothing to move, and a blank
    target nobody to move it to: neither has a step. The generation is read as every reader
    of a Lease reads it.
    """
    generation = integer_value(lease.get("generation"))
    expires_at = str(lease.get("expires_at") or "").strip()
    holder_ref = str(lease.get("holder_ref") or "").strip()
    if generation < 1 or not (expires_at and holder_ref and target.strip()):
        return ""
    return shlex.join(
        (
            *("ethos", "lane", "handoff", "transfer"),
            *("--generation", str(generation)),
            *("--expires-at", expires_at, "--branch", branch),
            *("--holder-ref", holder_ref, "--target-holder-ref", target),
            *("--root", root.resolve().as_posix(), "--json"),
        )
    )
