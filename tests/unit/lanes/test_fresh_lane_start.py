from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.mutation.lane_start_carrier as lane_start_carrier
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.literal_cases import literal_case
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from pathlib import Path


_HOLDER = "agent:test:case:agent-test"


def _fresh_commitment(
    repo: Path,
    path: Path,
    change: str = "fresh-change",
    *,
    predecessors: tuple[str, ...] = (),
    selected_attestations: tuple[str, ...] = (),
    dependencies: tuple[dict[str, object], ...] = (),
) -> Path:
    repository_id = load_repository_commitment(repo).id
    path.write_text(
        tomli_w.dumps(
            commitment_v2(
                id=f"change:{change}",
                intent="Exercise atomic fresh Change bootstrap.",
                subjects=(repository_id,),
                scope=("src/**",),
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
    assert report["lease"]["base_commitment_path"] == (
        "openspec/changes/fresh-change/commitment.toml"
    )
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


@pytest.mark.parametrize(
    ("predecessors", "selected_attestations", "dependencies"),
    [
        pytest.param(("0" * 64,), (), (), id="predecessor"),
        pytest.param((), ("1" * 64,), (), id="selection"),
        pytest.param(
            (),
            (),
            (
                {
                    "kind": "change:requires",
                    "target": "change:missing",
                    "attributes": {},
                },
            ),
            id="unresolved-dependency",
        ),
    ],
)
def test_fresh_lane_rejects_successor_commitment_fields(
    tmp_path: Path,
    predecessors: tuple[str, ...],
    selected_attestations: tuple[str, ...],
    dependencies: tuple[dict[str, object], ...],
) -> None:
    repo, _candidate = init_repo_with_candidate(tmp_path)
    target = tmp_path / "repo-work-fresh-change"
    commitment = _fresh_commitment(
        repo,
        tmp_path / "commitment.toml",
        predecessors=predecessors,
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

    assert report["required_gaps"] == ["lane_start_successor_commitment_requires_start_change"]
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
    literal_case(
        "lanes.test_fresh_lane_start:parametrize:test_start_work_lane_rejects_missing_invalid_or_mismatched_fresh_commitment:0"
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
    literal_case(
        "lanes.test_fresh_lane_start:parametrize:test_start_work_lane_removes_fresh_carrier_when_openspec_fails:1"
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
