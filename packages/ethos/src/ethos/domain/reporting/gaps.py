from __future__ import annotations

from typing import cast

from ethos.domain.reporting.scoring import adopter_quality_floor_report
from ethos_core.normalization.core import string_sequence
from ethos_core.state.invalid import invalid_state_projection


def advisory_gaps(
    audit: dict[str, object],
    claim_report: dict[str, object],
    playbooks: dict[str, object],
    status_payload: dict[str, object] | None = None,
    hosted_observation: dict[str, object] | None = None,
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
        *string_sequence(coordination.get("advisory_gaps"), drop_empty=True),
        *string_sequence(openspec.get("advisory_gaps"), drop_empty=True),
        *string_sequence(claim_report.get("advisory_gaps"), drop_empty=True),
        *string_sequence(playbooks.get("advisory_gaps"), drop_empty=True),
        *string_sequence((hosted_observation or {}).get("advisory_gaps"), drop_empty=True),
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
        if gap.endswith(":evidence.head_unbound") or gap == "evidence.head_unbound":
            actions.extend(
                [
                    "ethos quality claims --json",
                    "ethos quality evidence-freshness --json",
                ]
            )
        if gap.startswith("provider_not_configured:"):
            provider = gap.rsplit(":", 1)[-1].upper()
            actions.append(
                f"ETHOS_HOSTED_{provider}_REPO=<host/owner/repo> "
                "ETHOS_HOSTED_OBSERVATION_EXECUTE=1 "
                "tools/ci/scripts/run-hosted-provider-observation.sh"
            )
        elif gap.startswith(
            (
                "hosted_provider_observation_",
                "provider_tool_unavailable:",
                "provider_observation_failed:",
            )
        ):
            actions.append("tools/ci/scripts/run-hosted-provider-observation.sh")
        elif gap.startswith("source_budget_"):
            actions.append("ethos quality source-budget --json")
    return tuple(dict.fromkeys(actions))


def local_publication_projection(
    required_gaps: tuple[str, ...],
    proof_readiness: dict[str, object],
) -> dict[str, object]:
    """Project local publication state without authorizing a transition."""
    proof_gaps = string_sequence(proof_readiness.get("required_gaps"), drop_empty=True)
    gaps = list(dict.fromkeys((*required_gaps, *proof_gaps)))
    local_ready = not gaps and proof_readiness.get("blocking") is not True
    return {
        "kind": "local_publication_scorecard_projection",
        "state": "local_publish_ready" if local_ready else "blocked",
        "local_ready": local_ready,
        "blocking": not local_ready,
        "required_gaps": gaps,
        "remote_publication_claimed": False,
        "transition_authority": False,
    }


def coordination_risk_gaps(
    audit: dict[str, object],
    status_payload: dict[str, object],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return report-visible blocking and advisory Work Lane coordination risks."""
    coordination = cast("dict[str, object]", status_payload.get("coordination") or {})
    audit_required = tuple(
        gap
        for gap in string_sequence(audit.get("required_gaps"), drop_empty=True)
        if gap.startswith("coordination_gap:")
    )
    status_required = tuple(string_sequence(coordination.get("required_gaps"), drop_empty=True))
    required = tuple(dict.fromkeys((*audit_required, *status_required)))
    required_set = set(required)
    audit_coordination = tuple(string_sequence(audit.get("coordination_gaps"), drop_empty=True))
    status_advisory = tuple(string_sequence(coordination.get("advisory_gaps"), drop_empty=True))
    advisory = tuple(
        dict.fromkeys(
            gap for gap in (*audit_coordination, *status_advisory) if gap not in required_set
        )
    )
    return required, advisory


def gap_layers(
    result_required_gaps: tuple[str, ...],
    parity_gaps: dict[str, object],
    playbooks: dict[str, object],
    advisory: tuple[tuple[str, ...], tuple[str, ...]],
    hard_quality_floor: dict[str, object] | None = None,
    global_compression: dict[str, object] | None = None,
    coordination_required_gaps: tuple[str, ...] = (),
    coordination_advisory_gaps: tuple[str, ...] = (),
) -> dict[str, dict[str, object]]:
    advisory_gaps, advisory_next_actions = advisory
    hard_quality_floor = hard_quality_floor or adopter_quality_floor_report()
    global_compression = global_compression or adopter_quality_floor_report()
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
        "global_compression": _gap_layer(
            scope="global_compression",
            blocking=False,
            ok=bool(global_compression["ok"]),
            gaps=list(cast("list[str]", global_compression["required_gaps"])),
        ),
        "coordination_risk": {
            "scope": "coordination_risk",
            "blocking": bool(coordination_required_gaps),
            "ok": not coordination_required_gaps,
            "required_gaps": list(coordination_required_gaps),
            "advisory_gaps": list(coordination_advisory_gaps),
            "gap_count": len(coordination_required_gaps) + len(coordination_advisory_gaps),
            "invalid_states": invalid_state_projection(
                [*list(coordination_required_gaps), *list(coordination_advisory_gaps)]
            ),
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
