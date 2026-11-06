"""The next step as data: what an agent runs, what it changes, who authorizes it and its binding.

A step is derived from the same facts that render a result's `next_action`, so the text and the
data can never disagree, and it is re-derived on every read rather than stored or replayed.
"""

from __future__ import annotations

import shlex
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.contracts.admission import StepEffect
from ethos.contracts.admission import ethos_step_effects
from ethos.contracts.value import JsonObject

StepKind = Literal["command", "instruction", "decision", "done"]
Authorization = Literal["none", "embedded", "human"]
# The flags whose values an agent must pass unchanged, by the name a binding reads.
_BINDINGS = {
    "--root": "root",
    "--expect-head": "head",
    "--candidate-head": "candidate_head",
    "--receipt": "receipt",
    "--expect-plan-digest": "plan_digest",
    "--expires-at": "lease_expires_at",
}
_WRITES = frozenset({"local-write", "remote-write"})


class NextStep(BaseModel):
    """One next step: only a `command` has an argv, and only a `decision` needs a human."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    kind: StepKind
    argv: tuple[str, ...] = ()
    effects: tuple[StepEffect, ...] = ()
    authorization: Authorization = "none"
    binding: JsonObject = Field(default_factory=dict)
    why: str


def derive_next_step(text: str, *, continuation: str, why: str) -> NextStep:
    """Return the structured form of one rendered next action; prose stays an instruction."""
    if continuation == "await-user":
        return NextStep(kind="decision", authorization="human", why=why)
    if continuation == "done":
        return NextStep(kind="done", why=why)
    argv = _exact_ethos_argv(text)
    if not argv:
        return NextStep(kind="instruction", why=why)
    effects = ethos_step_effects(argv)
    embedded = "--authorize" in argv or bool(_WRITES.intersection(effects))
    return NextStep(
        kind="command",
        argv=argv,
        effects=effects,
        authorization="embedded" if embedded else "none",
        binding=_binding(argv),
        why=why,
    )


def _exact_ethos_argv(text: str) -> tuple[str, ...]:
    """Return the argv one rendered ETHOS command denotes, or nothing for prose or a template."""
    try:
        argv = tuple(shlex.split(text))
    except ValueError:
        return ()
    rendered = bool(argv) and argv[0] == "ethos" and shlex.join(argv) == text.strip()
    template = any(token.startswith("<") and token.endswith(">") for token in argv)
    return argv if rendered and not template else ()


def _binding(argv: tuple[str, ...]) -> dict[str, str]:
    """Name each value the argv binds, whether written as `--flag value` or `--flag=value`."""
    binding: dict[str, str] = {}
    for index, argument in enumerate(argv):
        flag, separator, value = argument.partition("=")
        if flag in _BINDINGS:
            following = argv[index + 1] if index + 1 < len(argv) else ""
            binding[_BINDINGS[flag]] = value if separator else following
    return binding
