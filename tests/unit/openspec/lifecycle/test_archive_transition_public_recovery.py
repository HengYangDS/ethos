from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.lifecycle.archive_refresh as refresh
import ethos.adapters.openspec.lifecycle.archive_transition as archive
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect
from ethos.repository.profile import INVALID_PROFILE_ERROR
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

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


@pytest.fixture
def archive_graph(tmp_path, monkeypatch):
    """Isolate graph resolution while validating native nested rebase evidence."""
    items, plans, effects, distances, objects, validated = [], {}, {}, {}, {}, []
    branch = "work/change"

    def archive_effect(name, head, *, change=CHANGE):
        path = ARCHIVE if change == CHANGE else f"openspec/changes/archive/2026-08-10-{change}"
        item = SimpleNamespace(
            predicate="effect:git-ref-update", verifier="agent:test", id=name, effect_digest=name
        )
        plans[name] = SimpleNamespace(
            policy={"transition": "openspec.archive", "change": change, "branch": branch},
            commitment={"schema_version": 3, "id": f"change:{change}", "acceptance": ["done"]},
            facts={"values": {"archive_path": path, "changed_paths": [f"{path}/tasks.md"]}},
            digest=name,
            prior_attestations={},
        )
        effects[name] = SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(desired=head)}
        )
        objects[f"{head}:{path}"] = "archive-tree"
        items.append(item)
        return item

    def refresh_effect(name, previous, current):
        item = archive_effect(name, current)
        rebase = issue_native_effect(
            tmp_path,
            effect=NativeEffect(
                predicate="effect:git-rebase",
                operation="git.rebase",
                command=("git", "rebase"),
                subject={"branch": branch, "candidate_head": HEAD},
                before={"branch": branch, "head": previous, "candidate_head": HEAD},
                after={"branch": "detached", "head": current, "candidate_head": HEAD},
            ),
            state="applied",
            commitment_digest=None,
            repository_id="repository:test",
            issued_at=datetime(2026, 9, 1, tzinfo=UTC),
        )
        plans[name].policy = {"transition": "lane.refresh", "execution_branch": branch}
        plans[name].commitment = None
        plans[name].prior_attestations = {"rebase": rebase.model_dump(mode="json")}
        effects[name] = SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(expected=previous, desired=current)},
            assertions={"refs/heads/candidate/dev": HEAD},
        )
        return item

    def validate(_root, effect, item, *, issuer, plan, current_postconditions):
        assert effect is effects[item.id]
        assert plan is plans[item.id]
        assert issuer == item.verifier
        assert current_postconditions is False
        validated.append(item.id)

    def ancestry(_root, *args, **_kwargs):
        previous = args[2] if args[0] == "merge-base" else args[2].split("..")[0]
        distance = distances.get(previous)
        return SimpleNamespace(returncode=0 if distance is not None else 1, stdout=str(distance))

    for module in (archive, refresh):
        monkeypatch.setattr(module, "plan_from_attestation", lambda item: plans[item.id])
        monkeypatch.setattr(module, "git_effect_from_plan", lambda plan: effects[plan.digest])
        monkeypatch.setattr(module, "validate_git_effect_attestation", validate)
    monkeypatch.setattr(archive, "read_attestation_set", lambda _root: ({}, tuple(items)))
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "commit-tree")
    monkeypatch.setattr(refresh, "repository_identity", lambda *_args, **_kwargs: "repository:test")
    monkeypatch.setattr(archive, "run_git", ancestry)
    monkeypatch.setattr(archive, "_object_id", lambda _root, spec, **_kwargs: objects.get(spec, ""))
    return SimpleNamespace(
        archive=archive_effect,
        refresh=refresh_effect,
        items=items,
        plans=plans,
        effects=effects,
        distances=distances,
        objects=objects,
        validated=validated,
        resolve=lambda **kwargs: archive.attested_archive_transition(
            tmp_path, head="f" * 40, **kwargs
        ),
    )


