"""Quality boundary command registrations."""

from __future__ import annotations

from ethos.repository.policy.boundary.product import contributor_policy_report
from ethos.repository.policy.boundary.product import product_boundary_report
from ethos.surface.cli.quality.reporting import ReportCommandSpec
from ethos.surface.cli.quality.reporting import constant_actions
from ethos.surface.cli.quality.reporting import declared_report_handler
from ethos.surface.cli.quality.reporting import module_report

_MODULE = __name__


def _product_boundary_report(root):
    return product_boundary_report(root)


def _contributor_policy_report(root):
    return contributor_policy_report(root)


PRODUCT_BOUNDARY_COMMAND = ReportCommandSpec(
    command="quality product-boundary",
    report=module_report(globals(), "_product_boundary_report"),
    next_actions=constant_actions(
        "neutralize product and release-visible historical surfaces; keep "
        "private provenance in adopter repositories or ignored local state"
    ),
)
CONTRIBUTOR_POLICY_COMMAND = ReportCommandSpec(
    command="quality contributor-policy",
    report=module_report(globals(), "_contributor_policy_report"),
    next_actions=constant_actions("declare role-based humans, teams, and automation identities"),
)

product_boundary = declared_report_handler(
    module_name=_MODULE,
    function_name="product_boundary",
    spec_name="PRODUCT_BOUNDARY_COMMAND",
    spec=PRODUCT_BOUNDARY_COMMAND,
)
contributor_policy = declared_report_handler(
    module_name=_MODULE,
    function_name="contributor_policy",
    spec_name="CONTRIBUTOR_POLICY_COMMAND",
    spec=CONTRIBUTOR_POLICY_COMMAND,
)
