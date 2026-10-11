"""Native content transformations preserve representation, not unobserved bytes."""

from __future__ import annotations

import ast

import pytest

from ethos.repository.policy.references.python.flow import PythonReferenceFlow
from ethos.repository.policy.references.python.functions.returns import PythonSourceReturns


@pytest.mark.parametrize(
    "expression",
    [
        "Path('locator').read_bytes().decode('utf-8').removesuffix('\\n')",
        "Path('locator').read_bytes().decode('utf-8').removesuffix('\\n').split('\\n')[0]",
        "Path('locator').read_text().removeprefix('prefix')",
        "Path('locator').read_text().split('\\n')[0]",
        "Path('locator').read_text().split()[0]",
        "'|'.join(Path('locator').read_text().split('\\n'))",
        "'prefix' + Path('locator').read_text()",
        "Path('locator').read_text() + 'suffix'",
        "'|'.join([Path('locator').read_text(), 'suffix'])",
    ],
    ids=[
        "suffix",
        "complete",
        "prefix",
        "split",
        "whitespace",
        "join",
        "left-add",
        "right-add",
        "finite",
    ],
)
def test_native_content_chain_preserves_known_representation(expression: str) -> None:
    """Known native transformations may supply Path components, never fabricated bytes."""
    source = (
        "import subprocess\nfrom pathlib import Path\n"
        f"text = {expression}\nsubprocess.run([str(Path(text) / 'python')])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.executables == {"python"}, observation
    assert not observation.uncertainties, observation


@pytest.mark.parametrize(
    "body",
    [
        "text = Path('locator').read_text().removesuffix(separator)\n",
        "text = Path('locator').read_text().split(separator)[0]\n",
        "text = '|'.join([Path('locator').read_text(), thing.value])\n",
        "text = (Path('locator').read_text() if flag else thing.value).removesuffix('x')\n",
    ],
    ids=["open-suffix", "open-separator", "mixed-elements", "mixed-receiver"],
)
def test_native_content_requires_closed_receiver_and_operands(body: str) -> None:
    """Unknown alternatives cannot borrow the successful native branch's representation."""
    source = (
        "import subprocess\nimport thing\nfrom pathlib import Path\n"
        f"{body}subprocess.run([str(Path(text) / 'python')])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.uncertainties, observation


def test_native_content_cannot_invent_an_executable_identity() -> None:
    """A known text result is not a known command, even after native transformations."""
    source = (
        "import subprocess\nfrom pathlib import Path\n"
        "text = Path('locator').read_text().removesuffix('\\n')\n"
        "subprocess.run([text])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert not observation.executables, observation
    assert observation.uncertainties, observation


@pytest.mark.parametrize(
    "dispatch", ["Path.read_text", "PosixPath.read_text", "Path.open", "io.open"]
)
def test_native_content_requires_current_read_dispatch(dispatch: str) -> None:
    """A replaced producer may change type and effects; its native result cannot be borrowed."""
    source = (
        "import io\nimport subprocess\nimport thing\nfrom pathlib import Path, PosixPath\n"
        f"{dispatch} = thing.read\n"
        "text = Path('locator').read_text().removesuffix('\\n')\n"
        "subprocess.run([str(Path(text) / 'python')])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.uncertainties, observation


def test_native_split_allocations_keep_independent_mutation_custody() -> None:
    """An escaped split list loses custody without corrupting a separate allocation."""
    source = (
        "import subprocess\nimport thing\nfrom pathlib import Path\n"
        "text = Path('locator').read_text()\n"
        "first = text.split('\\n')\nsecond = text.split('\\n')\n"
        "thing.mutate(first)\nsubprocess.run([str(Path(first[0]) / 'python')])\n"
        "subprocess.run([str(Path(second[0]) / 'python')])\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert observation.executables == {"python"}, observation
    assert [(item.line, item.target) for item in observation.uncertainties] == [
        (8, "subprocess.run")
    ], observation


def test_native_allocation_survives_opaque_constructor_alternative() -> None:
    """A possible native record must retain stores before its capabilities escape."""
    source = (
        "import subprocess\nimport thing\n"
        "ctor = subprocess.CompletedProcess if thing.flag else thing.make\n"
        "record = ctor([], 0)\nrecord.stdout = subprocess.run\nthing.consume(record)\n"
    )
    tree = ast.parse(source)
    sources = PythonSourceReturns({"probe.py": source}, {"probe.py": tree}, PythonReferenceFlow)
    observation = PythonReferenceFlow("probe.py", {}, sources=sources).observe(tree, source=source)
    assert any(
        item.target == "subprocess.run" and item.reason == "opaque_capability_escape"
        for item in observation.uncertainties
    ), observation
