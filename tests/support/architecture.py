"""Materialize isolated executable fixtures for architecture tests."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping


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


def declare_reference_package(root: Path, *, entry_point: str = "") -> None:
    """Declare package ownership, including Cyclopts only for command surfaces."""
    metadata = '[project]\nname = "example"\nversion = "1"\n'
    if entry_point:
        metadata += (
            f'dependencies = ["cyclopts"]\n\n[project.scripts]\nethos = "{entry_point}:main"\n'
        )
    write_reference_source(root, "pyproject.toml", metadata)


def projection_quality_fixture(
    source_ids: tuple[str, ...], invariants: tuple[str, ...] = ()
) -> dict:
    """Reuse the declared review contract while giving a synthetic graph its own scope."""
    owner = (
        Path(__file__).resolve().parents[2]
        / "system/projections/terminal-architecture/quality-contract.json"
    )
    quality = json.loads(owner.read_text())
    assurance = quality["assurance"]
    family = deepcopy(next(iter(assurance["semantic_families"].values())))
    family["invariants"] = list(invariants)
    assurance["semantic_families"] = {"fixture": family} if invariants else {}

    def select_sources(value: object) -> None:
        if isinstance(value, dict):
            if "source_ids" in value:
                value["source_ids"] = list(source_ids)
            for child in value.values():
                select_sources(child)
        elif isinstance(value, list):
            for child in value:
                select_sources(child)

    select_sources(assurance)
    assurance["principle_review"]["source_sections"] = {
        identity: ["Fixture assertion"] for identity in source_ids
    }
    return quality
