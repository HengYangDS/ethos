# ruff: noqa: INP001, E501, S102
"""Checkout loader; the sdist replaces this file with the packaged implementation."""

# fmt: off
exec(__import__("pathlib").Path(__file__).parents[2].joinpath("tools", "ci", "ethos_core_build_hook.py").read_text())
# fmt: on
