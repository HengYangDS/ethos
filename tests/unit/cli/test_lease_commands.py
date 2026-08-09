"""Public CLI projection for generation-bound Lease operations."""

from __future__ import annotations

import json
from datetime import UTC
from datetime import datetime

import pytest

import ethos.surface.cli.lane.lease as lease_cli
from ethos.contracts.semantic import Attestation
from ethos.surface.cli.lane.lease import TakeoverOptions
from ethos.surface.cli.lane.lease import emit_lease_result
from ethos.surface.cli.lane.lease import lane_lease_takeover
from tests.support.ethos_cli_runner import run_ethos_raw


@pytest.mark.parametrize(
    ("operation", "command"), [("renew", "lane lease renew"), ("resume", "lane lease resume")]
)
def test_declared_lease_cli_compiles_exact_request_and_emits_json(
    tmp_path, monkeypatch: pytest.MonkeyPatch, operation: str, command: str
) -> None:
    captured = {}

    def execute(*, root, request):
        captured.update(root=root, request=request)
        return {
            "verdict": "pass",
            "state": "planned",
            "branch": request.branch,
            "lease": {},
            "handoff_offer": {},
            "required_gaps": [],
        }

    monkeypatch.setattr(lease_cli, "execute_lease_operation", execute)
    completed = run_ethos_raw(
        "lane",
        "lease",
        operation,
        "--root",
        tmp_path.as_posix(),
        "--branch",
        "work/example",
        "--holder-ref",
        "agent:test:case:holder",
        "--lease-id",
        "lease:example",
        "--epoch",
        "3",
        "--expect-head",
        "a" * 40,
        "--expires-at",
        "2026-08-10T00:00:00+00:00",
        "--payload-sha256",
        "b" * 64,
        "--json",
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert (payload["command"], payload["verdict"], payload["state"]) == (
        command,
        "pass",
        "planned",
    )
    assert captured["root"] == tmp_path
    assert captured["request"].expected_epoch == 3
    assert captured["request"].operation == operation


@pytest.mark.parametrize(
    "report",
    [
        {
            "verdict": "pass",
            "state": "renewed",
            "branch": "work/example",
            "lease": {"lease_id": "lease:example", "epoch": 2, "holder_ref": "holder"},
            "handoff_offer": {},
            "diagnostics": [{"severity": "info"}, "ignored"],
            "required_gaps": [],
        },
        {
            "verdict": "pass",
            "state": "handoff_offered",
            "branch": "work/example",
            "lease": {},
            "handoff_offer": {"lease_id": "lease:example", "epoch": 2, "holder_ref": "holder"},
            "required_gaps": [],
        },
    ],
)
def test_lease_result_summary_uses_applied_lease_or_offer(monkeypatch, report) -> None:
    emitted = []
    monkeypatch.setattr(lease_cli, "emit", lambda result, **_kwargs: emitted.append(result))

    emit_lease_result("lane lease test", report, json_output=True)

    assert emitted[0].summary == {
        "branch": "work/example",
        "lease_id": "lease:example",
        "epoch": 2,
        "holder_ref": "holder",
    }


def test_takeover_cli_loads_authorization_and_projects_exact_request(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = datetime.now(UTC)
    authorization = Attestation.issue(
        {
            "predicate": "lane-resolution:takeover",
            "verifier": "maintainer:test:case:reviewer",
            "subject": "git:branch:work/example",
            "issued_at": now,
            "verdict": "pass",
            "evidence_refs": ("evidence:test:takeover",),
            "statement": {"authorization": {"test": "cli"}},
        }
    )
    path = tmp_path / "authorization.json"
    path.write_text(authorization.model_dump_json(), encoding="utf-8")
    captured = {}
    monkeypatch.setattr(lease_cli, "resolve_root", lambda root: root)
    monkeypatch.setattr(
        lease_cli,
        "execute_lease_takeover",
        lambda *, root, request: (
            captured.update(root=root, request=request)
            or {
                "verdict": "pass",
                "state": "planned",
                "branch": request.branch,
                "lease": {},
                "required_gaps": [],
            }
        ),
    )
    monkeypatch.setattr(
        lease_cli,
        "emit_lease_result",
        lambda command, report, **kwargs: captured.update(command=command, report=report, **kwargs),
    )
    options = TakeoverOptions(
        apply=False,
        root=tmp_path,
        json_output=True,
        branch="work/example",
        source_holder_ref="agent:test:case:source",
        target_holder_ref="agent:test:case:target",
        lease_id="lease:example",
        epoch=4,
        expect_head="a" * 40,
        expected_tree="b" * 40,
        expected_expires_at="2026-08-10T00:00:00+00:00",
        expected_payload_sha256="c" * 64,
        expected_lane_incarnation_id="lane-incarnation:example",
        expected_dirty_content_sha256="d" * 64,
        source_state="source_lost",
        authorization=path,
    )

    lane_lease_takeover(options)

    assert captured["command"] == "lane lease takeover"
    assert captured["json_output"] is True
    assert captured["request"].authorization == authorization
    assert captured["request"].expected_epoch == 4
