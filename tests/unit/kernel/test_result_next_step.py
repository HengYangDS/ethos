"""A result's next step is data: argv, effects, authorization and binding, never text to parse."""

from __future__ import annotations

import shlex

import pytest

from ethos.result import EthosResult

_HEAD = "a" * 40
_CANDIDATE = "c" * 40


def _next(next_action: str, **fields: object) -> dict[str, object]:
    values = {"command": "land", "verdict": "pass", "state": "ready"} | fields
    result = EthosResult.model_validate(values | {"next_action": next_action})
    return result.to_dict()["next"]


def test_a_publish_apply_names_its_remote_write_and_embedded_authorization() -> None:
    """A harness sees that running this argv writes a remote and carries its authorization."""
    argv = (
        *("ethos", "publish", "--receipt", "/store/r.json", "--apply", "--authorize"),
        *("--expect-head", _HEAD, "--root", "/repo", "--json"),
    )

    step = _next(shlex.join(argv), command="publish", state="ready_to_publish")

    assert step == {
        "kind": "command",
        "argv": list(argv),
        "effects": ["remote-read", "local-evidence-write", "remote-write"],
        "authorization": "embedded",
        "binding": {"receipt": "/store/r.json", "head": _HEAD, "root": "/repo"},
        "why": "ready_to_publish",
    }


def test_a_land_closeout_binds_both_heads_and_writes_locally() -> None:
    """The binding an agent must not change is data, and the blocker it resolves is the why."""
    argv = (
        *("ethos", "land", "--closeout", "--apply", "--authorize", "--expect-head", _HEAD),
        *("--candidate-head=" + _CANDIDATE, "--root", "/repo", "--json"),
    )
    gaps = ("accepted_head_unadmitted", "proof_missing")

    step = _next(shlex.join(argv), verdict="block", state="gapped", required_gaps=gaps)

    assert step["kind"] == "command"
    assert step["effects"] == ["local-evidence-write", "local-write"]
    assert step["authorization"] == "embedded"
    assert step["binding"] == {"head": _HEAD, "candidate_head": _CANDIDATE, "root": "/repo"}
    assert step["why"] == "accepted_head_unadmitted"


@pytest.mark.parametrize(
    ("text", "fields", "kind", "authorization", "why"),
    [
        (
            "approve the release risk",
            {"user_decision_required": True},
            "decision",
            "human",
            "ready",
        ),
        ("", {"state": "landed"}, "done", "none", "landed"),
    ],
)
def test_a_step_without_a_command_carries_no_argv(
    text: str, fields: dict[str, object], kind: str, authorization: str, why: str
) -> None:
    """A decision only a person can take, or a done result: nothing for an agent to run."""
    step = _next(text, **fields)

    assert step == {
        "kind": kind,
        "argv": [],
        "effects": [],
        "authorization": authorization,
        "binding": {},
        "why": why,
    }


@pytest.mark.parametrize(
    "text",
    [
        "repair the failed readiness gate",
        "openspec new change <name>",
        "ethos land --expect-head <head> --json",
        "run ethos status --json",
        'ethos land --subject "unterminated',
    ],
)
def test_prose_and_templates_stay_instructions(text: str) -> None:
    """Text that is not one exact ETHOS argv is never offered as something to execute."""
    step = _next(text, verdict="block", state="gapped", required_gaps=("gate_failed:static",))

    assert step["kind"] == "instruction"
    assert step["argv"] == []
    assert step["why"] == "gate_failed:static"


@pytest.mark.parametrize(
    ("argv", "effects"),
    [
        (("ethos", "status", "--json"), ["read"]),
        (("ethos", "lane", "status", "--root", "/lane", "--json"), ["read"]),
        (("ethos", "prove", "--full", "--execute", "--json"), ["execute", "local-evidence-write"]),
        (
            ("ethos", "hook", "install", "--authorize", "--json"),
            ["local-evidence-write", "local-write"],
        ),
        (("ethos", "host", "run", "nox"), ["execute", "local-evidence-write", "local-write"]),
        (
            ("ethos", "publish", "--ref", "refs/heads/dev", "--json"),
            ["remote-read", "local-evidence-write"],
        ),
    ],
)
def test_effects_order_from_the_least_to_the_most_consequential(
    argv: tuple[str, ...], effects: list[str]
) -> None:
    """Readers need no authorization; anything that writes or executes says so."""
    step = _next(shlex.join(argv))

    assert step["effects"] == effects
    assert step["authorization"] == ("embedded" if "local-write" in effects else "none")


def test_a_reader_re_derives_next_and_never_trusts_a_carried_one() -> None:
    """A carried step is only checked for shape; every reader derives its own from the text."""
    result = EthosResult(
        command="status", verdict="pass", state="ready", next_action="ethos status --json"
    )
    payload = result.to_dict()
    payload["next"] = {**payload["next"], "argv": ["ethos", "publish", "--apply"]}

    assert EthosResult.from_payload(payload).to_dict()["next"] == result.to_dict()["next"]
    payload["next"] = {**payload["next"], "kind": "launch"}
    with pytest.raises(ValueError, match="kind"):
        EthosResult.from_payload(payload)
