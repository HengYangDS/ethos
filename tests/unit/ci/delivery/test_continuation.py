"""Acceptance readers follow the typed `next` step and never parse `next_action`."""

from ethos.result import EthosResult
from tools.ci.delivery.acceptance.invocation import continuation


def _result(next_action: str, *, decision: bool = False) -> dict[str, object]:
    return EthosResult(
        command="status",
        verdict="block",
        state="blocked",
        required_gaps=("candidate_branch_missing",),
        next_action=next_action,
        user_decision_required=decision,
    ).to_dict()


def test_a_reader_follows_only_the_typed_step_of_its_kind() -> None:
    """The argv comes from `next`; prose, another kind or a missing step yields nothing."""
    command = _result("ethos lane candidate --apply --json")
    decision = _result("ethos lane candidate --apply --json", decision=True)

    assert continuation(command) == ("ethos", "lane", "candidate", "--apply", "--json")
    assert continuation(decision) == ()
    assert continuation(decision, kind="decision") == continuation(command)
    assert continuation(_result("repair the reported gap and rerun the command")) == ()
    assert continuation({"next_action": "ethos status --json"}) == ()
