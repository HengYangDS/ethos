"""Observe Python references through import binding, lexical scope and program point."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.references.closure import repository_semantic_closure
from ethos.repository.policy.references.observation import product_references_from_files
from tests.support.architecture import declare_reference_package
from tests.support.architecture import declare_reference_surface
from tests.support.architecture import write_reference_source

if TYPE_CHECKING:
    from pathlib import Path

MODULE = "src/example/module.py"


def _gaps(root: Path, **sources: str) -> list[str]:
    declare_reference_surface(root)
    declare_reference_package(root)
    for name, source in sources.items():
        write_reference_source(root, f"src/example/{name}.py", source)
    return repository_semantic_closure(root)["required_gaps"]


def _orphan(kind: str, identity: str, source: str = MODULE) -> str:
    return f"semantic_consumer_orphan:{kind}:{identity}:{source}"


@pytest.mark.parametrize(
    ("source", "kind", "identity"),
    [
        ("import subprocess as sp\nsp.run(['rogue-tool'])", "executable", "rogue-tool"),
        ("from subprocess import run\nrun(['rogue-tool'])", "executable", "rogue-tool"),
        (
            "import subprocess\nRUN = subprocess.run\nRUN(['rogue-tool'])",
            "executable",
            "rogue-tool",
        ),
        (
            "import subprocess\nARGV = ('rogue-tool', '-x')\nsubprocess.run(ARGV)",
            "executable",
            "rogue-tool",
        ),
        ("import os as o\no.getenv('ROGUE_HOME')", "value", "ROGUE_HOME"),
        ("from os import getenv\ngetenv('ROGUE_HOME')", "value", "ROGUE_HOME"),
        ("from os import environ\nenviron['ROGUE_HOME']", "value", "ROGUE_HOME"),
    ],
    ids=[
        "module-alias",
        "from-import",
        "callee-name",
        "argv-name",
        "os-alias",
        "getenv",
        "environ",
    ],
)
def test_aliases_preserve_a_real_consumer(
    tmp_path: Path, source: str, kind: str, identity: str
) -> None:
    assert _gaps(tmp_path, module=source) == [_orphan(kind, identity)]


@pytest.mark.parametrize(
    "source",
    [
        (
            "import subprocess\n\n\ndef check():\n    subprocess = object()\n"
            "    return subprocess.run(['rogue-tool'])"
        ),
        "import subprocess\n\n\ndef check(subprocess):\n    return subprocess.run(['rogue-tool'])",
        "TOOL_COMMAND = ('rogue-tool', 'run')\nCHECK_CMD = ['rogue-tool']",
        "import os\nos.environ['ROGUE_HOME'] = 'written, not read'",
    ],
    ids=["local", "parameter", "name-spelling", "environment-write"],
)
def test_shadowing_cannot_invent_an_effect(tmp_path: Path, source: str) -> None:
    assert _gaps(tmp_path, module=source) == []


def test_the_value_belongs_to_its_scope_and_program_point(tmp_path: Path) -> None:
    source = """
import os

NAME = "EARLY_HOME"
os.getenv(NAME)
NAME = "LATE_HOME"


def read():
    NAME = "LOCAL_HOME"
    return os.getenv(NAME)
"""
    assert _gaps(tmp_path, module=source) == [
        _orphan("value", "EARLY_HOME"),
        _orphan("value", "LOCAL_HOME"),
    ]


def test_a_function_reads_every_module_binding(tmp_path: Path) -> None:
    source = """
import os

NAME = "FIRST_HOME"


def read():
    return os.getenv(NAME)


NAME = "SECOND_HOME"
"""
    assert _gaps(tmp_path, module=source) == [
        _orphan("value", "FIRST_HOME"),
        _orphan("value", "SECOND_HOME"),
    ]


def test_dynamic_semantics_remain_bounded_unknown(tmp_path: Path) -> None:
    dynamic = "src/example/dynamic.py"
    gaps = _gaps(
        tmp_path,
        dynamic=(
            "import subprocess\n\n\ndef call(name):\n"
            "    run = getattr(subprocess, name)\n    return run(['x'])"
        ),
        mirror="import os\nHOST = {name: getattr(os, name) for name in dir(os)}",
        module="import subprocess\nsubprocess.run(['rogue-tool'])",
    )
    assert gaps == [
        _orphan("executable", "rogue-tool"),
        f"semantic_carrier_unknown:reference:{dynamic}:{dynamic}",
    ]


def test_a_caller_supplied_value_is_not_a_consumer_here() -> None:
    source = "import subprocess\n\n\ndef run(command):\n    return subprocess.run(command)\n"
    observed = product_references_from_files({MODULE: source})
    assert observed.references["executable"] == set()
    assert observed.coverage == "evaluated"


CONSUMER = """
import os

DOCKER_GATE_ENV = "IN_DOCKER_GATE"
os.environ.get(DOCKER_GATE_ENV)
os.getenv("UNDECLARED_HOME")
"""


@pytest.mark.parametrize(
    ("path", "declaration"),
    [
        (
            "tools/ci/Dockerfile",
            "FROM base\nRUN apt-get install -y rogue-tool\nENV IN_DOCKER_GATE=1",
        ),
        ("tools/ci/gate.Dockerfile", "FROM base\nARG IN_DOCKER_GATE \\\n    OTHER=2"),
        ("tools/ci/Containerfile", "FROM base\nENV IN_DOCKER_GATE 1"),
        (
            "tools/ci/docker-compose.local-ci.yml",
            "services:\n  gate:\n    build: .\n    environment:\n      IN_DOCKER_GATE: '1'",
        ),
        (
            "tools/ci/compose.yaml",
            "services:\n  gate:\n    build: .\n    environment:\n      - IN_DOCKER_GATE=1",
        ),
    ],
    ids=["dockerfile-env", "dockerfile-arg", "containerfile-legacy", "compose-map", "compose-list"],
)
def test_a_container_environment_declares_its_values(
    tmp_path: Path, path: str, declaration: str
) -> None:
    write_reference_source(tmp_path, path, declaration)
    assert _gaps(tmp_path, module=CONSUMER) == [_orphan("value", "UNDECLARED_HOME")]
