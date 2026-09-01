from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.archive_transition as archive
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.repository.profile import INVALID_PROFILE_ERROR

if TYPE_CHECKING:
    from pathlib import Path


HEAD = "a" * 40
TREE = "b" * 40
CHANGE = "change"
ACTIVE = "openspec/changes/change"
ARCHIVE = "openspec/changes/archive/2026-08-10-change"
SOURCE_ARTIFACTS = (
    f"{ACTIVE}/.openspec.yaml",
    f"{ACTIVE}/proposal.md",
    f"{ACTIVE}/design.md",
    f"{ACTIVE}/tasks.md",
    f"{ACTIVE}/specs/contracts/spec.md",
)


def _profile(*, valid: bool = True) -> SimpleNamespace:
    if not valid:
        return SimpleNamespace(state="invalid", declaration=None)
    return SimpleNamespace(
        state="valid",
        declaration=SimpleNamespace(openspec=SimpleNamespace(material_paths=("openspec/**",))),
    )


def _git(
    monkeypatch: pytest.MonkeyPatch,
    *,
    collision: bool = False,
    preserved: bool = True,
) -> None:
    source_tree = "source-tree"
    prior_tree = "prior-tree" if collision else ""
    preservation = archive.collision_preservation_path(ARCHIVE, prior_tree, HEAD)

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if args[:3] == ("ls-tree", "-r", "--name-only"):
            return SimpleNamespace(returncode=0, stdout="\n".join(SOURCE_ARTIFACTS))
        if args[0] != "rev-parse":
            return SimpleNamespace(returncode=1, stdout="")
        value = {
            f"{HEAD}:{ACTIVE}": source_tree,
            f"{TREE}:{ARCHIVE}": source_tree,
            f"{HEAD}:{ARCHIVE}": prior_tree,
            f"{TREE}:{preservation}": prior_tree if preserved else "wrong",
        }.get(args[1], "")
        return SimpleNamespace(returncode=0 if value else 1, stdout=value)

    monkeypatch.setattr(archive, "run_git", run_git)


def _scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    changed_paths: tuple[str, ...],
    collision: bool = False,
    preserved: bool = True,
) -> dict[str, object] | None:
    _git(monkeypatch, collision=collision, preserved=preserved)
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile())
    return archive.archive_postimage_scope_report(
        tmp_path,
        changed_paths=changed_paths,
        requested_change=CHANGE,
        tree=TREE,
        source_head=HEAD,
    )


def test_archive_scope_accepts_only_exact_official_change_relocation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    report = _scope(monkeypatch, tmp_path, changed_paths=moved)

    assert report is not None
    assert report["verdict"] == "pass"
    assert report["archive_path"] == ARCHIVE
    assert report["changes"] == [{"name": CHANGE, "path": ARCHIVE}]
    assert report["uncovered_paths"] == []

    retired = _scope(
        monkeypatch,
        tmp_path,
        changed_paths=(f"{ARCHIVE}/extra.txt",),
    )
    assert retired is not None
    assert retired["verdict"] == "block"
    assert _scope(monkeypatch, tmp_path, changed_paths=(f"{ARCHIVE}/tasks.md", "README.md")) is None


def test_archive_scope_maps_only_proven_delta_specs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    report = _scope(
        monkeypatch,
        tmp_path,
        changed_paths=(
            f"{ARCHIVE}/tasks.md",
            "openspec/specs/contracts/spec.md",
            "openspec/specs/unproven/spec.md",
        ),
    )

    assert report is not None
    assert report["covered_paths"] == [
        {"path": f"{ARCHIVE}/tasks.md", "changes": [CHANGE]},
        {"path": "openspec/specs/contracts/spec.md", "changes": [CHANGE]},
    ]
    assert report["uncovered_paths"] == ["openspec/specs/unproven/spec.md"]


def test_archive_scope_requires_exact_collision_preservation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    assert (
        _scope(
            monkeypatch,
            tmp_path,
            changed_paths=moved,
            collision=True,
            preserved=False,
        )
        is None
    )

    report = _scope(
        monkeypatch,
        tmp_path,
        changed_paths=moved,
        collision=True,
        preserved=True,
    )
    assert report is not None
    assert str(report["preserved_archive_path"]).startswith(f"{ARCHIVE}-")


