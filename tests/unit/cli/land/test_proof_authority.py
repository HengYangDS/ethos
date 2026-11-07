"""Landing binds the intent that its admitted proof carries."""

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.mutation.landing as landing_mutation
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import prepared_work_lane
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from tests.support.governed_repository import WorkLaneFixture

HOLDER = "agent:test:case:agent-test"


def archive(root: Path, change: str) -> str:
    """Prove the completed Change at HEAD, archive it and return the archived HEAD."""
    head = git(root, "rev-parse", "HEAD")
    seed_executed_proof(root, head)
    archived = run_ethos_blocked(
        *("lane", "archive-change", "--change", change, "--expect-head", head, "--apply", "--json"),
        cwd=root,
    )
    assert archived["required_gaps"] == ["proof_not_proven"], archived
    return git(root, "rev-parse", "HEAD")


def declare_second_change(root: Path) -> None:
    """Declare one more complete Change that adds its own requirement."""
    archived = next((root / "openspec/changes/archive").glob("*-fixture-change"))
    carrier = root / "openspec/changes/second-change"
    (carrier / "specs/contracts").mkdir(parents=True)
    for name in ("proposal.md", "design.md"):
        (carrier / name).write_text((archived / name).read_text(encoding="utf-8"), encoding="utf-8")
    (carrier / "specs/contracts/spec.md").write_text(
        "## ADDED Requirements\n\n"
        "### Requirement: Second fixture change\n\n"
        "A second official Change SHALL archive its own requirement.\n\n"
        "#### Scenario: Second fixture change is archived\n\n"
        "- **WHEN** the lane archives the second Change\n"
        "- **THEN** its requirement joins the accepted specs\n",
        encoding="utf-8",
    )
    (carrier / "tasks.md").write_text("- [x] Exercise the second fixture\n", encoding="utf-8")
    commit_fixture(root, "docs(openspec): declare second-change")


def first_change_proved_after_two_archives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[WorkLaneFixture, str]:
    """Archive the lane's two Changes, then prove the first one at the final HEAD."""
    fixture = prepared_work_lane(tmp_path)
    monkeypatch.setenv("ETHOS_ACTOR", HOLDER)
    commit_fixture_file(fixture.worktree, "notes/feature.md", "# feature\n", "test: feature work")
    commit_fixture_file(
        fixture.worktree,
        "openspec/changes/fixture-change/tasks.md",
        "- [x] Exercise fixture lifecycle\n",
        "test: complete fixture change",
    )
    archive(fixture.worktree, "fixture-change")
    declare_second_change(fixture.worktree)
    head = archive(fixture.worktree, "second-change")
    monkeypatch.setenv("ETHOS_CHANGE", "fixture-change")
    seed_executed_proof(fixture.worktree, head)
    monkeypatch.delenv("ETHOS_CHANGE")
    return fixture, head


def land(root: Path, head: str, *, blocked: bool = False) -> dict[str, Any]:
    arguments = ("land", "--apply", "--authorize", "--expect-head", head, "--json")
    return (run_ethos_blocked if blocked else run_ethos)(*arguments, cwd=root)


def test_a_proof_of_an_earlier_archived_change_lands(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, head = first_change_proved_after_two_archives(tmp_path, monkeypatch)

    landed = land(fixture.worktree, head)

    assert (landed["verdict"], landed["state"], landed["required_gaps"]) == (
        "pass",
        "candidate_validated",
        [],
    )
    plan = landed["data"]["candidate_update"]["attestation"]["payload"]["body"]["plan"]
    assert plan["commitment"]["id"] == "change:fixture-change"
    assert git(fixture.candidate, "rev-parse", "HEAD") == head


def test_an_encoding_not_admissible_at_the_head_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, head = first_change_proved_after_two_archives(tmp_path, monkeypatch)
    before = git(fixture.candidate, "rev-parse", "HEAD")
    monkeypatch.setattr(
        landing_mutation, "admissible_openspec_commitments", lambda *_args, **_kwargs: ()
    )

    refused = land(fixture.worktree, head, blocked=True)

    assert refused["required_gaps"] == ["proof_attestation_authority_binding_mismatch"]
    assert git(fixture.candidate, "rev-parse", "HEAD") == before


def test_an_explicit_change_selects_the_landed_intent_over_the_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The option overrides an inherited selection that names the unproved Change."""
    fixture, head = first_change_proved_after_two_archives(tmp_path, monkeypatch)
    monkeypatch.setenv("ETHOS_CHANGE", "second-change")
    preview = ("land", "--expect-head", head, "--json")

    inherited = run_ethos(*preview, cwd=fixture.worktree)
    assert inherited["required_gaps"] == ["proof_not_proven"]
    selected = run_ethos(*preview, "--change", "fixture-change", cwd=fixture.worktree)

    assert (selected["verdict"], selected["required_gaps"]) == ("pass", [])
