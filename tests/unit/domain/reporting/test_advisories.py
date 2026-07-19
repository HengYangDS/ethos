from __future__ import annotations

from ethos.domain.reporting.gaps import advisory_gaps


def test_quality_floor_advisories_are_visible_without_becoming_required_gaps() -> None:
    quality_floor = {
        "gates": {
            "source-budget": {
                "advisory_gaps": ["source_budget_campaign_growth_overage:global_total:12>10"]
            }
        }
    }

    assert advisory_gaps(
        *quality_floor["gates"].values(),
    ) == ("source_budget_campaign_growth_overage:global_total:12>10",)
