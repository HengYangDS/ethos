# ruff: noqa: INP001, E402, E501, F401, E702, I001
"""Checkout hook; the sdist substitutes the packaged implementation."""

# fmt: off
import sys; from pathlib import Path
sys.path[:0] = [str(Path(__file__).parents[2] / "tools")]; from ci.ethos_core_build_hook import CustomBuildHook
# fmt: on
