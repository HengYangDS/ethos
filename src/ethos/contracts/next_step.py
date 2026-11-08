"""The next step as data: what an agent runs, what it changes, who authorizes it and its binding.

A step is derived from the same facts that render a result's `next_action`, so the text and the
data can never disagree, and it is re-derived on every read rather than stored or replayed. A root
argv takes its form, effects and authority from the catalog operation it selects.
"""

from __future__ import annotations

import shlex
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from ethos.contracts.admission import StepAuthorization
from ethos.contracts.admission import StepEffect
from ethos.contracts.admission import ethos_step_authorization
from ethos.contracts.admission import ethos_step_destructive
from ethos.contracts.admission import ethos_step_effects
from ethos.contracts.operations.catalog import select_argv
from ethos.contracts.value import JsonObject

StepKind = Literal["command", "instruction", "decision", "done"]
# The flags whose values an agent must pass unchanged, by the name a binding reads.
_BINDINGS = {
    "--root": "root",
    "--expect-head": "head",
    "--candidate-head": "candidate_head",
    "--receipt": "receipt",
    "--expect-plan-digest": "plan_digest",
    "--expires-at": "lease_expires_at",
}


class NextStep(BaseModel):
    """One next step: a `command` an agent runs, or a `decision` whose argv a person approves."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    kind: StepKind
    # The catalog operation a root argv selects; empty for any other step.
    form: str = ""
    argv: tuple[str, ...] = ()
    effects: tuple[StepEffect, ...] = ()
    destructive: bool = False
    authorization: StepAuthorization = "none"
    binding: JsonObject = Field(default_factory=dict)
    why: str


def derive_next_step(text: str, *, continuation: str, why: str) -> NextStep:
    """Return the structured form of one rendered next action; prose stays an instruction."""
    if continuation == "done":
        return NextStep(kind="done", why=why)
    argv = _exact_ethos_argv(text)
    decision = continuation == "await-user"
    if not argv:
        if decision:
            return NextStep(kind="decision", authorization="human", why=why)
        return NextStep(kind="instruction", why=why)
    form, effects, destructive, authorization = _classified(argv)
    return NextStep(
        kind="decision" if decision else "command",
        form=form,
        argv=argv,
        effects=effects,
        destructive=destructive,
        # What a person approves carries its argv, and no reader runs it without that approval.
        authorization="human" if decision else authorization,
        binding=_binding(argv),
        why=why,
    )


def _classified(
    argv: tuple[str, ...],
) -> tuple[str, tuple[StepEffect, ...], bool, StepAuthorization]:
    """Classify a root argv by the operation it selects and any other argv by its declared rows."""
    root = select_argv(argv)
    if root is None:
        effects = ethos_step_effects(argv)
        destructive = ethos_step_destructive(argv, effects)
        return "", effects, destructive, ethos_step_authorization(argv, effects)
    selected = root[1]
    if selected is None:
        # A root argv that selects no operation could do anything, so a person decides it.
        return "", ("opaque",), True, "human"
    return selected.id, selected.effects, selected.destructive, selected.authorization


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
