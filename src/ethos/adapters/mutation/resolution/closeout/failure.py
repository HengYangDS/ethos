"""Stable closeout-failure classification for lane-resolution transitions."""

from __future__ import annotations


def classify_closeout_failure(error: Exception, fallback: str) -> str:
    """Preserve one stable resolution gap and otherwise use the bounded fallback."""
    message = str(error).strip()
    return message if message.startswith(("lane_resolution_", "lane_closeout_")) else fallback
