"""Checkout loader; the sdist replaces this file with the packaged implementation."""

# fmt: off
exec(open(__file__.replace("build_hook.py", "../../tools/packaging/ethos_core_build_hook.py"), encoding="utf-8").read())
# fmt: on
