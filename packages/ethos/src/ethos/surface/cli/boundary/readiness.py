"""Readiness quality command registrations."""

from __future__ import annotations

from ethos.surface.cli.quality.reporting import declared_report_handler

enterprise_readiness = declared_report_handler(
    module_name=__name__,
    function_name="enterprise_readiness",
)
governance_kernel = declared_report_handler(
    module_name=__name__,
    function_name="governance_kernel",
)
