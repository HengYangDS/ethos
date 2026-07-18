from __future__ import annotations

from ethos.domain.orient import orientation_packet


def test_orientation_ignores_invalid_temporary_probe_counts() -> None:
    for count in ("not-a-number", True):
        packet = orientation_packet(
            status_payload={
                "root": "/repo",
                "branch": "dev",
                "role": "accepted_root",
                "dirty": True,
                "changed_paths": ["README.md"],
                "dirty_provenance": {
                    "temporary_probes": {"count": count, "paths": [], "truncated": False}
                },
                "foreign_work_lanes": [],
                "coordination": {},
                "runtime_binding": {},
                "landing_readiness": {},
                "closeout_support": {"supported": False},
            }
        )

        assert packet["temporary_probes"]["count"] == 0
        assert packet["capability"]["candidate_action"] == "repair_or_commit_current_changes"
