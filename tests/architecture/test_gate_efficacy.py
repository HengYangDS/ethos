"""The credited ledger of gate efficacy: each credited (gate, role) has a passing marked test."""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from tests.support.gate_marks import DESELECTED
from tests.support.gate_marks import ROLES
from tests.support.gate_marks import gate_marks
from tests.support.registries import proof_registry

ROOT = Path(__file__).resolve().parents[2]
# A refusing pair enters only after one recorded mutant of its gate's policy made its refusing test
# fail (see the crediting Change's tasks). The ledger only grows.
CREDITED = frozenset(
    {
        ("commit-ranges", "refusing"),
        ("commit-ranges", "conforming"),
        ("commit-ranges", "fail_closed"),
        ("format-selection", "refusing"),
        ("format-selection", "conforming"),
        ("format-selection", "fail_closed"),
    }
)
_PLANTED = """\
import pytest


@pytest.mark.gate("commit-ranges", "refusing")
def test_skips():
    pytest.skip("nothing judged")


@pytest.mark.gate("commit-ranges", "refusing")
@pytest.mark.xfail(strict=False)
def test_xfails():
    raise AssertionError


@pytest.mark.gate("no-such-gate", "refusing")
def test_unknown_gate():
    pass


@pytest.mark.gate("commit-ranges", "refusing")
def test_proves():
    pass
"""


def test_the_ledger_names_registered_gates_and_roles() -> None:
    assert {gate for gate, _role in CREDITED} <= set(proof_registry())
    assert {role for _gate, role in CREDITED} <= ROLES


def _whole_suite(config: pytest.Config) -> bool:
    """The proof's run: every test path, and nothing deselected, ignored or narrowed to failures."""
    testpaths = {(config.rootpath / path).resolve() for path in config.getini("testpaths")}
    given = {(config.invocation_params.dir / argument).resolve() for argument in config.args}
    return (
        given == testpaths
        and not config.getoption("lf")
        and not config.getoption("ignore")
        and not config.getoption("ignore_glob")
        and not config.stash.get(DESELECTED, 0)
    )


def test_every_credited_pair_has_a_marked_test(request: pytest.FixtureRequest) -> None:
    """On the whole suite, marked pairs equal the ledger: none lost and none unledgered."""
    if not _whole_suite(request.config):
        pytest.skip("judged only on the whole suite, as the proof's test gate runs it")
    marked = {pair for item in request.session.items for pair in gate_marks(item)}

    assert marked == CREDITED


def test_a_marked_test_cannot_skip_and_names_a_registered_gate(tmp_path: Path) -> None:
    """Under two workers, skips, xfails and unknown gates fail; each mark is a report property."""
    (tmp_path / "test_planted.py").write_text(_PLANTED, encoding="utf-8")
    report = tmp_path / "report.xml"
    environment = os.environ | {"PYTHONPATH": os.pathsep.join((str(ROOT), str(ROOT / "src")))}

    completed = subprocess.run(
        (
            *(sys.executable, "-m", "pytest", "-p", "tests.support.gate_marks", "-n", "2"),
            *("-q", "-p", "no:cacheprovider", "--rootdir", str(tmp_path)),
            *("-o", "junit_family=xunit1", f"--junitxml={report}", str(tmp_path)),
        ),
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )

    # The skip and the xfail fail; the unknown gate errors at setup; the proving test passes.
    assert "2 failed, 1 passed" in completed.stdout, completed.stdout + completed.stderr
    assert "1 error" in completed.stdout
    assert "PytestUnknownMarkWarning" not in completed.stdout
    properties = {
        (case.get("name"), prop.get("value"))
        for case in ElementTree.parse(report).getroot().iter("testcase")
        for prop in case.iter("property")
        if prop.get("name") == "ethos.gate"
    }
    assert ("test_proves", "commit-ranges:refusing") in properties
