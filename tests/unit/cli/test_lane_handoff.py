from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.surface.cli.lane.handoff as handoff_cli

if TYPE_CHECKING:
    from pathlib import Path


def test_offer_and_accept_delegate_to_declared_lease_operation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[object] = []
    monkeypatch.setattr(handoff_cli, "execute_declared_lease_operation", observed.append)
    offer = SimpleNamespace(command="lane handoff offer")
    accept = SimpleNamespace(command="lane handoff accept")

    handoff_cli.lane_handoff_offer(offer)
    handoff_cli.lane_handoff_accept(accept)

    assert observed == [offer, accept]


@pytest.mark.parametrize("operation", ["export", "import", "revoke"])
def test_handoff_cli_projects_blocked_adapter_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
) -> None:
    report = {
        "verdict": "block",
        "state": "blocked",
        "branch": "work/example",
        "lease": {},
        "required_gaps": ["handoff_failed"],
    }
    captured: dict[str, object] = {}
    monkeypatch.setattr(handoff_cli, "resolve_root", lambda _root: tmp_path)
    monkeypatch.setattr(
        handoff_cli,
        "emit_lease_result",
        lambda command, result, *, json_output: captured.update(
            command=command, result=result, json_output=json_output
        ),
    )
    common = {
        "root": tmp_path,
        "apply": True,
        "json_output": True,
    }
    if operation == "export":
        received: list[object] = []
        monkeypatch.setattr(
            handoff_cli,
            "export_cross_host_handoff",
            lambda request: received.append(request) or report,
        )
        options = SimpleNamespace(
            **common,
            command="lane handoff export",
            branch="work/example",
            holder_ref="agent:test:case:source",
            target_holder_ref="agent:test:case:target",
            lease_id="lease:1",
            epoch=2,
            expected_expires_at="2026-08-10T00:00:00+00:00",
            expected_payload_sha256="a" * 64,
            expect_head="b" * 40,
            context_text="context",
            context_file=tmp_path / "context.md",
            output_root=tmp_path / "packages",
        )
        handoff_cli.lane_handoff_export(options)
        request = received[0]
        assert request.context_file == (tmp_path / "context.md").as_posix()
        assert request.output_root == (tmp_path / "packages").as_posix()
    elif operation == "import":
        received = []
        monkeypatch.setattr(
            handoff_cli,
            "import_cross_host_handoff",
            lambda request: received.append(request) or report,
        )
        options = SimpleNamespace(
            **common,
            command="lane handoff import",
            package=tmp_path / "package",
            target_holder_ref="agent:test:case:target",
        )
        handoff_cli.lane_handoff_import(options)
        request = received[0]
        assert request.package == (tmp_path / "package").as_posix()
    else:
        received = []
        monkeypatch.setattr(
            handoff_cli,
            "revoke_cross_host_source",
            lambda request: received.append(request) or report,
        )
        options = SimpleNamespace(
            **common,
            command="lane handoff revoke-source",
            package=tmp_path / "package",
            acknowledgement=tmp_path / "ack.json",
            holder_ref="agent:test:case:source",
            lease_id="lease:1",
            epoch=2,
            expect_head="b" * 40,
            expected_expires_at="2026-08-10T00:00:00+00:00",
            expected_payload_sha256="a" * 64,
        )
        handoff_cli.lane_handoff_revoke_source(options)
        request = received[0]
        assert request.acknowledgement == (tmp_path / "ack.json").as_posix()

    assert captured == {
        "command": options.command,
        "result": report,
        "json_output": True,
    }
