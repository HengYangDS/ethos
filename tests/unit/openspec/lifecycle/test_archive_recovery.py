"""Resolve an archive transition from evidence-preserving history."""

from __future__ import annotations

from datetime import UTC
from datetime import datetime
from types import SimpleNamespace

import pytest

import ethos.adapters.openspec.lifecycle.archive_provenance as provenance
import ethos.adapters.openspec.lifecycle.archive_transition as archive
import ethos.adapters.repo.commit.rewrite as rewrite
from ethos.adapters.repo.native_effect_attestation import NativeEffect
from ethos.adapters.repo.native_effect_attestation import issue_native_effect

HEAD = "a" * 40
CHANGE = "change"
ARCHIVE = "openspec/changes/archive/2026-08-10-change"


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
        item.payload = SimpleNamespace(body={"plan": {"policy": plans[name].policy}})
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
        item.payload.body["plan"]["policy"] = plans[name].policy
        plans[name].commitment = None
        plans[name].prior_attestations = {"rebase": rebase.model_dump(mode="json")}
        effects[name] = SimpleNamespace(
            updates={f"refs/heads/{branch}": SimpleNamespace(expected=previous, desired=current)},
            assertions={"refs/heads/candidate/dev": HEAD},
        )
        item.payload.body["plan"]["effect"] = {
            "updates": {f"refs/heads/{branch}": {"expected": previous, "desired": current}}
        }
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

    for module in (archive, rewrite):
        monkeypatch.setattr(module, "plan_from_attestation", lambda item: plans[item.id])
        monkeypatch.setattr(module, "git_effect_from_plan", lambda plan: effects[plan.digest])
        monkeypatch.setattr(module, "validate_git_effect_attestation", validate)
    monkeypatch.setattr(archive, "read_attestation_set", lambda _root: ({}, tuple(items)))
    monkeypatch.setattr(archive, "current_tree", lambda *_args: "commit-tree")
    monkeypatch.setattr(rewrite, "repository_identity", lambda *_args, **_kwargs: "repository:test")
    monkeypatch.setattr(provenance, "run_git", ancestry)
    monkeypatch.setattr(provenance, "is_ancestor", lambda _root, old, _new: old in distances)
    monkeypatch.setattr(provenance, "ref_head", lambda _root, spec: objects.get(spec, ""))
    return SimpleNamespace(
        archive=archive_effect,
        refresh=refresh_effect,
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
    archive_graph.distances[HEAD] = 0

    def run_git(_root, *args, **_kwargs):
        return SimpleNamespace(returncode=code if args[0] == "rev-list" else 0, stdout=count)

    monkeypatch.setattr(provenance, "run_git", run_git)
    recovered = archive_graph.resolve(change=CHANGE)
    if expected is None:
        assert recovered is None
    else:
        assert recovered is not None
        assert recovered[1]["resolved_head"] == HEAD
