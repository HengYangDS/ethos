"""Materialize isolated executable fixtures for architecture tests."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path


def isolated_path(tmp_path: Path, executables: Mapping[str, str]) -> dict[str, str]:
    """Materialize executable fixtures on a minimal cross-platform PATH."""
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    for name, body in executables.items():
        path = fake_bin / name
        path.write_text(body, encoding="utf-8")
        path.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = os.pathsep.join((str(fake_bin), "/bin", "/usr/bin"))
    return env


def write_reference_source(root: Path, relative: str, content: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")


def declare_reference_surface(
    root: Path, name: str = "runtime", carrier: str = "src/example"
) -> None:
    """Declare a selected native surface while preserving its exact scope."""
    write_reference_source(
        root,
        "system/surfaces.toml",
        'schema = "system/schemas/contracts/surfaces.schema.json"\n'
        f'[[surface]]\nname = "{name}"\ncarrier = "{carrier}"\n',
    )


def declare_reference_package(root: Path, *, entry_point: str = "") -> None:
    """Declare package ownership, including Cyclopts only for command surfaces."""
    metadata = '[project]\nname = "example"\nversion = "1"\n'
    if entry_point:
        metadata += (
            f'dependencies = ["cyclopts"]\n\n[project.scripts]\nethos = "{entry_point}:main"\n'
        )
    write_reference_source(root, "pyproject.toml", metadata)


def architecture_projection_fixture(root: Path, title: str = "Example") -> tuple[Path, Path, Path]:
    """Declare a literal source/output pair without using the production renderer."""
    declaration = root / ".config/checks/architecture-projection/policy.toml"
    declaration.parent.mkdir(parents=True, exist_ok=True)
    declaration.write_text(
        'schema = "ethos-architecture-projection-v1"\n[[projection]]\n'
        'id = "view"\nsource = "docs/model.c4"\noutput = "docs/diagram.mmd"\n'
        'kind = "likec4-to-mermaid"\n',
    )
    model, output = root / "docs/model.c4", root / "docs/diagram.mmd"
    model.parent.mkdir(exist_ok=True)
    model.write_text(f'system Example "{title}"\n')
    output.write_text(
        "%% Generated from docs/model.c4. Do not edit by hand.\n"
        f'flowchart LR\n  Example["{title}"]\n',
    )
    return declaration, model, output
