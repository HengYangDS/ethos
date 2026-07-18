"""Quality boundary command registrations."""

from __future__ import annotations

from ethos.surface.cli.quality.reporting import declared_report_handler

product_boundary = declared_report_handler(
    module_name=__name__,
    function_name="product_boundary",
)
contributor_policy = declared_report_handler(
    module_name=__name__,
    function_name="contributor_policy",
)
