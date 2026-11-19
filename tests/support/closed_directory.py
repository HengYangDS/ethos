"""The mark of a test that needs a directory which its owner cannot search."""

from __future__ import annotations

import os

import pytest

NEEDS_A_CLOSED_DIRECTORY = pytest.mark.skipif(
    os.name == "nt" or not hasattr(os, "geteuid") or os.geteuid() == 0,
    reason="a directory that its owner cannot search needs POSIX modes and no superuser",
)
