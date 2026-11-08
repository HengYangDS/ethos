"""A root command runs one catalog operation, or reports its refusal as a result that exits 2."""

import asyncio
import json

import pytest
from fastmcp import Client

from ethos.application.proof.operation import ProofRequest
from ethos.application.proof.operation import prove_repository
from ethos.application.publication.operation import publish_repository
from ethos.result import PAYLOAD_BUDGETS
from ethos.surface.mcp.server import create_server
from tests.support.ethos_cli_runner import run_ethos_process
from tests.support.ethos_cli_runner import run_ethos_raw

_RECEIPT = {
    "receipt": "request.json",
    "receipt_sha256": "0" * 64,
    "apply": True,
    "authorize": True,
    "expect_head": "a" * 40,
}


@pytest.mark.parametrize(
    ("argv", "gap"),
    [
        (("land", "--closeout", "--release"), "command_operation_unmatched:land"),
        (("land", "--tag", "v1"), "command_field_refused:tag"),
        (("land", "--bogus"), "command_usage_invalid:land"),
        (("land", "true"), "command_usage_invalid:land"),
        (("land", "--no-apply"), "command_usage_invalid:land"),
        (("publish", "--apply"), "command_operation_unmatched:publish"),
        (("adopt", "--create", "--purpose", "p"), "formation_root_required"),
    ],
)
def test_a_refused_request_exits_2_with_its_result_on_stdout(
    argv: tuple[str, ...], gap: str
) -> None:
    """The console prints one schema-3 refusal under `--json` and runs nothing."""
    completed = run_ethos_process(*argv, "--json")

    assert completed.returncode == 2, completed.stderr
    payload = json.loads(completed.stdout)
    assert (payload["schema_version"], payload["verdict"]) == (3, "block")
    assert (payload["state"], payload["required_gaps"]) == ("usage_refused", [gap])
    assert payload["next"]["kind"] == "instruction"


def test_help_prints_the_catalog_as_text_and_as_one_bounded_result() -> None:
    """Help lists each operation with its flags; `--json` prints the catalog within its budget."""
    text = run_ethos_process("land", "--help")
    assert text.returncode == 0
    assert "land.closeout.apply" in text.stdout
    assert "--no-apply" not in text.stdout

    every = run_ethos_process("--help", "--json")
    one = run_ethos_process("land", "--help", "--json")

    assert (every.returncode, one.returncode) == (0, 0)
    payload = json.loads(every.stdout)
    assert (payload["command"], payload["state"]) == ("help", "described")
    assert "bound" not in payload
    assert len(every.stdout.encode()) <= PAYLOAD_BUDGETS["help"]
    operations = [
        item["id"] for entry in payload["data"]["commands"] for item in entry["operations"]
    ]
    assert len(operations) == 29
    assert [entry["name"] for entry in json.loads(one.stdout)["data"]["commands"]] == ["land"]


def test_every_transport_refuses_the_same_request_alike(tmp_path) -> None:
    """The CLI, the SDK and the MCP tool refuse a receipt apply naming a peer, before any read."""
    argv = (
        *("publish", "--receipt", "request.json", "--receipt-sha256", "0" * 64),
        *("--peer", "github", "--apply", "--authorize", "--expect-head", "a" * 40),
    )
    completed = run_ethos_raw(*argv, "--root", str(tmp_path), "--json")
    assert completed.returncode == 2
    refused = json.loads(completed.stdout)["required_gaps"]
    assert refused == ["command_field_refused:peer_ids"]
    assert list(publish_repository(tmp_path, peer_ids=("github",), **_RECEIPT).required_gaps) == (
        refused
    )

    async def through_mcp() -> dict[str, object]:
        async with Client(create_server(tmp_path)) as client:
            result = await client.call_tool("publish", _RECEIPT | {"peer_ids": ["github"]})
            return dict(result.structured_content or {})

    assert asyncio.run(through_mcp())["required_gaps"] == refused
    proof = run_ethos_raw("prove", "--readiness", "--root", str(tmp_path), "--json")
    assert proof.returncode == 2
    assert list(prove_repository(tmp_path, ProofRequest(readiness=True)).required_gaps) == [
        "command_operation_unmatched:prove"
    ]
    assert json.loads(proof.stdout)["required_gaps"] == ["command_operation_unmatched:prove"]
