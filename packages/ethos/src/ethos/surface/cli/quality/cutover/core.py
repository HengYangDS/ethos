"""No-compatibility-residue quality command registration."""

from __future__ import annotations

from ethos.surface.cli.quality.reporting import declared_report_handler

no_compat = declared_report_handler(
    module_name=__name__,
    function_name="no_compat",
)
