"""A root command runs one catalog operation, or reports its refusal as a result that exits 2."""

import asyncio
import json
import sys
from contextlib import nullcontext

import pytest
from fastmcp import Client

import ethos.application.console as console_module
import ethos.cli as cli
from ethos.application.catalog import Refused
from ethos.application.catalog import select_operation
from ethos.application.proof.operation import prove_repository
from ethos.application.publication.operation import publish_repository
from ethos.contracts.operations.catalog import COMMANDS
from ethos.contracts.operations.prove import ProofRequest
from ethos.result import PAYLOAD_BUDGETS
from ethos.surface.mcp.server import create_server
from tests.support.ethos_cli_runner import run_ethos_process
from tests.support.ethos_cli_runner import run_ethos_raw

_RECORD = "command_usage_invalid:attestation record"
_GROUP = ("attestation record", "attestation query", "attestation release")
_RECEIPT = {
    "receipt": "request.json",
    "receipt_sha256": "0" * 64,
    "apply": True,
    "authorize": True,
    "expect_head": "a" * 40,
}


@pytest.mark.parametrize(
    ("argv", "command", "gap"),
    [
        (("land", "--closeout", "--release"), "land", "command_operation_unmatched:land"),
        (("land", "--tag", "v1"), "land", "command_field_refused:tag"),
        (("land", "--bogus"), "land", "command_usage_invalid:land"),
        (("land", "true"), "land", "command_usage_invalid:land"),
        (("land", "--no-apply"), "land", "command_usage_invalid:land"),
        (("publish", "--apply"), "publish", "command_operation_unmatched:publish"),
        (("adopt", "--create", "--purpose", "p"), "adopt", "formation_root_required"),
        (("attestation", "record", "--input", "x", "--authorize"), "attestation record", _RECORD),
        (("attestation", "bogus"), "attestation", "command_usage_invalid:attestation"),
        (("bogus",), "ethos", "command_usage_invalid:ethos"),
    ],
)
def test_a_refused_request_exits_2_with_its_result_on_stdout(
    tmp_path, argv: tuple[str, ...], command: str, gap: str
) -> None:
    """One schema-3 refusal naming its command path goes to stdout, its human frame to stderr."""
    completed = run_ethos_raw(*argv, "--json", cwd=tmp_path)

    assert completed.returncode == 2, completed.stderr
    assert completed.stderr.startswith(f"{command}: usage_refused")
    payload = json.loads(completed.stdout)
    assert (payload["schema_version"], payload["verdict"]) == (3, "block")
    assert payload["command"] == command
    assert (payload["state"], payload["required_gaps"]) == ("usage_refused", [gap])
    assert payload["next"]["kind"] == "instruction"


_REQUIRING = [
    name
    for name, command in COMMANDS.items()
    if any(info.is_required() for info in command.request.model_fields.values())
]


@pytest.mark.parametrize("name", _REQUIRING)
def test_a_missing_required_field_names_the_full_command_path(tmp_path, name: str) -> None:
    """A usage error names the longest catalog path, in its gap and in the payload's command."""
    payload = json.loads(run_ethos_raw(*name.split(), "--json", cwd=tmp_path).stdout)
    assert payload["command"] == name
    assert payload["required_gaps"] == [f"command_usage_invalid:{name}"]


def test_help_prints_the_catalog_as_text_and_as_one_bounded_result(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Help lists each operation with its flags; `--json` prints the catalog within its budget.

    A group's help lists its own commands in full and its shown nested groups by name.
    """
    text = run_ethos_process("land", "--help")
    assert text.returncode == 0
    assert "land.closeout.apply" in text.stdout
    assert "--no-apply" not in text.stdout
    usage = run_ethos_process("land", "--bogus", "--json")
    assert (usage.returncode, json.loads(usage.stdout)["state"]) == (2, "usage_refused")
    assert "Unknown option: --bogus." in usage.stderr
    monkeypatch.setattr(console_module, "command_scope", lambda **_: nullcontext())
    monkeypatch.setattr(sys, "argv", ["ethos", "land", "--help", "--json", "--root", "/absent"])
    cli.console_main()
    console = json.loads(capsys.readouterr().out)
    assert [entry["name"] for entry in console["data"]["commands"]] == ["land"]

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
    assert [item["name"] for item in payload["data"]["groups"]] == ["attestation", "host"]
    assert [entry["name"] for entry in json.loads(one.stdout)["data"]["commands"]] == ["land"]
    for argv, names in (("attestation",), _GROUP), (("attestation", "query"), _GROUP[1:2]):
        described = json.loads(run_ethos_process(*argv, "--help", "--json").stdout)
        assert [entry["name"] for entry in described["data"]["commands"]] == list(names)
    lane = json.loads(run_ethos_process("lane", "--help", "--json").stdout)
    nested = [item["name"].removeprefix("lane ") for item in lane["data"]["groups"]]
    assert ("bound" in lane, nested) == (False, ["redact", "retire", "lease", "handoff"])


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
    invalid = select_operation("land", {"retag": 5})
    assert isinstance(invalid, Refused)
    assert invalid.result.required_gaps == ("command_usage_invalid:land",)
    proof = run_ethos_raw("prove", "--readiness", "--root", str(tmp_path), "--json")
    assert proof.returncode == 2
    assert list(prove_repository(tmp_path, ProofRequest(readiness=True)).required_gaps) == [
        "command_operation_unmatched:prove"
    ]
    assert json.loads(proof.stdout)["required_gaps"] == ["command_operation_unmatched:prove"]
