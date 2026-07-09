from __future__ import annotations

from typing import cast

from ethos.domain.reporting.scoring import adopter_quality_floor_report
from ethos_core.invalid_states import invalid_state_projection


def advisory_gaps(
    audit: dict[str, object],
    claim_report: dict[str, object],
    playbooks: dict[str, object],
    status_payload: dict[str, object] | None = None,
) -> tuple[str, ...]:
    """Collect non-blocking small signals that should stay visible in report.

    Required gaps remain the blocking transition vocabulary. Advisory gaps are
    early disorder signals: visible to humans and agents, but not proof-closing
    blockers by themselves. Keep the collection explicit so the scorecard does
    not recursively reinterpret arbitrary nested provider payloads as product
    truth.
    """
    openspec = cast("dict[str, object]", audit.get("openspec") or {})
    coordination = cast("dict[str, object]", (status_payload or {}).get("coordination") or {})
    values = [
        *string_list(coordination.get("advisory_gaps")),
        *string_list(openspec.get("advisory_gaps")),
        *string_list(claim_report.get("advisory_gaps")),
        *string_list(playbooks.get("advisory_gaps")),
    ]
    return tuple(dict.fromkeys(values))


def advisory_next_actions(advisory_gaps: tuple[str, ...]) -> tuple[str, ...]:
    """Translate non-blocking advisory signals into bounded repair hints.

    These are not transition requirements and do not authorize mutation from the
    current checkout. They only keep small visible signals actionable for a
    human or agent who chooses to repair the owning branch or surface.
    """
    actions: list[str] = []
    for gap in advisory_gaps:
        parts = gap.split(":")
        if (
            gap
            in {
                "foreign_work_lane_present",
                "unbound_work_lane_ref_present",
            }
            or gap.startswith(
                (
                    "work_lane_missing_lease:",
                    "coordination_gap:",
                )
            )
            or gap == "work_lane_closeout_residue_present"
        ):
            actions.extend(["ethos orient --json", "ethos lane status --json"])
        if len(parts) == 4 and parts[0] == "openspec_protected_branch_active_change_unarchived":
            branch = parts[1]
            role = parts[2]
            change = parts[3]
            actions.extend(
                [
                    f"git ls-tree -r --name-only {branch} -- openspec/changes/{change}",
                    "ethos explain "
                    f"openspec_protected_branch_active_change_unarchived:{branch}:{role}:{change} "
                    "--json",
                ]
            )
    return tuple(dict.fromkeys(actions))


def string_list(value: object) -> list[str]:
    if not isinstance(value, list | tuple):
        return []
    return [str(item) for item in value if str(item)]


def gap_layers(
    result_required_gaps: tuple[str, ...],
    parity_gaps: dict[str, object],
    playbooks: dict[str, object],
    advisory: tuple[tuple[str, ...], tuple[str, ...]],
    hard_quality_floor: dict[str, object] | None = None,
    coordination_gaps: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    advisory_gaps, advisory_next_actions = advisory
    hard_quality_floor = hard_quality_floor or adopter_quality_floor_report()
    return {
        "governance_audit": _gap_layer(
            scope="governance_audit",
            blocking=True,
            ok=not result_required_gaps,
            gaps=list(result_required_gaps),
        ),
        "capability_parity": _gap_layer(
            scope="capability_parity",
            blocking=False,
            ok=bool(parity_gaps["ok"]),
            gaps=list(cast("list[str]", parity_gaps["required_gaps"])),
        ),
        "playbook_projection": {
            **_gap_layer(
                scope="skills-v2",
                blocking=True,
                ok=bool(playbooks["ok"]),
                gaps=list(cast("list[str]", playbooks["required_gaps"])),
            ),
            "advisory_gaps": list(cast("list[object]", playbooks["advisory_gaps"])),
        },
        "hard_quality_floor": _gap_layer(
            scope="hard_quality_floor",
            blocking=True,
            ok=bool(hard_quality_floor["ok"]),
            gaps=list(cast("list[str]", hard_quality_floor["required_gaps"])),
        ),
        "coordination_risk": {
            "scope": "coordination_risk",
            "blocking": False,
            "ok": True,
            "required_gaps": [],
            "advisory_gaps": list(coordination_gaps),
            "gap_count": len(coordination_gaps),
            "invalid_states": invalid_state_projection(list(coordination_gaps)),
        },
        "advisory_signals": {
            "scope": "advisory_signals",
            "blocking": False,
            "ok": True,
            "required_gaps": [],
            "advisory_gaps": list(advisory_gaps),
            "gap_count": len(advisory_gaps),
            "next_actions": list(advisory_next_actions),
            "invalid_states": invalid_state_projection(list(advisory_gaps)),
        },
    }


def _gap_layer(*, scope: str, blocking: bool, ok: bool, gaps: list[str]) -> dict[str, object]:
    return {
        "scope": scope,
        "blocking": blocking,
        "ok": ok,
        "required_gaps": gaps,
        "gap_count": len(gaps),
        "invalid_states": invalid_state_projection(gaps),
    }


def all_invalid_states(
    result_required_gaps: tuple[str, ...],
    parity_gaps: dict[str, object],
    playbooks: dict[str, object],
) -> dict[str, object]:
    return invalid_state_projection(
        [
            *list(result_required_gaps),
            *list(cast("list[str]", parity_gaps["required_gaps"])),
            *list(cast("list[str]", playbooks["required_gaps"])),
        ]
    )


def skills_scorecard(playbooks: dict[str, object]) -> dict[str, object]:
    v2_compliance = cast("dict[str, object]", playbooks["v2_compliance"])
    return {
        "id": "skills-v2",
        "scope": "playbook_projection",
        "mode": playbooks["mode"],
        "ok": bool(playbooks["ok"]),
        "score": v2_compliance["score"],
        "max_score": v2_compliance["max_score"],
        "blocking": True,
        "required_gaps": list(cast("list[object]", playbooks["required_gaps"])),
        "advisory_gaps": list(cast("list[object]", playbooks["advisory_gaps"])),
    }
