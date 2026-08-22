from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from typing import cast

import pytest
import tomli_w

import ethos.adapters.mutation.lane_start_carrier as lane_start_carrier
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.literal_cases import literal_case
from tests.support.semantic import commitment_fixture

if TYPE_CHECKING:
    from pathlib import Path


_HOLDER = "agent:test:case:agent-test"


def _fresh_commitment(
    repo: Path,
    path: Path,
    change: str = "fresh-change",
    *,
    scope: tuple[str, ...] = ("src/**",),
    predecessors: tuple[str, ...] = (),
    selected_attestations: tuple[str, ...] = (),
    dependencies: tuple[dict[str, object], ...] = (),
) -> Path:
    repository_id = load_repository_commitment(repo).id
    path.write_text(
        tomli_w.dumps(
            commitment_fixture(
                id=f"change:{change}",
                intent="Exercise atomic fresh Change bootstrap.",
                subjects=(repository_id,),
                scope=scope,
                predecessors=predecessors,
                selected_attestations=selected_attestations,
                dependencies=dependencies,
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )
    return path


def _fake_openspec(path: Path) -> Path:
    executable = path / "openspec"
    executable.write_text(
        """#!/usr/bin/env python3
import json
import os
import pathlib
import sys

root = pathlib.Path.cwd()
args = sys.argv[1:]
failure = os.environ.get("FAKE_OPENSPEC_FAILURE", "")
if args[:2] == ["new", "change"]:
    if failure == "create":
        raise SystemExit(2)
    change = args[2]
    configured = "custom-workflow" if "schema: custom-workflow" in (
        root / "openspec" / "config.yaml"
    ).read_text() else "spec-driven"
    schema = args[args.index("--schema") + 1] if "--schema" in args else configured
    target = root / "openspec" / "changes" / change
    target.mkdir(parents=True)
    (target / ".openspec.yaml").write_text(f"schema: {schema}\\ncreated: 2026-08-05\\n")
    (target / "README.md").write_text(f"# {change}\\n")
    print(json.dumps({"change": {"id": change, "path": str(target)}}))
elif args[:2] == ["status", "--change"]:
    if failure == "status":
        raise SystemExit(2)
    change = args[2]
    metadata = root / "openspec" / "changes" / change / ".openspec.yaml"
    schema = metadata.read_text().splitlines()[0].removeprefix("schema: ")
    print(json.dumps({"changeName": change, "schemaName": schema}))
else:
    raise SystemExit(2)
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def test_start_work_lane_bootstraps_a_fresh_change_without_a_source_lane(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    (candidate / "openspec" / "config.yaml").write_text(
        "schema: custom-workflow\n",
        encoding="utf-8",
    )
    git(candidate, "add", "openspec/config.yaml")
    git(
        candidate,
        "commit",
        "-m",
        "select custom OpenSpec schema",
    )
    target = tmp_path / "repo-work-fresh-change"
    commitment = _fresh_commitment(repo, tmp_path / "commitment.toml")
    openspec = _fake_openspec(tmp_path)
    monkeypatch.setattr(
        lane_start_carrier,
        "openspec_base_command",
        lambda: (openspec.as_posix(),),
    )

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=commitment,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["verdict"] == "pass"
    assert report["state"] == "started"
    assert report["base_head"] == git(candidate, "rev-parse", "HEAD")
    assert report["source_root"] == ""
    assert report["source_change_id"] == "fresh-change"
    lease = cast("dict[str, object]", report["lease"])
    assert lease["base_commitment_path"] == ("openspec/changes/fresh-change/commitment.toml")
    assert (
        json.loads(
            subprocess.run(
                [openspec, "status", "--change", "fresh-change", "--json"],
                cwd=target,
                check=True,
                text=True,
                capture_output=True,
            ).stdout
        )["schemaName"]
        == "custom-workflow"
    )
    assert git(target, "status", "--short") == ""


def test_start_work_lane_rejects_ambiguous_fresh_and_source_inputs(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    source = create_change_source_lane(repo, tmp_path / "repo-work-source", holder_ref=_HOLDER)

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        source_root=source,
        commitment_path=_fresh_commitment(repo, tmp_path / "commitment.toml"),
        path=tmp_path / "repo-work-fresh-change",
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lane_start_intent_ambiguous"]


def test_start_work_lane_dry_run_validates_required_and_bound_commitment(tmp_path: Path) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"

    missing = start_work_lane(
        root=repo,
        name="fresh-change",
        path=target,
        holder_ref=_HOLDER,
    )
    mismatched = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=_fresh_commitment(repo, tmp_path / "commitment.toml", "other-change"),
        path=target,
        holder_ref=_HOLDER,
    )
    planned = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=_fresh_commitment(repo, tmp_path / "commitment.toml"),
        path=target,
        holder_ref=_HOLDER,
    )

    assert missing["required_gaps"] == ["lane_start_commitment_required"]
    assert mismatched["required_gaps"] == ["lane_start_commitment_identity_mismatch"]
    assert (planned["verdict"], planned["state"], planned["required_gaps"]) == (
        "pass",
        "planned",
        [],
    )
    assert ref_head(repo, "work/fresh-change") == ""
    assert not target.exists()


def test_fresh_lane_accepts_predecessors_resolved_from_the_exact_candidate_tree(
    tmp_path: Path,
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    related = commitment_fixture(
        id="change:historical-change",
        intent="Preserve one immutable historical predecessor.",
        subjects=(load_repository_commitment(candidate).id,),
    )
    historical = "openspec/changes/archive/2026-08-01-historical-change/commitment.toml"
    historical_path = candidate / historical
    historical_path.parent.mkdir(parents=True)
    historical_path.write_text(
        tomli_w.dumps(related.model_dump(mode="python")),
        encoding="utf-8",
    )
    git(candidate, "add", historical)
    git(candidate, "commit", "-m", "record historical Change")
    predecessor = load_commitment(
        candidate,
        carrier=historical,
        change_id="historical-change",
    ).digest()
    target = tmp_path / "repo-work-fresh-change"
    commitment = _fresh_commitment(
        repo,
        tmp_path / "commitment.toml",
        predecessors=(predecessor,),
    )

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=commitment,
        path=target,
        holder_ref=_HOLDER,
    )

    assert (report["verdict"], report["state"], report["required_gaps"]) == (
        "pass",
        "planned",
        [],
    )
    assert ref_head(repo, "work/fresh-change") == ""
    assert not target.exists()


def test_fresh_lane_allows_independent_successors_from_one_predecessor(
    tmp_path: Path,
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    predecessor_commitment = commitment_fixture(
        id="change:shared-predecessor",
        intent="Provide one immutable fork point.",
        subjects=(load_repository_commitment(candidate).id,),
    )
    carrier = "openspec/changes/archive/2026-08-01-shared-predecessor/commitment.toml"
    carrier_path = candidate / carrier
    carrier_path.parent.mkdir(parents=True)
    carrier_path.write_text(
        tomli_w.dumps(predecessor_commitment.model_dump(mode="python")),
        encoding="utf-8",
    )
    git(candidate, "add", carrier)
    git(candidate, "commit", "-m", "record shared predecessor")
    predecessor = load_commitment(
        candidate,
        carrier=carrier,
        change_id="shared-predecessor",
    ).digest()

    reports = tuple(
        start_work_lane(
            root=repo,
            name=change,
            commitment_path=_fresh_commitment(
                repo,
                tmp_path / f"{change}.toml",
                change,
                scope=(scope,),
                predecessors=(predecessor,),
            ),
            path=tmp_path / f"repo-work-{change}",
            holder_ref=f"agent:test:case:{change}",
        )
        for change, scope in (
            ("first-successor", "src/first/**"),
            ("second-successor", "src/second/**"),
        )
    )

    assert [(report["verdict"], report["state"]) for report in reports] == [
        ("pass", "planned"),
        ("pass", "planned"),
    ], reports
    assert ref_head(repo, "work/first-successor") == ""
    assert ref_head(repo, "work/second-successor") == ""
    assert not (tmp_path / "repo-work-first-successor").exists()
    assert not (tmp_path / "repo-work-second-successor").exists()


def test_fresh_lane_rejects_an_unresolved_predecessor_before_any_effect(
    tmp_path: Path,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"
    missing = "0" * 64
    commitment = _fresh_commitment(
        repo,
        tmp_path / "commitment.toml",
        predecessors=(missing,),
    )

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=commitment,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["required_gaps"] == [f"change_lineage_predecessor_missing:{missing}"]
    assert ref_head(repo, "work/fresh-change") == ""
    assert not target.exists()


@pytest.mark.parametrize(
    ("selected_attestations", "dependencies", "gap"),
    [
        pytest.param(
            ("1" * 64,),
            (),
            "lane_start_selected_attestations_require_start_change",
            id="selection",
        ),
        pytest.param(
            (),
            (
                {
                    "kind": "change:requires",
                    "target": "change:missing",
                    "attributes": {},
                },
            ),
            "lane_start_dependencies_require_start_change",
            id="unresolved-dependency",
        ),
    ],
)
def test_fresh_lane_rejects_unresolved_non_lineage_authority(
    tmp_path: Path,
    selected_attestations: tuple[str, ...],
    dependencies: tuple[dict[str, object], ...],
    gap: str,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"
    commitment = _fresh_commitment(
        repo,
        tmp_path / "commitment.toml",
        selected_attestations=selected_attestations,
        dependencies=dependencies,
    )

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=commitment,
        path=target,
        holder_ref=_HOLDER,
    )

    assert report["required_gaps"] == [gap]
    assert ref_head(repo, "work/fresh-change") == ""
    assert not target.exists()


def test_start_work_lane_dry_run_rejects_unproven_hook_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"
    monkeypatch.setattr(
        "ethos.adapters.mutation.lanes.require_runtime_wheel_provenance",
        lambda: (_ for _ in ()).throw(ValueError("hook_runtime_wheel_provenance_missing")),
    )

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=_fresh_commitment(repo, tmp_path / "commitment.toml"),
        path=target,
        holder_ref=_HOLDER,
    )

    assert report["required_gaps"] == ["hook_runtime_wheel_provenance_missing"]
    assert ref_head(repo, "work/fresh-change") == ""
    assert not target.exists()


@pytest.mark.parametrize(
    ("commitment", "gap"),
    cast(
        "list[tuple[str | None, str]]",
        literal_case(
            "lanes.test_fresh_lane_start:parametrize:test_start_work_lane_rejects_missing_invalid_or_mismatched_fresh_commitment:0"
        ),
    ),
)
def test_start_work_lane_rejects_missing_invalid_or_mismatched_fresh_commitment(
    tmp_path: Path,
    commitment: str | None,
    gap: str,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"
    carrier = None
    if commitment == "invalid":
        carrier = tmp_path / "commitment.toml"
        carrier.write_text("not toml =", encoding="utf-8")
    elif commitment:
        carrier = _fresh_commitment(repo, tmp_path / "commitment.toml", commitment)

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=carrier,
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]
    assert ref_head(repo, "work/fresh-change") == ""
    assert not target.exists()


@pytest.mark.parametrize(
    ("failure", "gap"),
    cast(
        "list[tuple[str, str]]",
        literal_case(
            "lanes.test_fresh_lane_start:parametrize:test_start_work_lane_removes_fresh_carrier_when_openspec_fails:1"
        ),
    ),
)
def test_start_work_lane_removes_fresh_carrier_when_openspec_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure: str,
    gap: str,
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"
    openspec = _fake_openspec(tmp_path)
    monkeypatch.setattr(lane_start_carrier, "openspec_base_command", lambda: (str(openspec),))
    monkeypatch.setenv("FAKE_OPENSPEC_FAILURE", failure)

    report = start_work_lane(
        root=repo,
        name="fresh-change",
        commitment_path=_fresh_commitment(repo, tmp_path / "commitment.toml"),
        path=target,
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == [gap]
    assert report["lease_state"] == "not_acquired"
    assert ref_head(repo, "work/fresh-change") == ""
    assert "work/fresh-change" not in leases_by_branch(repo)
    assert not target.exists()
