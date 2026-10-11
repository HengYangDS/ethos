"""Context disposal preserves only the lifetime and state its actual protocol owns."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@pytest.mark.parametrize(
    ("setup", "manager", "body", "unknown"),
    [
        ("", "tempfile.TemporaryDirectory(prefix='probe-')", "pass", False),
        ("from tempfile import TemporaryDirectory as temp\n", "temp()", "pass", False),
        ("", "tempfile.TemporaryDirectory()", "return state", False),
        ("", "tempfile.TemporaryDirectory(prefix=thing.prefix)", "pass", True),
        ("", "tempfile.TemporaryDirectory('a', suffix='b')", "pass", True),
        ("", "thing.context()", "pass", True),
        ("", "tempfile.TemporaryDirectory() if flag else thing.context()", "pass", True),
        (
            "tempfile.TemporaryDirectory = thing.context\n",
            "tempfile.TemporaryDirectory()",
            "pass",
            True,
        ),
        (
            "tempfile.TemporaryDirectory.__exit__ = thing.exit\n",
            "tempfile.TemporaryDirectory()",
            "pass",
            True,
        ),
        ("", "tempfile.TemporaryDirectory()", "thing.mutate(state)", True),
    ],
    ids=[
        "native",
        "alias",
        "return",
        "opaque-input",
        "invalid-binding",
        "opaque",
        "mixed",
        "rebound",
        "replaced-exit",
        "body-mutation",
    ],
)
def test_context_exit_preserves_only_unexposed_local_state(
    setup: str, manager: str, body: str, *, unknown: bool
) -> None:
    """A native cleanup cannot mutate an unexposed local; opaque protocols stay unknown."""
    source = (
        "import subprocess, tempfile, thing\n"
        f"{setup}def prepare():\n"
        f"    with {manager}:\n"
        "        state = {'command': 'context_probe'}\n"
        f"        {body}\n"
        "    return state\n"
        "subprocess.run([prepare()['command']])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert bool([item for item in observation.uncertainties if item.state == "unknown"]) is unknown
    assert unknown or observation.executables == {"context_probe"}


def test_native_context_enter_returns_text_without_inventing_root_content() -> None:
    """An entered directory is native text, not a claimed path or observed root string."""
    source = (
        "import subprocess, tempfile\nfrom pathlib import Path\n"
        "with tempfile.TemporaryDirectory() as root:\n"
        "    subprocess.run([str(Path(root) / 'context_probe')])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.executables == {"context_probe"}
    assert not observation.uncertainties


@pytest.mark.parametrize("method", ["__init__", "_rmtree", "_cleanup"])
@pytest.mark.parametrize("after_read", [False, True], ids=["initial", "cached"])
def test_context_protocol_replacement_cannot_preserve_captured_state(
    method: str, *, after_read: bool
) -> None:
    """A changed dispatch dependency invalidates its captured state and any summary reuse."""
    source = (
        "import subprocess, tempfile\n"
        "state = {'command': 'before_probe'}\n"
        "def replacement(*args, **kwargs):\n"
        "    state['command'] = 'after_probe'\n"
        "def prepare():\n"
        "    with tempfile.TemporaryDirectory():\n"
        "        pass\n"
        "    return state['command']\n"
    )
    if after_read:
        source += "subprocess.run([prepare()])\n"
    source += f"tempfile.TemporaryDirectory.{method} = replacement\n"
    source += "subprocess.run([prepare()])\n"
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert any(item.state == "unknown" for item in observation.uncertainties), observation
