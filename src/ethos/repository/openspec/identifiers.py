"""Canonical OpenSpec active Change identifier grammar."""

from __future__ import annotations

import re

LOGICAL_CHANGE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
TEMPORAL_SUFFIX_PATTERN = re.compile(r"-20\d{6}$")


def logical_change_identifier_issue(identifier: str) -> str:
    """Return the stable validation issue for one logical Change ID."""
    if not LOGICAL_CHANGE_ID_PATTERN.fullmatch(identifier):
        return "invalid"
    if TEMPORAL_SUFFIX_PATTERN.search(identifier):
        return "temporal_suffix"
    return ""
