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


def test_a_reader_follows_only_a_typed_step_with_an_argv() -> None:
    """The argv comes from `next`; prose, a template or a missing step yields nothing."""
    argv = ("ethos", "lane", "candidate", "--apply", "--json")

    assert continuation(_result(" ".join(argv))) == argv
    assert continuation(_result(" ".join(argv), decision=True)) == argv
    assert continuation(_result("repair the reported gap and rerun the command")) == ()
    assert continuation(_result("ethos lane candidate --root <repository> --json")) == ()
    assert continuation({"next_action": "ethos status --json"}) == ()
