"""Qualify closed native keyword argument shapes through public source consumers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize(
    "mapping",
    [
        '{"shell": False}',
        '{**{"shell": True}, "shell": False}',
        '({"shell": False} if condition else {})',
    ],
)
def test_public_closure_binds_finite_keyword_expansion(tmp_path: Path, mapping: str) -> None:
    """Closed keyword mappings follow the same native call signature as explicit arguments."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command, **options):\n"
        "        return subprocess.Popen(command, **options)\n"
        "def launch(command, **options):\n"
        "    return Scope().start(command, **options)\n"
        f"options = {mapping}\n"
        'launch(("keyword_method_probe",), **options)\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["verdict"] == "block", report
    assert {item["identity"] for item in report["orphan"]} == {"keyword_method_probe"}, report


def test_public_closure_keeps_open_keyword_expansion_unknown(tmp_path: Path) -> None:
    """An open mapping cannot close a source call by discarding unknown argument channels."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        "class Scope:\n"
        "    def start(self, command, **options):\n"
        "        return subprocess.Popen(command, **options)\n"
        'Scope().start(("keyword_method_probe",), **external_options)\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert report["coverage"] == "unknown", report
    assert report["verdict"] == "unknown", report


def test_public_closure_reads_missing_key_default_in_each_mapping_shape(tmp_path: Path) -> None:
    """A closed optional key selects its native default on the absent branch."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        'options = {"command": "present_key_probe"} if condition else {}\n'
        'command = options.get("command", "missing_key_probe")\n'
        "subprocess.run([command])\n",
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {
        "present_key_probe",
        "missing_key_probe",
    }, report


def test_public_closure_preserves_optional_keyword_override(tmp_path: Path) -> None:
    """A native executable keyword remains separate from the process-visible argv label."""
    declare_reference_surface(tmp_path)
    declare_reference_package(tmp_path)
    write_reference_source(
        tmp_path,
        "src/example/probe.py",
        "import subprocess\n"
        'options = {"executable": "override_probe"} if condition else {}\n'
        'subprocess.run(["argv_probe"], **options)\n',
    )

    report = repository_semantic_closure(tmp_path)

    assert {item["identity"] for item in report["orphan"]} == {
        "override_probe",
        "argv_probe",
    }, report
