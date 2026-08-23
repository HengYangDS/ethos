"""Generated-artifact gate observation adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

from ethos.adapters.repo.git import run_git
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.repository.policy.artifacts import generated_artifact_topology_report

if TYPE_CHECKING:
    from pathlib import Path

_ROOT_TEST_RESIDUE_FILENAMES = frozenset({".coverage", "coverage.xml", "junit.xml"})
_ROOT_TEST_RESIDUE_PREFIXES = (".coverage.",)


def generated_artifact_gate_report(root: Path) -> dict[str, Any]:
    """Observe Git classifications, then apply generated-artifact policy."""
    declaration = load_generated_artifact_topology_declaration(
        root / "system/policies/generated-artifact-topology.toml"
    )
    ignored = frozenset(
        name for name in (*_ROOT_TEST_RESIDUE_FILENAMES,) if _ignored_untracked(root, name)
    ) | frozenset(
        path.name
        for path in root.iterdir()
        if path.is_file()
        and path.name.startswith(_ROOT_TEST_RESIDUE_PREFIXES)
        and _ignored_untracked(root, path.name)
    )
    homes = tuple(
        home.rstrip("/")
        for lifecycle in declaration.lifecycle_class
        if not lifecycle.tracked
        for home in lifecycle.homes
    )
    completed = _git(root, "ls-files", "--", *homes)
    tracked = tuple(path for path in completed.stdout.splitlines() if path)
    return generated_artifact_topology_report(
        root,
        ignored_local_paths=ignored,
        tracked_untracked_paths=tracked,
    )


def _ignored_untracked(root: Path, relative: str) -> bool:
    return (
        _git(root, "check-ignore", "--quiet", "--", relative).returncode == 0
        and _git(root, "ls-files", "--error-unmatch", "--", relative).returncode != 0
    )


def _git(root: Path, *args: str):
    return run_git(root, *args, check=False, observation=True)
