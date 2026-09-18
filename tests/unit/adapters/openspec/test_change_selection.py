"""Official entity selection preserves Change identity through archived closeout."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.openspec.cli as official
import ethos.adapters.openspec.commitment as compilation
from ethos.adapters.openspec.commitment import load_openspec_commitment
from ethos.adapters.openspec.selection import artifact_path_change
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_openspec_baseline
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("consumer", ["compilation", "accepted-closeout"])
@pytest.mark.parametrize("existing_capability", [False, True])
def test_same_name_archived_change_keeps_its_exact_acceptance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, consumer: str, *, existing_capability: bool
) -> None:
    """A real official archive cannot let a same-name spec shadow Change evidence."""
    fixture = prepared_work_lane(tmp_path)
    root = fixture.worktree
    change = "contracts" if existing_capability else "new-capability"
    active = root / "openspec/changes" / change
    (root / "openspec/changes/fixture-change").rename(active)
    if not existing_capability:
        (active / "specs/contracts").rename(active / "specs" / change)
        delta = active / "specs" / change / "spec.md"
        delta.write_text(
            "## Purpose\n\nPreserve exact Change identity when archive creates "
            "a same-name capability.\n\n" + delta.read_text()
        )
        proposal = active / "proposal.md"
        proposal.write_text(proposal.read_text().replace("`contracts`", f"`{change}`"))
    (active / "tasks.md").write_text("- [x] Exercise the exact archived lifecycle.\n")
    head = commit_fixture(root, "complete same-name Change")
    accepted = git(fixture.repository, "rev-parse", "HEAD")
    command = official.openspec_base_command()
    assert command is not None
    current = official.run_json(root, command, ("show", change, "--type", "change", "--json"))
    assert current["exit_code"] == 0, current
    assert current["json"]["deltas"]
    expected = load_openspec_commitment(root, change_id=change, tree_ref=head)
    seed_executed_proof(root, head)

    archived = run_ethos(
        "lane",
        "archive-change",
        "--change",
        change,
        "--expect-head",
        head,
        "--apply",
        "--json",
        cwd=root,
    )
    assert archived["verdict"] == "pass", archived
    archived_head = git(root, "rev-parse", "HEAD")
    assert not active.exists()
    assert (root / "openspec/specs" / change / "spec.md").is_file()
    untyped = official.run_json(root, command, ("show", change, "--json"))
    typed = official.run_json(root, command, ("show", change, "--type", "change", "--json"))
    assert untyped["exit_code"] == 0
    assert "requirements" in untyped["json"]
    assert "deltas" not in untyped["json"]
    assert typed["exit_code"] != 0

    if consumer == "compilation":
        projection = Mock(wraps=official.run_json)
        monkeypatch.setattr(official, "run_json", projection)
        restored = load_openspec_commitment(
            root, change_id=change, tree_ref=archived_head, expected_digest=expected.digest()
        )
        assert restored == expected
        projection.assert_not_called()
        with pytest.raises(ValueError, match="commitment_digest_mismatch"):
            load_openspec_commitment(
                root, change_id=change, tree_ref=archived_head, expected_digest="f" * 64
            )
        git(root, "checkout", head, "--", f"openspec/changes/{change}")
        reopened = commit_fixture(root, "reopen same-name Change")
        assert load_openspec_commitment(root, change_id=change, tree_ref=reopened) == expected
        assert projection.call_args.args[2][:1] == ("show",)
        return

    seed_executed_proof(root, archived_head)
    run_ethos("land", "--apply", "--authorize", "--expect-head", archived_head, "--json", cwd=root)
    closed = run_ethos(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted,
        "--candidate-head",
        archived_head,
        "--json",
        cwd=fixture.repository,
    )
    assert closed["verdict"] == "pass", closed
    assert git(fixture.repository, "rev-parse", "HEAD") == archived_head


@pytest.mark.parametrize("change", ["contracts", "missing-change"])
def test_missing_change_without_archive_cannot_select_a_spec(tmp_path: Path, change: str) -> None:
    """A present specification and a wholly absent name both lack Change evidence."""
    root = init_git_repo(tmp_path / "repository")
    adopt_and_commit(root)
    commit_openspec_baseline(root)
    head = git(root, "rev-parse", "HEAD")

    with pytest.raises(ValueError, match=f"openspec_show_failed:{change}"):
        load_openspec_commitment(root, change_id=change, tree_ref=head)


@pytest.mark.parametrize(
    ("payload", "gap"),
    [
        ({"id": "contracts", "requirements": []}, "openspec_acceptance_missing"),
        (
            {"id": "other", "deltas": [{"spec": "contracts", "requirements": []}]},
            "openspec_show_invalid",
        ),
    ],
)
def test_invalid_successful_change_projection_cannot_fall_back_to_history(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: dict, gap: str
) -> None:
    """A malformed successful typed response remains an error, not historical intent."""
    root = init_git_repo(tmp_path / "repository")
    adopt_and_commit(root)
    commit_openspec_baseline(root)

    def show(_root, _command, args):
        assert args == ("show", "contracts", "--type", "change", "--json")
        return {"exit_code": 0, "parse_error": "", "json": payload}

    monkeypatch.setattr(official, "run_json", show)
    monkeypatch.setattr(
        compilation,
        "attested_archive_transition",
        lambda *_a, **_k: pytest.fail("hid invalid intent"),
    )
    with pytest.raises((TypeError, ValueError), match=gap):
        load_openspec_commitment(root, change_id="contracts")


@pytest.mark.parametrize(
    "kind",
    ["same", "mixed", "different", "empty", "invalid", "archive", "escape", "missing", "symlink"],
)
def test_artifact_path_selection_never_invents_unambiguous_intent(tmp_path, kind):
    """Only one exact existing active root can supply a path-selected identity."""
    path = "openspec/changes/example"
    target = tmp_path / path
    target.mkdir(parents=True)
    requests = {
        "same": (f"{path}/proposal.md", f"{path}/tasks.md"),
        "mixed": (f"{path}/proposal.md", "README.md"),
        "different": (f"{path}/proposal.md", "openspec/changes/other/tasks.md"),
        "empty": (),
        "invalid": ("openspec/changes/Invalid/tasks.md",),
        "archive": ("openspec/changes/archive/tasks.md",),
        "escape": (f"{path}/../other/tasks.md",),
    }
    if kind in {"missing", "symlink"}:
        target.rmdir()
        if kind == "symlink":
            target.symlink_to(tmp_path)
    selected = artifact_path_change(tmp_path, requests.get(kind, (f"{path}/tasks.md",)))
    assert selected == ("example" if kind == "same" else None)