def test_committed_archive_scope_is_inferred_without_a_lease_or_carrier(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    _git(monkeypatch)
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile())
    monkeypatch.setattr(archive, "current_tree", lambda *_args: TREE)

    def git_stdout(_root: Path, *args: str) -> str:
        return {
            ("rev-parse", "HEAD"): "c" * 40,
            ("rev-parse", f"{'c' * 40}^"): HEAD,
        }.get(args, "")

    monkeypatch.setattr(archive, "git_stdout", git_stdout)
    report = archive.lease_bound_archive_scope_report(
        tmp_path,
        changed_paths=moved,
    )

    assert report is not None
    assert report["verdict"] == "pass"
    assert report["state"] == "post_archive_closeout"
    assert report["changes"] == [{"name": CHANGE, "path": ARCHIVE}]


def test_archive_attestation_remains_current_for_descendant_head(monkeypatch, tmp_path) -> None:
    desired = "c" * 40
    current = "d" * 40

    def run_git(_root: Path, *args: str, **_kwargs: object) -> SimpleNamespace:
        if args[:3] == ("merge-base", "--is-ancestor", desired):
            return SimpleNamespace(returncode=0, stdout="")
        if args == ("rev-list", "--count", f"{desired}..{current}"):
            return SimpleNamespace(returncode=0, stdout="2\n")
        return SimpleNamespace(returncode=1, stdout="")

    plan = SimpleNamespace(
        policy={"transition": "openspec.archive", "change": CHANGE, "branch": "work/change"},
        commitment={"schema_version": 3, "id": f"change:{CHANGE}", "acceptance": ["done"]},
        facts={
            "values": {
                "archive_path": ARCHIVE,
                "changed_paths": [f"{ARCHIVE}/tasks.md"],
            }
        },
        digest="plan",
    )
    effect = SimpleNamespace(
        updates={
            "refs/heads/work/change": SimpleNamespace(desired=desired),
        }
    )
    attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="attestation",
        effect_digest="effect",
    )
    monkeypatch.setattr(archive, "read_attestation_set", lambda _root: ({}, [attestation]))
    monkeypatch.setattr(archive, "plan_from_attestation", lambda _attestation: plan)
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda _plan: effect)
    monkeypatch.setattr(archive, "validate_git_effect_attestation", lambda *_a, **_k: None)
    monkeypatch.setattr(
        archive, "current_tree", lambda _root, commit: "tree" if commit == desired else ""
    )
    monkeypatch.setattr(archive, "run_git", run_git)

    recovered = archive.attested_archive_transition(tmp_path, head=current)

    assert recovered is not None
    commitment, authority = recovered
    assert commitment.id == f"change:{CHANGE}"
    assert authority["attestation_id"] == "attestation"