@pytest.mark.parametrize(
    "mode",
    [
        "direct",
        "refresh",
        "chain",
        "changed_tree",
        "fork",
        "cycle",
        "missing_tree",
        "malformed",
    ],
)
def test_archive_graph_selects_only_unambiguous_current_evidence(archive_graph, mode):
    graph = archive_graph
    previous, current, other = "c" * 40, "d" * 40, "e" * 40
    graph.archive("archive", previous)
    graph.archive("unrelated", other, change="unrelated")
    graph.distances[other] = 3
    if mode == "direct":
        graph.distances[previous] = 2
    else:
        graph.refresh("refresh", previous, current)
        graph.distances[current] = 0
    if mode == "chain":
        graph.distances.pop(current)
        graph.refresh("second", current, "1" * 40)
        graph.distances["1" * 40] = 0
    elif mode == "changed_tree":
        graph.objects[f"{current}:{ARCHIVE}"] = "changed-tree"
    elif mode == "fork":
        graph.refresh("second", previous, "1" * 40)
        graph.distances["1" * 40] = 1
    elif mode == "cycle":
        graph.refresh("cycle", current, previous)
    elif mode == "missing_tree":
        graph.objects.pop(f"{previous}:{ARCHIVE}")
    elif mode == "malformed":
        graph.plans["refresh"].prior_attestations = {"rebase": {"schema_version": 2}}
    recovered = graph.resolve(change=CHANGE)
    if mode in {"changed_tree", "fork", "missing_tree", "malformed"}:
        assert recovered is None
        return
    assert recovered is not None
    commitment, authority = recovered
    assert commitment.id == f"change:{CHANGE}"
    assert authority["attestation_id"] == "archive"
    assert authority["resolved_head"] == (
        previous if mode == "direct" else "1" * 40 if mode == "chain" else current
    )
    assert authority["refresh_attestation_ids"] == (
        [] if mode == "direct" else ["refresh", "second"] if mode == "chain" else ["refresh"]
    )
    assert authority["authorized_paths"] == [f"{ARCHIVE}/tasks.md"]
    assert "archive" in graph.validated
    if mode in {"refresh", "chain", "cycle"}:
        assert "refresh" in graph.validated
    assert graph.resolve()[0].id == f"change:{CHANGE}"


def test_archive_recovery_rejects_equally_near_attestations(archive_graph):
    archive_graph.archive("first", HEAD)
    archive_graph.archive("second", HEAD)
    archive_graph.distances[HEAD] = 0
    with pytest.raises(ValueError, match="openspec_archive_attestation_ambiguous"):
        archive_graph.resolve(change=CHANGE)


@pytest.mark.parametrize(
    "flaw",
    [
        "read",
        "predicate",
        "transition",
        "change",
        "branch",
        "update",
        "commitment",
        "paths",
        "facts",
        "tree",
        "validation",
        "acceptance",
        "archive_path",
    ],
)
def test_archive_recovery_rejects_incomplete_or_invalid_evidence(archive_graph, monkeypatch, flaw):
    graph = archive_graph
    previous = "c" * 40
    item = graph.archive("archive", previous)
    plan = graph.plans[item.id]
    graph.distances[previous] = 0
    if flaw in {"read", "validation"}:

        def refuse(*_args, **_kwargs):
            message = "invalid evidence"
            raise ValueError(message)

        monkeypatch.setattr(
            archive,
            "read_attestation_set" if flaw == "read" else "validate_git_effect_attestation",
            refuse,
        )
    elif flaw == "predicate":
        item.predicate = "proof:execution"
    elif flaw in {"transition", "change", "branch"}:
        plan.policy[flaw] = ""
    elif flaw == "update":
        graph.effects[item.id].updates.clear()
    elif flaw == "commitment":
        plan.commitment = None
    elif flaw in {"paths", "facts"}:
        plan.facts["values"] = {"changed_paths": []} if flaw == "paths" else None
    elif flaw == "tree":
        monkeypatch.setattr(archive, "current_tree", lambda *_args: "")
    elif flaw == "acceptance":
        plan.commitment["acceptance"] = []
    else:
        graph.distances.clear()
        plan.facts["values"]["archive_path"] = ""
    assert graph.resolve(change=CHANGE) is None


@pytest.mark.parametrize(
    ("code", "count", "expected"), [(0, "2\n", 2), (1, "2", None), (0, "invalid", None)]
)
def test_archive_ancestry_observation_rejects_failed_or_malformed_count(
    archive_graph, monkeypatch, code, count, expected
):
    archive_graph.archive("archive", HEAD)

    def run_git(_root, *args, **_kwargs):
        return SimpleNamespace(returncode=code if args[0] == "rev-list" else 0, stdout=count)

    monkeypatch.setattr(archive, "run_git", run_git)
    recovered = archive_graph.resolve(change=CHANGE)
    if expected is None:
        assert recovered is None
    else:
        assert recovered is not None
        assert recovered[1]["resolved_head"] == HEAD


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


