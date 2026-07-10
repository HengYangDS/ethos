"""Readiness quality command registrations."""

from __future__ import annotations

from ethos.domain.readiness.enterprise import enterprise_readiness_report
from ethos.repository.policy.governance.kernel import governance_kernel_report
from ethos.surface.cli.quality.reporting import ReportCommandSpec
from ethos.surface.cli.quality.reporting import conditional_actions
from ethos.surface.cli.quality.reporting import declared_report_handler
from ethos.surface.cli.quality.reporting import module_report

_MODULE = __name__


def _enterprise_readiness_report(root):
    return enterprise_readiness_report(root)


def _governance_kernel_report(root):
    return governance_kernel_report(root)


ENTERPRISE_READINESS_COMMAND = ReportCommandSpec(
    command="quality enterprise-readiness",
    report=module_report(globals(), "_enterprise_readiness_report"),
    next_actions=conditional_actions(
        when_blocked=(
            "resolve enterprise-readiness required gaps, then rerun "
            "ethos quality enterprise-readiness --json"
        ),
        when_clean="ethos prove --execute --expect-head $(git rev-parse HEAD) --json",
    ),
)
GOVERNANCE_KERNEL_COMMAND = ReportCommandSpec(
    command="quality governance-kernel",
    report=module_report(globals(), "_governance_kernel_report"),
    next_actions=conditional_actions(
        when_blocked="repair governance kernel, profile/adoption scaffold, and command-plane docs",
        when_clean="ethos quality enterprise-readiness --json",
    ),
)

enterprise_readiness = declared_report_handler(
    module_name=_MODULE,
    function_name="enterprise_readiness",
    spec_name="ENTERPRISE_READINESS_COMMAND",
    spec=ENTERPRISE_READINESS_COMMAND,
)
governance_kernel = declared_report_handler(
    module_name=_MODULE,
    function_name="governance_kernel",
    spec_name="GOVERNANCE_KERNEL_COMMAND",
    spec=GOVERNANCE_KERNEL_COMMAND,
)