def test_archive_attestation_follows_exact_refresh_chain_without_selecting_other_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archived_head = "c" * 40
    refreshed_head = "d" * 40
    unrelated_head = "e" * 40
    branch = "work/change"
    rebase = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            predicate="effect:git-rebase",
            operation="git.rebase",
            command=("git", "rebase"),
            subject={"branch": branch, "candidate_head": "f" * 40},
            before={"branch": branch, "head": archived_head, "candidate_head": "f" * 40},
            after={"branch": "detached", "head": refreshed_head, "candidate_head": "f" * 40},
        ),
        state="applied",
        commitment_digest=None,
        repository_id="repository:test",
        issued_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    archive_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="archive-attestation",
        effect_digest="archive-effect",
    )
    refresh_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="refresh-attestation",
        effect_digest="refresh-effect",
    )
    unrelated_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="unrelated-attestation",
        effect_digest="unrelated-effect",
    )
    archive_plan = SimpleNamespace(
        policy={"transition": "openspec.archive", "change": CHANGE, "branch": branch},
        commitment={"schema_version": 3, "id": f"change:{CHANGE}", "acceptance": ["done"]},
        facts={
            "values": {
                "archive_path": ARCHIVE,
                "changed_paths": [f"{ARCHIVE}/tasks.md"],
            }
        },
        digest="archive-plan",
        prior_attestations={},
    )
    refresh_plan = SimpleNamespace(
        policy={"transition": "lane.refresh", "execution_branch": branch},
        commitment=None,
        facts={"values": {}},
        digest="refresh-plan",
        prior_attestations={"rebase": rebase.model_dump(mode="json")},
    )
    unrelated_plan = SimpleNamespace(
        policy={
            "transition": "openspec.archive",
            "change": "unrelated",
            "branch": "work/unrelated",
        },
        commitment={"schema_version": 3, "id": "change:unrelated", "acceptance": ["done"]},
        facts={
            "values": {
                "archive_path": "openspec/changes/archive/2026-09-01-unrelated",
                "changed_paths": ["openspec/changes/archive/2026-09-01-unrelated/tasks.md"],
            }
        },
        digest="unrelated-plan",
        prior_attestations={},
    )
    plans = {
        "archive-attestation": archive_plan,
        "refresh-attestation": refresh_plan,
        "unrelated-attestation": unrelated_plan,
    }
    effects = {
        "archive-plan": SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(desired=archived_head)}
        ),
        "refresh-plan": SimpleNamespace(
            updates={
                f"refs/heads/{branch}": SimpleNamespace(
                    expected=archived_head,
                    desired=refreshed_head,
                )
            },
            assertions={"refs/heads/candidate/dev": "f" * 40},
        ),
        "unrelated-plan": SimpleNamespace(
            updates={"refs/heads/work/unrelated": SimpleNamespace(desired=unrelated_head)}
        ),
    }
    monkeypatch.setattr(
        archive,
        "read_attestation_set",
        lambda _root: ({}, [archive_attestation, refresh_attestation, unrelated_attestation]),
    )
    monkeypatch.setattr(archive, "plan_from_attestation", lambda item: plans[item.id])
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda plan: effects[plan.digest])
    monkeypatch.setattr(archive, "validate_git_effect_attestation", lambda *_a, **_k: None)
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "commit-tree")
    monkeypatch.setattr(archive, "repository_identity", lambda *_a, **_k: "repository:test")
    monkeypatch.setattr(
        archive,
        "_ancestor_distance",
        lambda _root, ancestor, _descendant: {
            archived_head: None,
            refreshed_head: 0,
            unrelated_head: 1,
        }.get(ancestor),
    )
    monkeypatch.setattr(
        archive,
        "_object_id",
        lambda _root, specification, **_kwargs: (
            "archive-tree"
            if specification in {f"{archived_head}:{ARCHIVE}", f"{refreshed_head}:{ARCHIVE}"}
            else "unrelated-tree"
        ),
    )

    recovered = archive.attested_archive_transition(tmp_path, head=refreshed_head)

    assert recovered is not None
    commitment, authority = recovered
    assert commitment.id == f"change:{CHANGE}"
    assert authority["resolved_head"] == refreshed_head
    assert authority["refresh_attestation_ids"] == ["refresh-attestation"]


