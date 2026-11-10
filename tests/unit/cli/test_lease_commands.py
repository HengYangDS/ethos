"""Lease and handoff operations run one exact request and project the Lease it leaves."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime

import pytest

import ethos.application.lane.lease as lease
from ethos.application.catalog import invoke
from tests.support.semantic import attestation_fixture

_PROOF = {"generation": 3, "expires_at": "2026-08-10T00:00:00+00:00"}
LEASE = _PROOF | {"branch": "work/example", "holder_ref": "agent:test:case:holder"}
_TARGET = {"target_holder_ref": "agent:test:case:target"}
_PACKAGE = {"package": "package", "expect_head": "b" * 40}
# Each handoff, the owner that runs it and the fields it hands that owner unchanged.
_HANDOFFS = {
    "transfer": ("execute_lease_operation", LEASE | _TARGET),
    "export": (
        "export_cross_host_handoff",
        LEASE | _TARGET | {"expect_head": "b" * 40, "context_file": "c.md", "output_root": "out"},
    ),
    "import": ("import_cross_host_handoff", {"package": "package"} | _TARGET),
    "revoke-source": (
        "revoke_cross_host_source",
        _PROOF | _PACKAGE | {"acknowledgement": "ack.json", "holder_ref": LEASE["holder_ref"]},
    ),
}


def _owner(
    monkeypatch: pytest.MonkeyPatch, name: str, report: dict[str, object] | None = None
) -> list[dict[str, object]]:
    """Replace one owner with a recorder of its root and request that returns `report`."""
    calls: list[dict[str, object]] = []
    planned = {"verdict": "pass", "state": "planned", "branch": "work/example", "lease": {}}

    def owner(*args: object, **kwargs: object) -> dict[str, object]:
        calls.append({"root": kwargs.get("root"), "request": kwargs.get("request", *args)})
        return report or planned | {"required_gaps": []}

    monkeypatch.setattr(lease, name, owner)
    return calls


@pytest.mark.parametrize("operation", ["renew", "resume"])
@pytest.mark.parametrize("given", [LEASE, {"generation": 3}])
def test_a_lease_preview_binds_its_coordinates_and_names_its_exact_apply(
    tmp_path, monkeypatch: pytest.MonkeyPatch, operation: str, given: dict[str, object]
) -> None:
    """Given coordinates bind as given and omitted ones are the current Lease's."""
    calls = _owner(monkeypatch, "execute_lease_operation")
    monkeypatch.setattr(lease, "current_lease_coordinates", lambda _root: LEASE | {"branch": "x"})
    result = invoke(f"lane lease {operation}", tmp_path, given | {"branch": "work/example"})

    request = calls[0]["request"]
    assert (calls[0]["root"], request.operation, request.apply) == (tmp_path, operation, False)
    assert {name: getattr(request, name) for name in LEASE} == LEASE
    apply = (
        f"ethos lane lease {operation} --generation 3 --expires-at 2026-08-10T00:00:00+00:00"
        f" --branch work/example --holder-ref agent:test:case:holder"
        f" --root {tmp_path.as_posix()} --apply"
    )
    assert (result.command, result.state, result.next_action) == (
        f"lane lease {operation}",
        "planned",
        apply,
    )


def test_an_apply_without_every_coordinate_refuses_before_any_effect(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The compare-and-swap still needs every coordinate that the caller saw."""
    calls = _owner(monkeypatch, "execute_lease_operation")
    result = invoke("lane lease renew", tmp_path, {"generation": 3, "apply": True})

    assert (result.verdict, result.required_gaps, calls) == (
        "block",
        ("lease_coordinates_required",),
        [],
    )


def test_a_lease_result_summarizes_the_lease_its_transition_left() -> None:
    """A passing transition points at the lane's status and keeps only mapping diagnostics."""
    report = {
        "verdict": "pass",
        "state": "renewed",
        "branch": "work/example",
        "lease": LEASE,
        "diagnostics": [{"severity": "info"}, "ignored"],
        "required_gaps": [],
    }
    result = lease.lease_result("lane lease renew", report)

    assert (result.summary, result.diagnostics, result.to_dict()["data"]) == (
        LEASE,
        ({"severity": "info"},),
        report,
    )
    assert result.next_action == "ethos lane status --json"


def test_a_takeover_loads_the_attestation_that_authorizes_it(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The request carries the parsed Attestation, never its path."""
    authorization = attestation_fixture(
        predicate="lane-resolution:takeover",
        verifier="maintainer:test:case:reviewer",
        subject="git:branch:work/example",
        issued_at=datetime.now(UTC),
        payload_kind="authorization:lane-takeover",
        payload_body={"authorization": {"test": "cli"}},
        evidence_refs=("evidence:test:takeover",),
    )
    path = tmp_path / "authorization.json"
    path.write_text(authorization.canonical_json(), encoding="utf-8")
    calls = _owner(monkeypatch, "execute_lease_takeover")
    source = {"source_holder_ref": "agent:test:case:source", "source_state": "source_lost"}
    fields = _PROOF | _TARGET | source | {"branch": "work/example", "authorization": path}
    result = invoke("lane lease takeover", tmp_path, fields)

    request = calls[0]["request"]
    assert (request.authorization, request.generation, result.command) == (
        authorization,
        3,
        "lane lease takeover",
    )


@pytest.mark.parametrize("operation", sorted(_HANDOFFS))
def test_a_handoff_hands_its_owner_the_exact_request_and_keeps_its_block(
    tmp_path, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    """Each handoff passes every given field unchanged and projects the owner's blocked report."""
    name, fields = _HANDOFFS[operation]
    report = {
        "verdict": "block",
        "state": "blocked",
        "branch": "work/example",
        "lease": {},
        "required_gaps": ["handoff_failed"],
    }
    calls = _owner(monkeypatch, name, report)
    result = invoke(f"lane handoff {operation}", tmp_path, fields | {"apply": True})

    request = calls[0]["request"]
    assert {key: getattr(request, key) for key in fields} == fields
    assert getattr(request, "operation", "transfer") == "transfer"
    assert (request.apply, result.verdict, result.to_dict()["data"], result.next_action) == (
        True,
        "block",
        report,
        "",
    )
