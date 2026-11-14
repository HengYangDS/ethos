"""Acceptance readers follow the typed `next` step and never parse `next_action`."""

import json
import sys

from ethos.repository.policy.schema import validate_schema_instance
from ethos.result import EthosResult
from ethos.result import apply_payload_budget
from tests.support import ethos_cli_runner
from tools.ci.delivery.acceptance.invocation import continuation
from tools.ci.delivery.acceptance.invocation import invoke


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


def test_every_reader_keeps_the_inputs_a_step_carries(tmp_path, monkeypatch) -> None:
    """One synthetic result, read by each reader of `next` in the product, tools and support."""
    carried = EthosResult.model_validate(
        {
            "command": "status",
            "verdict": "pass",
            "state": "ready",
            "next_action": "ethos status --json",
            "data": {"log": "x" * 40_000},
        }
    ).to_dict()
    carried["next"]["inputs"] = [{"name": "change", "flag": "--change", "description": "Its ID."}]
    full = EthosResult.from_payload(carried)
    bounded = apply_payload_budget(full, root=tmp_path).to_json()
    echo = (sys.executable, "-I", "-c", "import sys; print(sys.argv[1])", bounded)
    monkeypatch.setattr(ethos_cli_runner, "run_application", lambda _: sys.stdout.write(bounded))
    reads = (
        full.to_dict(),  # the result model
        json.loads(bounded),  # the copy that the payload budget and the runtime name share
        invoke(tmp_path, echo, environment={})[1],  # the acceptance reader, through the detail
        ethos_cli_runner.run_ethos("status", "--json", cwd=tmp_path),  # the test support
    )

    assert [read["next"] for read in reads] == [carried["next"]] * 4
    assert validate_schema_instance("result.schema.json", carried)["required_gaps"] == []
    assert continuation(reads[2]) == ("ethos", "status", "--json")