def test_archive_attestation_rejects_refresh_that_changes_the_archive_postimage(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archived_head = "c" * 40
    changed_head = "d" * 40
    branch = "work/change"
    rebase = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            predicate="effect:git-rebase",
            operation="git.rebase",
            command=("git", "rebase"),
            subject={"branch": branch, "candidate_head": "f" * 40},
            before={"branch": branch, "head": archived_head, "candidate_head": "f" * 40},
            after={"branch": "detached", "head": changed_head, "candidate_head": "f" * 40},
        ),
        state="applied",
        commitment_digest=None,
        repository_id="repository:test",
        issued_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    archive_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="archive-attestation",
        effect_digest="archive-effect",
    )
    refresh_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="refresh-attestation",
        effect_digest="refresh-effect",
    )
    plans = {
        "archive-attestation": SimpleNamespace(
            policy={"transition": "openspec.archive", "change": CHANGE, "branch": branch},
            commitment={
                "schema_version": 3,
                "id": f"change:{CHANGE}",
                "acceptance": ["done"],
            },
            facts={
                "values": {
                    "archive_path": ARCHIVE,
                    "changed_paths": [f"{ARCHIVE}/tasks.md"],
                }
            },
            digest="archive-plan",
            prior_attestations={},
        ),
        "refresh-attestation": SimpleNamespace(
            policy={"transition": "lane.refresh", "execution_branch": branch},
            commitment=None,
            facts={"values": {}},
            digest="refresh-plan",
            prior_attestations={"rebase": rebase.model_dump(mode="json")},
        ),
    }
    effects = {
        "archive-plan": SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(desired=archived_head)}
        ),
        "refresh-plan": SimpleNamespace(
            updates={
                f"refs/heads/{branch}": SimpleNamespace(
                    expected=archived_head,
                    desired=changed_head,
                )
            },
            assertions={"refs/heads/candidate/dev": "f" * 40},
        ),
    }
    monkeypatch.setattr(
        archive,
        "read_attestation_set",
        lambda _root: ({}, [archive_attestation, refresh_attestation]),
    )
    monkeypatch.setattr(archive, "plan_from_attestation", lambda item: plans[item.id])
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda plan: effects[plan.digest])
    monkeypatch.setattr(archive, "validate_git_effect_attestation", lambda *_a, **_k: None)
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "commit-tree")
    monkeypatch.setattr(archive, "repository_identity", lambda *_a, **_k: "repository:test")
    monkeypatch.setattr(
        archive,
        "_ancestor_distance",
        lambda _root, ancestor, _descendant: 0 if ancestor == changed_head else None,
    )
    monkeypatch.setattr(
        archive,
        "_object_id",
        lambda _root, specification, **_kwargs: {
            f"{archived_head}:{ARCHIVE}": "archive-tree",
            f"{changed_head}:{ARCHIVE}": "changed-tree",
        }.get(specification, ""),
    )

    assert archive.attested_archive_transition(tmp_path, head=changed_head) is None


def test_archive_refresh_resolution_fails_closed_on_fork(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archived_head = "c" * 40
    first_head = "d" * 40
    second_head = "e" * 40
    current_head = "f" * 40
    branch = "work/change"
    candidate_head = "1" * 40
    first_rebase = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            predicate="effect:git-rebase",
            operation="git.rebase",
            command=("git", "rebase"),
            subject={"branch": branch, "candidate_head": candidate_head},
            before={"branch": branch, "head": archived_head, "candidate_head": candidate_head},
            after={"branch": "detached", "head": first_head, "candidate_head": candidate_head},
        ),
        state="applied",
        commitment_digest=None,
        repository_id="repository:test",
        issued_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    second_rebase = issue_native_effect(
        tmp_path,
        effect=NativeEffect(
            predicate="effect:git-rebase",
            operation="git.rebase",
            command=("git", "rebase"),
            subject={"branch": branch, "candidate_head": candidate_head},
            before={"branch": branch, "head": archived_head, "candidate_head": candidate_head},
            after={"branch": "detached", "head": second_head, "candidate_head": candidate_head},
        ),
        state="applied",
        commitment_digest=None,
        repository_id="repository:test",
        issued_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    archive_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="archive-attestation",
        effect_digest="archive-effect",
    )
    first_refresh = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="refresh-first",
        effect_digest="refresh-first-effect",
    )
    second_refresh = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="refresh-second",
        effect_digest="refresh-second-effect",
    )
    plans = {
        "archive-attestation": SimpleNamespace(
            policy={"transition": "openspec.archive", "change": CHANGE, "branch": branch},
            commitment={
                "schema_version": 3,
                "id": f"change:{CHANGE}",
                "acceptance": ["done"],
            },
            facts={
                "values": {
                    "archive_path": ARCHIVE,
                    "changed_paths": [f"{ARCHIVE}/tasks.md"],
                }
            },
            digest="archive-plan",
            prior_attestations={},
        ),
        "refresh-first": SimpleNamespace(
            policy={"transition": "lane.refresh", "execution_branch": branch},
            commitment=None,
            facts={"values": {}},
            digest="refresh-first-plan",
            prior_attestations={"rebase": first_rebase.model_dump(mode="json")},
        ),
        "refresh-second": SimpleNamespace(
            policy={"transition": "lane.refresh", "execution_branch": branch},
            commitment=None,
            facts={"values": {}},
            digest="refresh-second-plan",
            prior_attestations={"rebase": second_rebase.model_dump(mode="json")},
        ),
    }
    effects = {
        "archive-plan": SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(desired=archived_head)}
        ),
        "refresh-first-plan": SimpleNamespace(
            updates={
                f"refs/heads/{branch}": SimpleNamespace(
                    expected=archived_head,
                    desired=first_head,
                )
            },
            assertions={"refs/heads/candidate/dev": candidate_head},
        ),
        "refresh-second-plan": SimpleNamespace(
            updates={
                f"refs/heads/{branch}": SimpleNamespace(
                    expected=archived_head,
                    desired=second_head,
                )
            },
            assertions={"refs/heads/candidate/dev": candidate_head},
        ),
    }
    monkeypatch.setattr(
        archive,
        "read_attestation_set",
        lambda _root: ({}, [archive_attestation, first_refresh, second_refresh]),
    )
    monkeypatch.setattr(archive, "plan_from_attestation", lambda item: plans[item.id])
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda plan: effects[plan.digest])
    monkeypatch.setattr(archive, "validate_git_effect_attestation", lambda *_a, **_k: None)
    monkeypatch.setattr(archive, "repository_identity", lambda *_a, **_k: "repository:test")
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "commit-tree")
    monkeypatch.setattr(
        archive,
        "_ancestor_distance",
        lambda _root, ancestor, _descendant: 1 if ancestor in {first_head, second_head} else None,
    )
    monkeypatch.setattr(archive, "_object_id", lambda *_a, **_k: "archive-tree")

    assert archive.attested_archive_transition(tmp_path, head=current_head) is None


