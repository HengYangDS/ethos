"""No-compatibility-residue quality command registration."""

from __future__ import annotations

from ethos.repository.policy.no_compat.core import no_compat_report
from ethos.surface.cli.quality.reporting import ReportCommandSpec
from ethos.surface.cli.quality.reporting import declared_report_handler
from ethos.surface.cli.quality.reporting import module_report

_MODULE = __name__


def _no_compat_report(root):
    return no_compat_report(root)


NO_COMPAT_COMMAND = ReportCommandSpec(
    command="quality no-compat",
    report=module_report(globals(), "_no_compat_report"),
)

no_compat = declared_report_handler(
    module_name=_MODULE,
    function_name="no_compat",
    spec_name="NO_COMPAT_COMMAND",
    spec=NO_COMPAT_COMMAND,
)
