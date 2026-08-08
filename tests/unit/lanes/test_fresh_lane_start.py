from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_start_carrier as lane_start_carrier
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.adapters.repo.git import ref_head
from ethos.adapters.repo.status.bindings import leases_by_branch
from tests.support.governed_repository import create_change_source_lane
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate

if TYPE_CHECKING:
    from pathlib import Path


_HOLDER = "agent:test:case:agent-test"


def _fresh_commitment(path: Path, change: str = "fresh-change") -> Path:
    path.write_text(
        "\n".join(
            (
                "schema_version = 1",
                f'id = "change:{change}"',
                'intent = "Exercise atomic fresh Change bootstrap."',
                'subjects = ["repository:self"]',
                'scope = ["src/**"]',
                'permissions = ["repository.read", "work-lane.write", "git.ref.compare-and-swap"]',
                "",
            )
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
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "select custom OpenSpec schema",
    )
    target = tmp_path / "repo-work-fresh-change"
    commitment = _fresh_commitment(tmp_path / "commitment.toml")
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
        commitment_path=_fresh_commitment(tmp_path / "commitment.toml"),
        path=tmp_path / "repo-work-fresh-change",
        holder_ref=_HOLDER,
        apply=True,
    )

    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["lane_start_intent_ambiguous"]


@pytest.mark.parametrize(
    ("commitment", "gap"),
    [
        (None, "lane_start_commitment_required"),
        ("invalid", "lane_start_commitment_invalid"),
        ("other-change", "lane_start_commitment_identity_mismatch"),
    ],
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
        carrier = _fresh_commitment(tmp_path / "commitment.toml", commitment)

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
    [
        ("create", "openspec_change_creation_failed"),
        ("status", "openspec_change_validation_failed"),
    ],
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
        commitment_path=_fresh_commitment(tmp_path / "commitment.toml"),
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
