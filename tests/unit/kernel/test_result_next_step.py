"""A result's next step is data: argv, effects, authorization and binding, never text to parse."""

from __future__ import annotations

import shlex

import pytest

from ethos.result import EthosResult

_HEAD = "a" * 40
_CANDIDATE = "c" * 40
_EVIDENCE_WRITE = ["local-evidence-write", "local-write"]
_REMOTE = ["read", "remote-read", "local-evidence-write", "remote-write"]


def _next(next_action: str, **fields: object) -> dict[str, object]:
    values = {"command": "land", "verdict": "pass", "state": "ready"} | fields
    result = EthosResult.model_validate(values | {"next_action": next_action})
    return result.to_dict()["next"]


def test_a_publish_apply_names_its_remote_write_and_its_authority() -> None:
    """A harness sees that running this argv writes a remote and which token authorizes it."""
    argv = (
        *("ethos", "publish", "--receipt", "/store/r.json", "--apply", "--authorize"),
        *("--expect-head", _HEAD, "--root", "/repo", "--json"),
    )

    step = _next(shlex.join(argv), command="publish", state="ready_to_publish")

    assert step == {
        "kind": "command",
        "form": "publish.apply",
        "argv": list(argv),
        "effects": _REMOTE,
        "destructive": False,
        "authorization": "authorize",
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

    assert (step["kind"], step["form"]) == ("command", "land.closeout.apply")
    assert step["effects"] == ["read", *_EVIDENCE_WRITE]
    assert step["authorization"] == "authorize"
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
    """A decision in prose, or a done result: nothing for an agent to run."""
    step = _next(text, **fields)

    assert step == {
        "kind": kind,
        "form": "",
        "argv": [],
        "effects": [],
        "destructive": False,
        "authorization": authorization,
        "binding": {},
        "why": why,
    }


def test_a_decision_carries_the_command_a_person_approves() -> None:
    """The destructive apply a preview hands to a person is data, never hidden behind prose."""
    argv = ("ethos", "lane", "retire", "abandon", "--receipt", "/r.json", "--receipt-sha256", "x")
    argv += ("--apply", "--authorize", "--json")

    step = _next(shlex.join(argv), user_decision_required=True)

    assert (step["kind"], step["argv"], step["authorization"]) == ("decision", list(argv), "human")
    assert (step["destructive"], step["effects"]) == (True, _EVIDENCE_WRITE)
    assert step["binding"] == {"receipt": "/r.json"}


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


_RETIRE = "lane retire absorbed-ref --apply --authorize --confirm-irreversible"


@pytest.mark.parametrize(
    ("command", "effects", "authorization", "destructive"),
    [
        ("status --json", ["read"], "none", False),
        (
            "prove --full --execute --json",
            ["read", "execute", "local-evidence-write"],
            "none",
            False,
        ),
        ("mcp --root /repo", ["execute", "opaque"], "human", True),
        ("publish --ref refs/heads/dev --json", _REMOTE[:3], "none", False),
        ("publish --retire --receipt /r --apply --authorize", _REMOTE, "authorize", True),
        ("lane handoff revoke-source --apply", _EVIDENCE_WRITE, "apply", True),
        ("lane handoff transfer --apply", _EVIDENCE_WRITE, "apply", False),
        (_RETIRE, _EVIDENCE_WRITE, "confirm-irreversible", True),
        ("lane lease takeover --authorization /a --apply", _EVIDENCE_WRITE, "attestation", False),
        ("land --retag v1 --apply --authorize", ["read", *_EVIDENCE_WRITE], "authorize", True),
        # The closeout preview only reads the refs and worktrees it reports.
        ("land --closeout --json", ["read"], "none", False),
        # A root argv that selects no catalog operation could do anything, so a person decides it.
        ("land --closeout --release --json", ["opaque"], "human", True),
        ("publish --apply --json", ["opaque"], "human", True),
    ],
)
def test_an_argv_names_its_effects_authority_and_any_deletion(
    command: str, effects: list[str], authorization: str, *, destructive: bool
) -> None:
    """Effects run from the least to the most consequential; only a selected deletion counts."""
    step = _next(shlex.join(("ethos", *shlex.split(command))))

    assert (step["effects"], step["authorization"]) == (effects, authorization)
    assert step["destructive"] is destructive


def test_a_reader_re_derives_next_and_never_trusts_a_carried_one() -> None:
    """A carried step is only checked for shape; every reader derives its own from the text."""
    result = EthosResult(
        command="status", verdict="pass", state="ready", next_action="ethos status --json"
    )
    payload = result.to_dict()
    payload["next"] = {**payload["next"], "argv": ["ethos", "publish", "--apply"]}

    assert EthosResult.from_payload(payload).to_dict()["next"] == result.to_dict()["next"]
    for field, value in (("kind", "launch"), ("authorization", "embedded")):
        payload["next"] = {**result.to_dict()["next"], field: value}
        with pytest.raises(ValueError, match=field):
            EthosResult.from_payload(payload)