@pytest.fixture
def native_archive(tmp_path):
    """Provide real Git objects, not an official CLI execution claim."""
    repo, _candidate = init_repo_with_candidate(tmp_path)
    for relative in SOURCE_ARTIFACTS:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"source artifact: {relative}\n")
    git(repo, "add", "--all")
    git(repo, "commit", "-m", "declare archive source")
    head = git(repo, "rev-parse", "HEAD")
    return repo, head


@pytest.mark.parametrize(
    "mode", ["unchanged", "move", "changed", "retained_active", "foreign", "missing_change"]
)
def test_archive_postimage_uses_isolated_native_git_projection(native_archive, mode):
    repo, head = native_archive
    index = (repo / ".git/index").read_bytes()
    target = repo / ARCHIVE
    if mode not in {"unchanged", "missing_change"}:
        target.parent.mkdir(parents=True)
        (repo / ACTIVE).rename(target)
        if mode == "changed":
            (target / "tasks.md").write_text("changed acceptance\n")
        elif mode == "retained_active":
            (repo / ACTIVE).mkdir()
            (repo / ACTIVE / "tasks.md").write_text("not fully archived\n")
        elif mode == "foreign":
            (repo / "foreign.txt").write_text("unrelated\n")
    before = git(repo, "status", "--porcelain")
    report = archive.archive_postimage(
        repo, head=head, change="" if mode == "missing_change" else CHANGE
    )
    assert (repo / ".git/index").read_bytes() == index
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == before
    if mode == "missing_change":
        assert report is None
        return
    assert report is not None
    assert report.active_present is (mode in {"unchanged", "retained_active"})
    if mode == "move":
        assert report.scope["verdict"] == "pass"
        assert report.scope["archive_path"] == ARCHIVE
        assert report.scope["completion_artifacts"] == sorted(SOURCE_ARTIFACTS)
    else:
        assert report.scope is None


@pytest.mark.parametrize(
    "mode",
    [
        "inferred",
        "selected",
        "wrong_change",
        "preservation_mismatch",
        "nonarchive",
        "missing_parent",
        "missing_source",
    ],
)
def test_committed_archive_selection_binds_current_git_diff(native_archive, monkeypatch, mode):
    repo, head = native_archive
    target = repo / ARCHIVE
    target.parent.mkdir(parents=True)
    (repo / ACTIVE).rename(target)
    git(repo, "add", "--all")
    git(repo, "commit", "-m", "archive exact source")
    kwargs = {}
    if mode in {"selected", "wrong_change"}:
        kwargs["requested_change"] = CHANGE if mode == "selected" else "another"
    elif mode == "preservation_mismatch":
        kwargs["preserved_archive"] = (ARCHIVE, ARCHIVE + "-unbound")
    elif mode == "nonarchive":
        kwargs["changed_paths"] = ("README.md",)
    elif mode == "missing_parent":
        native = archive.git_stdout
        monkeypatch.setattr(
            archive,
            "git_stdout",
            lambda root, *args: "" if args[-1].endswith("^") else native(root, *args),
        )
    elif mode == "missing_source":
        native = archive.run_git

        def run(root, *args, **kwargs):
            return (
                SimpleNamespace(returncode=1, stdout="")
                if args == ("rev-parse", f"{head}:{ACTIVE}")
                else native(root, *args, **kwargs)
            )

        monkeypatch.setattr(archive, "run_git", run)
    result = archive.lease_bound_archive_scope_report(repo, **kwargs)
    if mode in {"inferred", "selected"}:
        assert result["verdict"] == "pass"
        assert result["state"] == "post_archive_closeout"
        assert result["changes"] == [{"name": CHANGE, "path": ARCHIVE}]
    else:
        assert result is None


def test_archive_scope_requires_complete_source_enumeration(tmp_path, monkeypatch):
    _git(monkeypatch)
    native = archive.run_git

    def run(root, *args, **kwargs):
        return (
            SimpleNamespace(returncode=1, stdout="")
            if args[0] == "ls-tree"
            else native(root, *args, **kwargs)
        )

    monkeypatch.setattr(archive, "run_git", run)
    assert (
        archive.archive_postimage_scope_report(
            tmp_path,
            changed_paths=(f"{ARCHIVE}/tasks.md",),
            requested_change=CHANGE,
            tree=TREE,
            source_head=HEAD,
        )
        is None
    )
