from __future__ import annotations

from ethos.adapters.mutation.resolution.closeout.failure import classify_closeout_failure


def test_classify_closeout_failure_preserves_admitted_gap_or_uses_fallback() -> None:
    fallback = "lane_resolution_fallback"

    assert (
        classify_closeout_failure(ValueError("lane_resolution_preservation_failed"), fallback)
        == "lane_resolution_preservation_failed"
    )
    assert (
        classify_closeout_failure(ValueError("lane_closeout_transition_failed"), fallback)
        == "lane_closeout_transition_failed"
    )
    assert classify_closeout_failure(ValueError("unclassified failure"), fallback) == fallback
