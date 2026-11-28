"""The hosts ETHOS runs on: macOS and Linux."""

from __future__ import annotations

import platform

from ethos.contracts.outcome import refuse


def require_supported_host() -> None:
    """Refuse a host other than macOS or Linux before an entry observes or changes anything."""
    if (system := platform.system()) not in {"Darwin", "Linux"}:
        refuse(f"host_platform_unsupported:{system}")