def test_archive_attestation_rejects_malformed_nested_refresh_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    archived_head = "c" * 40
    refreshed_head = "d" * 40
    branch = "work/change"
    archive_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="archive-attestation",
        effect_digest="archive-effect",
    )
    refresh_attestation = SimpleNamespace(
        predicate="effect:git-ref-update",
        verifier="agent:test",
        id="refresh-attestation",
        effect_digest="refresh-effect",
    )
    plans = {
        "archive-attestation": SimpleNamespace(
            policy={"transition": "openspec.archive", "change": CHANGE, "branch": branch},
            commitment={
                "schema_version": 3,
                "id": f"change:{CHANGE}",
                "acceptance": ["done"],
            },
            facts={
                "values": {
                    "archive_path": ARCHIVE,
                    "changed_paths": [f"{ARCHIVE}/tasks.md"],
                }
            },
            digest="archive-plan",
            prior_attestations={},
        ),
        "refresh-attestation": SimpleNamespace(
            policy={"transition": "lane.refresh", "execution_branch": branch},
            commitment=None,
            facts={"values": {}},
            digest="refresh-plan",
            prior_attestations={"rebase": {"schema_version": 2}},
        ),
    }
    effects = {
        "archive-plan": SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(desired=archived_head)}
        ),
        "refresh-plan": SimpleNamespace(
            updates={
                f"refs/heads/{branch}": SimpleNamespace(
                    expected=archived_head,
                    desired=refreshed_head,
                )
            },
            assertions={"refs/heads/candidate/dev": "f" * 40},
        ),
    }
    monkeypatch.setattr(
        archive,
        "read_attestation_set",
        lambda _root: ({}, [archive_attestation, refresh_attestation]),
    )
    monkeypatch.setattr(archive, "plan_from_attestation", lambda item: plans[item.id])
    monkeypatch.setattr(archive, "git_effect_from_plan", lambda plan: effects[plan.digest])
    monkeypatch.setattr(archive, "validate_git_effect_attestation", lambda *_a, **_k: None)
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "commit-tree")
    monkeypatch.setattr(
        archive,
        "_ancestor_distance",
        lambda _root, ancestor, _descendant: 0 if ancestor == refreshed_head else None,
    )
    monkeypatch.setattr(archive, "_object_id", lambda *_a, **_k: "archive-tree")

    assert archive.attested_archive_transition(tmp_path, head=refreshed_head) is None


def test_archive_scope_rejects_invalid_profile(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tuple(path.replace(ACTIVE, ARCHIVE, 1) for path in SOURCE_ARTIFACTS)
    _git(monkeypatch)
    monkeypatch.setattr(archive, "load_repository_profile", lambda _root: _profile(valid=False))

    with pytest.raises(ValueError, match=INVALID_PROFILE_ERROR):
        archive.archive_postimage_scope_report(
            tmp_path,
            changed_paths=moved,
            requested_change=CHANGE,
            tree=TREE,
            source_head=HEAD,
        )
