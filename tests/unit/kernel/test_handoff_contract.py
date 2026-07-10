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
        dirty_disposition="committed",
        source_lease_id="lease:one",
        source_lease_epoch=3,
        source_holder_ref=HolderRef.parse("agent:source:run:one"),
        artifacts=({"path": "repository.bundle", "sha256": "d" * 64, "kind": "git_bundle"},),
    )

    payload = handoff.to_payload()
    assert payload["source_head"] == "a" * 40
    assert payload["source_tree"] == "b" * 40
    assert payload["target_holder_ref"] == "agent:other:run:two"
    assert payload["transfers_source_lease"] is False
    assert payload["destination_creates_local_incarnation"] is True
    assert payload["source_lease_binding"]["epoch"] == 3
    assert payload["truth_boundary"] == "content_addressed_context_until_promoted"
