from __future__ import annotations

from ethos_core.contracts.coordination import CrossHostHandoff
from ethos_core.contracts.coordination import HolderRef


def test_cross_host_handoff_transfers_content_not_source_lease() -> None:
    handoff = CrossHostHandoff(
        source_lane_ref="work/example",
        source_head="a" * 40,
        source_tree="b" * 40,
        target_holder_ref=HolderRef.parse("agent:other:run:two"),
        context_digest="c" * 64,
        dirty_content_sha256="f" * 64,
        dirty_disposition="committed",
        source_lease_id="lease:one",
        source_lease_epoch=3,
        source_lease_expires_at="2026-07-20T00:00:00+00:00",
        source_lease_payload_sha256="e" * 64,
        source_holder_ref=HolderRef.parse("agent:source:run:one"),
        artifacts=({"path": "repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"},),
    )

    payload = handoff.to_payload()
    assert payload["source_head"] == "a" * 40
    assert payload["source_tree"] == "b" * 40
    assert payload["target_holder_ref"] == "agent:other:run:two"
    assert payload["dirty_content_sha256"] == "f" * 64
    assert payload["transfers_source_lease"] is False
    assert payload["destination_creates_local_incarnation"] is True
    assert payload["source_lease_binding"]["epoch"] == 3
    assert payload["source_lease_binding"]["expires_at"] == "2026-07-20T00:00:00+00:00"
    assert payload["source_lease_binding"]["payload_sha256"] == "e" * 64
    assert payload["truth_boundary"] == "content_addressed_context_until_promoted"
    assert CrossHostHandoff.model_fields["source_lease_expires_at"].is_required()
    assert CrossHostHandoff.model_fields["source_lease_payload_sha256"].is_required()
