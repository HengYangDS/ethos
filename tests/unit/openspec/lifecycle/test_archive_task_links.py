"""Final task completion stays admissible after archive relocation rewrites its links."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.openspec.archive_projection import refresh_archive_projections
from ethos.adapters.openspec.lifecycle.archive_transition import archive_postimage
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path

CHANGE = "task-links"
ACTIVE = f"openspec/changes/{CHANGE}"
ARCHIVE = f"openspec/changes/archive/2026-10-16-{CHANGE}"
TASKS = (
    "- [x] 1.1 Prepare the [contract](../../../docs/target.md#scope)\n"
    "- [ ] 1.2 Confirm the [result](design.md#result)\n"
)


def _archived(tmp_path: Path) -> tuple[Path, str]:
    """Commit an active Change whose tasks link outside it, then stage the native archive move."""
    repo, _candidate = init_repo_with_candidate(tmp_path)
    for relative, content in {
        "docs/target.md": "# Target\n",
        f"{ACTIVE}/.openspec.yaml": "schema: spec-driven\n",
        f"{ACTIVE}/proposal.md": "## Why\n\nKeep task links valid after archive.\n",
        f"{ACTIVE}/design.md": "## Result\n\nArchive the selected intent.\n",
        f"{ACTIVE}/tasks.md": TASKS,
        f"{ACTIVE}/specs/contracts/spec.md": "## ADDED Requirements\n",
    }.items():
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    head = commit_fixture(repo, "declare linked tasks before archive")
    target = repo / ARCHIVE
    target.parent.mkdir(parents=True, exist_ok=True)
    (repo / ACTIVE).rename(target)
    (target / "tasks.md").write_text(TASKS.replace("- [ ]", "- [x]"), encoding="utf-8")
    return repo, head


def test_completed_tasks_with_relocated_links_are_admitted_on_every_pass(tmp_path: Path) -> None:
    """The native postimage and ETHOS's own relocated postimage both admit the completion."""
    repo, head = _archived(tmp_path)

    assert archive_postimage(repo, head=head, change=CHANGE) is not None
    refresh_archive_projections(repo, source_head=head)
    relocated = (repo / ARCHIVE / "tasks.md").read_text(encoding="utf-8")

    assert "(../../../../docs/target.md#scope)" in relocated
    assert "- [ ]" not in relocated
    result = archive_postimage(repo, head=head, change=CHANGE)
    assert result is not None
    assert result.scope is not None
    assert result.scope["verdict"] == "pass"
    assert git(repo, "rev-parse", "HEAD") == head


@pytest.mark.parametrize(
    "tamper",
    [
        lambda text: text.replace("Prepare the", "Rewrite the"),
        lambda text: text.replace("docs/target.md#scope", "docs/target.md#other"),
        lambda text: text + "- [x] 1.3 Insert unreviewed work\n",
    ],
)
def test_relocated_tasks_still_refuse_body_and_task_changes(tmp_path: Path, tamper) -> None:
    """Only the exact native link relocation and final checkboxes may differ from the source."""
    repo, head = _archived(tmp_path)
    refresh_archive_projections(repo, source_head=head)
    tasks = repo / ARCHIVE / "tasks.md"
    tasks.write_text(tamper(tasks.read_text(encoding="utf-8")), encoding="utf-8")

    with pytest.raises(ValueError, match="archive_reference_"):
        archive_postimage(repo, head=head, change=CHANGE)
