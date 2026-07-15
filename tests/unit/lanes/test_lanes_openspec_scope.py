from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import ethos.adapters.openspec.cli as openspec_cli
import ethos.adapters.openspec.core as openspec_core
import ethos.adapters.openspec.lifecycle.core as openspec_lifecycle
import ethos.adapters.openspec.lifecycle.scope as openspec_scope
import ethos.surface.cli.root.planning as planning_cli
import ethos.surface.cli.root.proof as proof_cli
from ethos.adapters.admission.prewrite import _material_scope_from_lifecycle
from ethos.adapters.admission.prewrite import prewrite_guard
from ethos.adapters.mutation.lanes import start_work_lane
from ethos.repository.adoption.planner import adoption_plan
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.lane_helpers import add_candidate_worktree
from tests.support.lane_helpers import git
from tests.support.lane_helpers import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def _official_open_spec_result(
    args: tuple[str, ...], changes: list[dict[str, object]]
) -> dict[str, object]:
    """Return one fake official OpenSpec command result with stable JSON shape."""
    payloads: dict[tuple[str, ...], dict[str, object]] = {
        ("doctor", "--json"): {"root": {"healthy": True}},
        ("list", "--json"): {"changes": changes},
        ("status", "--change", "matching", "--json"): {
            "isComplete": True,
            "schemaName": "spec-driven",
        },
        ("validate", "--all", "--strict", "--json"): {
            "items": [],
            "summary": {"totals": {"failed": 0}},
        },
        ("archive", "matching", "--yes", "--json"): {"archive": {"change": "matching"}},
    }
    return {
        "command": ["openspec", *args],
        "exit_code": 0,
        "stdout": "{}",
        "stderr": "",
        "json": payloads.get(args, {}),
        "parse_error": "",
    }


def _mock_official_active_change(monkeypatch, name: str, status: str = "in-progress") -> None:
    """Bind one named official Change to the test seam."""
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda _root, _base, args: _official_open_spec_result(
            args, [{"name": name, "status": status}]
        ),
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "active_claim_openspec_carriers",
        lambda _root: {f"openspec/changes/{name}"},
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "proposal_protocol_report",
        lambda _root, _change: {"ok": True, "required_gaps": []},
    )


def _worktree(repo: Path, tmp_path: Path, monkeypatch) -> Path:
    worktree = tmp_path / "repo-work-owned"
    add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    start_work_lane(
        root=repo,
        name="owned",
        path=worktree,
        holder_ref="agent:test:case:agent-test",
        apply=True,
    )
    monkeypatch.setenv("ETHOS_ACTOR", "agent:test:case:agent-test")
    return worktree


def test_prewrite_uses_same_official_scope_candidates_as_plan_and_prove(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Prewrite excludes unknown directories through the official list reader."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["guidelines.md"]\n', encoding="utf-8"
    )
    (repo / "guidelines.md").write_text("# Guidelines\n", encoding="utf-8")
    matching = repo / "openspec" / "changes" / "matching"
    matching.mkdir(parents=True)
    (matching / "scope.toml").write_text(
        'schema_version = 1\npaths = ["guidelines.md"]\n', encoding="utf-8"
    )
    (repo / "openspec" / "changes" / "unknown-directory").mkdir(parents=True)
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add adopter scope fixture")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    _mock_official_active_change(monkeypatch, "matching")

    lifecycle = openspec_core.openspec_governance_report(
        worktree,
        lifecycle=True,
        changed_paths=("guidelines.md",),
    )
    prewrite = prewrite_guard(
        root=worktree,
        paths=[worktree / "guidelines.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert lifecycle["lifecycle"]["scope_binding"]["state"] == "covered"
    assert [item["name"] for item in lifecycle["lifecycle"]["scope_binding"]["changes"]] == [
        "matching"
    ]
    assert prewrite["ok"] is True
    assert prewrite["material_scope"] == lifecycle["lifecycle"]["scope_binding"]

    unavailable = _material_scope_from_lifecycle({})
    assert unavailable["state"] == "not_available"
    assert unavailable["ok"] is True
    malformed = _material_scope_from_lifecycle({"lifecycle": {"scope_binding": "bad"}})
    assert malformed == unavailable


def test_prewrite_bootstrap_reads_untracked_official_change_scope_companion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A valid untracked companion admits later material writes for its official Change."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["guidelines.md"]\n', encoding="utf-8"
    )
    (repo / "guidelines.md").write_text("# Guidelines\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare adopter material paths")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    change = worktree / "openspec" / "changes" / "bootstrap"
    change.mkdir(parents=True)
    (change / "scope.toml").write_text(
        'schema_version = 1\npaths = ["guidelines.md"]\n', encoding="utf-8"
    )
    _mock_official_active_change(monkeypatch, "bootstrap")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "guidelines.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is True
    assert report["material_scope"]["state"] == "covered"
    assert report["material_scope"]["covered_paths"] == [
        {"path": "guidelines.md", "changes": ["bootstrap"]}
    ]


@pytest.mark.parametrize(
    ("scope_body", "expected"),
    [
        (None, "openspec_material_path_uncovered:guidelines.md"),
        ("paths = []\n", "openspec_material_path_uncovered:guidelines.md"),
    ],
)
def test_prewrite_bootstrap_requires_valid_untracked_scope_companion(
    tmp_path: Path,
    monkeypatch,
    scope_body: str | None,
    expected: str,
) -> None:
    """A bare or malformed Change directory never grants a material write exemption."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["guidelines.md"]\n', encoding="utf-8"
    )
    (repo / "guidelines.md").write_text("# Guidelines\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare adopter material paths")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    change = worktree / "openspec" / "changes" / "bootstrap"
    change.mkdir(parents=True)
    if scope_body is not None:
        (change / "scope.toml").write_text(scope_body, encoding="utf-8")
    _mock_official_active_change(monkeypatch, "bootstrap")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / "guidelines.md"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == expected
    assert report["material_scope"]["changes"][0]["ok"] is False


def test_prewrite_admits_only_new_official_scope_file_for_bootstrap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A single absent scope companion is the only bootstrap write exception."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        "[openspec]\n"
        'material_paths = ["guidelines.md", ".ethos/profile.toml", '
        '"openspec/changes/bootstrap/**"]\n',
        encoding="utf-8",
    )
    (repo / "guidelines.md").write_text("# Guidelines\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare adopter material paths")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    change = worktree / "openspec" / "changes" / "bootstrap"
    change.mkdir(parents=True)
    scope_path = change / "scope.toml"
    _mock_official_active_change(monkeypatch, "bootstrap")

    bootstrap = prewrite_guard(
        root=worktree,
        paths=[scope_path],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert bootstrap["ok"] is True
    assert bootstrap["material_scope"]["state"] == "bootstrap_scope_creation"
    assert bootstrap["material_scope"]["bootstrap"] == {
        "change": "bootstrap",
        "scope_path": "openspec/changes/bootstrap/scope.toml",
    }

    scope_path.write_text(
        "schema_version = 1\n"
        'paths = ["guidelines.md", ".ethos/profile.toml", '
        '"openspec/changes/bootstrap/**"]\n',
        encoding="utf-8",
    )
    covered = prewrite_guard(
        root=worktree,
        paths=[
            worktree / "guidelines.md",
            worktree / ".ethos" / "profile.toml",
            scope_path,
            change / "proposal.md",
        ],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert covered["ok"] is True
    assert covered["material_scope"]["state"] == "covered"
    assert {item["path"] for item in covered["material_scope"]["covered_paths"]} == {
        "guidelines.md",
        ".ethos/profile.toml",
        "openspec/changes/bootstrap/scope.toml",
        "openspec/changes/bootstrap/proposal.md",
    }


def test_prewrite_bootstrap_scope_must_cover_its_own_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A companion that omits itself cannot bootstrap its own tracked write."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["openspec/changes/bootstrap/**"]\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare scope material paths")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    change = worktree / "openspec" / "changes" / "bootstrap"
    change.mkdir(parents=True)
    scope_path = change / "scope.toml"
    scope_path.write_text('schema_version = 1\npaths = ["guidelines.md"]\n', encoding="utf-8")
    _mock_official_active_change(monkeypatch, "bootstrap")

    report = prewrite_guard(
        root=worktree,
        paths=[scope_path],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert (
        report["error"] == "openspec_material_path_uncovered:openspec/changes/bootstrap/scope.toml"
    )


def test_uncovered_material_path_blocks_prewrite_plan_and_prove(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """All product surfaces project the same uncovered-path diagnostic."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["guidelines.md"]\n', encoding="utf-8"
    )
    (repo / "guidelines.md").write_text("# Guidelines\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare uncovered material path")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    _mock_official_active_change(monkeypatch, "matching")
    (worktree / "guidelines.md").write_text("# Changed\n", encoding="utf-8")
    expected = "openspec_material_path_uncovered:guidelines.md"

    prewrite = prewrite_guard(
        root=worktree,
        paths=[worktree / "guidelines.md"],
        editor_root=worktree,
        require_editor_root=True,
    )
    plan = run_ethos("plan", "--changed", "--root", worktree.as_posix(), "--json")
    prove = run_ethos_blocked("prove", "--root", worktree.as_posix(), "--json")

    assert prewrite["error"] == expected
    assert plan["ok"] is False
    assert expected in plan["required_gaps"]
    assert expected in prove["required_gaps"]


def test_plan_and_prove_receive_the_same_dirty_scope_paths(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """Plan and proof pass dirty repository paths to the lifecycle read model."""
    repo = init_repo(tmp_path / "repo")
    adoption_plan(repo, profile="generic", apply=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "adopt and add readme")
    expected = ("README.md",)
    calls: list[tuple[str, tuple[str, ...]]] = []

    def report(
        _root: Path,
        *,
        lifecycle: bool = False,
        changed_paths: tuple[str, ...] = (),
    ) -> dict[str, object]:
        calls.append(("lifecycle" if lifecycle else "plain", changed_paths))
        return {"ok": True, "required_gaps": []}

    monkeypatch.setattr(planning_cli, "openspec_governance_report", report)
    monkeypatch.setattr(proof_cli, "openspec_governance_report", report)
    (repo / "README.md").write_text("changed\n", encoding="utf-8")

    plan = run_ethos("plan", "--changed", "--root", repo.as_posix(), "--json")
    prove = run_ethos("prove", "--root", repo.as_posix(), "--json")

    assert plan["ok"] is True
    assert prove["ok"] is True
    assert calls == [("lifecycle", expected), ("lifecycle", expected)]


def test_archiving_scope_covers_path_despite_unrelated_incomplete_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """One valid selected companion covers a path; other diagnostics stay advisory."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["guidelines.md"]\n', encoding="utf-8"
    )
    matching = repo / "openspec" / "changes" / "matching"
    matching.mkdir(parents=True)
    (matching / "scope.toml").write_text(
        'schema_version = 1\npaths = ["guidelines.md"]\n', encoding="utf-8"
    )
    archiving = repo / "openspec" / "changes" / "archiving"
    archiving.mkdir(parents=True)
    (archiving / "scope.toml").write_text(
        'schema_version = 1\npaths = ["guidelines.md"]\n', encoding="utf-8"
    )
    (repo / "openspec" / "changes" / "unrelated-incomplete").mkdir(parents=True)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda _root, _base, args: _official_open_spec_result(
            args,
            [
                {"name": "archiving", "status": "archiving"},
                {"name": "matching", "status": "complete"},
                {"name": "unrelated-incomplete", "status": "in-progress"},
            ],
        ),
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "active_claim_openspec_carriers",
        lambda _root: {
            "openspec/changes/archiving",
            "openspec/changes/matching",
            "openspec/changes/unrelated-incomplete",
        },
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "proposal_protocol_report",
        lambda _root, _change: {"ok": True, "required_gaps": []},
    )

    report = openspec_core.openspec_governance_report(
        repo,
        lifecycle=True,
        changed_paths=("guidelines.md",),
    )
    binding = report["lifecycle"]["scope_binding"]

    assert binding["state"] == "covered"
    assert binding["required_gaps"] == []
    assert binding["covered_paths"] == [
        {"path": "guidelines.md", "changes": ["archiving", "matching"]}
    ]
    assert "openspec_scope_missing:unrelated-incomplete" in binding["advisory_gaps"]


@pytest.mark.parametrize(
    ("scope_body", "state", "diagnostic", "external"),
    [
        (
            'schema_version = 1\npaths = ["guidelines.md"]\n',
            "covered",
            "",
            False,
        ),
        (None, "uncovered", "openspec_archive_scope_missing:change", False),
        ("paths = [\n", "uncovered", "openspec_archive_scope_invalid:change", False),
        ('schema_version = 1\npaths = ["guidelines.md"]\n', "uncovered", "", True),
    ],
)
def test_current_archive_scope_is_reconciliation_only(
    tmp_path: Path, scope_body: str | None, state: str, diagnostic: str, external: bool
) -> None:
    repo = init_repo(tmp_path / "repo")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(
        '[openspec]\nmaterial_paths = [".ethos/profile.toml", "guidelines.md", "openspec/**"]\n'
    )
    archive = repo / "openspec" / "changes" / "archive" / "change"
    archive.mkdir(parents=True)
    if scope_body is not None:
        (archive / "scope.toml").write_text(scope_body)
    metadata = archive / ".openspec.yaml"
    metadata.write_text("schema: spec-driven\ncreated: 2026-07-15\n")
    archive_paths = (
        metadata.relative_to(repo).as_posix(),
        (archive / "scope.toml").relative_to(repo).as_posix(),
    )
    material_paths = (
        "guidelines.md",
        *archive_paths,
        *((".ethos/profile.toml",) if external else ()),
    )
    current = openspec_scope.material_change_scope_report(
        repo, changed_paths=material_paths, active_change_names=()
    )
    historical = openspec_scope.material_change_scope_report(
        repo, changed_paths=("guidelines.md",), active_change_names=()
    )
    uncovered = material_paths if diagnostic else ((".ethos/profile.toml",) if external else ())
    assert (current["state"], historical["state"]) == (state, "uncovered")
    assert tuple(current["uncovered_paths"]) == uncovered
    assert diagnostic in current["advisory_gaps"] or not diagnostic


def test_prewrite_plan_and_prove_share_official_scope_coverage_verdict(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """All entry points use the official list-selected Change companions."""
    repo = init_repo(tmp_path / "repo")
    adoption_plan(repo, profile="generic", apply=True)
    matching = repo / "openspec" / "changes" / "matching"
    (matching / "specs" / "repository-governance").mkdir(parents=True)
    (matching / "proposal.md").write_text("# Matching\n", encoding="utf-8")
    (matching / "design.md").write_text("# Design\n", encoding="utf-8")
    (matching / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (matching / "specs" / "repository-governance" / "spec.md").write_text(
        "## ADDED Requirements\n", encoding="utf-8"
    )
    (matching / "scope.toml").write_text(
        'schema_version = 1\npaths = ["docs/governance/**"]\n', encoding="utf-8"
    )
    claim = repo / "evidence" / "claims" / "matching.toml"
    claim.write_text(
        '[claim]\nstate = "active"\n\n[carriers]\nopenspec = "openspec/changes/matching"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add matching scope fixture")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    monkeypatch.setattr(openspec_cli, "openspec_base_command", lambda: ("openspec",))
    monkeypatch.setattr(
        openspec_cli,
        "run_json",
        lambda _root, _base, args: _official_open_spec_result(
            args, [{"name": "matching", "status": "in-progress"}]
        ),
    )
    monkeypatch.setattr(
        openspec_lifecycle,
        "proposal_protocol_report",
        lambda _root, _change: {"ok": True, "required_gaps": []},
    )
    governed_path = worktree / "docs" / "governance" / "ethos.md"
    governed_path.write_text("# Changed\n", encoding="utf-8")

    prewrite = prewrite_guard(
        root=worktree,
        paths=[governed_path],
        editor_root=worktree,
        require_editor_root=True,
    )
    plan = run_ethos("plan", "--changed", "--root", worktree.as_posix(), "--json")
    prove = run_ethos("prove", "--root", worktree.as_posix(), "--json")
    plan_scope = plan["data"]["openspec_lifecycle"]["lifecycle"]["scope_binding"]
    prove_scope = prove["data"]["openspec_lifecycle"]["lifecycle"]["scope_binding"]

    assert prewrite["ok"] is True
    assert plan["ok"] is True
    assert prove["ok"] is True
    assert prewrite["material_scope"] == plan_scope == prove_scope
    assert plan_scope["covered_paths"] == [
        {"path": "docs/governance/ethos.md", "changes": ["matching"]}
    ]


def test_prewrite_does_not_rebootstrap_a_tracked_scope_companion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The bootstrap exception applies only before a Change-local scope is tracked."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["openspec/changes/bootstrap/**"]\n',
        encoding="utf-8",
    )
    scope_path = repo / "openspec" / "changes" / "bootstrap" / "scope.toml"
    scope_path.parent.mkdir(parents=True)
    scope_path.write_text(
        'schema_version = 1\npaths = ["openspec/changes/bootstrap/**"]\n',
        encoding="utf-8",
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "track bootstrap scope")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    scope_path = worktree / "openspec" / "changes" / "bootstrap" / "scope.toml"
    scope_path.unlink()
    _mock_official_active_change(monkeypatch, "bootstrap")

    report = prewrite_guard(
        root=worktree,
        paths=[scope_path],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["material_scope"]["state"] == "uncovered"
    assert (
        report["error"] == "openspec_material_path_uncovered:openspec/changes/bootstrap/scope.toml"
    )


@pytest.mark.parametrize(
    "profile_body",
    [
        'schema_version = 1\nprofile_id = "sample"\n',
        "[openspec]\nmaterial_paths = []\n",
    ],
)
def test_scope_reader_fails_closed_when_adopter_omits_material_paths(
    tmp_path: Path,
    profile_body: str,
) -> None:
    """No valid adopter profile can silently interpret empty material paths as none."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(profile_body, encoding="utf-8")

    report = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=(),
        active_change_names=(),
    )

    assert report["state"] == "material_paths_missing"
    assert report["required_gaps"] == ["openspec_material_paths_missing"]


def test_scope_reader_rejects_nonempty_invalid_material_paths(tmp_path: Path) -> None:
    """A declared but invalid material-path payload cannot bypass admission."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = [""]\n', encoding="utf-8"
    )

    report = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=("guidelines.md",),
        active_change_names=(),
    )

    assert report["required_gaps"] == ["openspec_material_paths_invalid"]


def test_scope_reader_accepts_overlap_and_ignores_nonmaterial_paths(
    tmp_path: Path,
) -> None:
    """Coverage is per material path; overlaps are accepted and other paths are inert."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = ["docs/**"]\n', encoding="utf-8"
    )
    first = repo / "openspec" / "changes" / "first"
    second = repo / "openspec" / "changes" / "second"
    unselected = repo / "openspec" / "changes" / "unselected"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    unselected.mkdir(parents=True)
    (first / "scope.toml").write_text('schema_version = 1\npaths = ["docs/**"]\n', encoding="utf-8")
    (second / "scope.toml").write_text(
        'schema_version = 1\npaths = ["docs/governance/**"]\n', encoding="utf-8"
    )

    report = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=("README.md", "docs/governance/policy.md"),
        active_change_names=("first", "second"),
    )

    assert report["state"] == "covered"
    assert report["material_paths"] == ["docs/governance/policy.md"]
    assert report["covered_paths"] == [
        {"path": "docs/governance/policy.md", "changes": ["first", "second"]}
    ]
    assert report["required_gaps"] == []


def test_scope_reader_handles_invalid_profile_and_product_root_compatibly(
    tmp_path: Path,
) -> None:
    """Malformed adopter profiles fail closed, while product roots remain unaffected."""
    invalid_adopter = init_repo(tmp_path / "invalid-adopter")
    (invalid_adopter / ".ethos").mkdir(exist_ok=True)
    (invalid_adopter / ".ethos" / "profile.toml").write_text(
        '[openspec\nmaterial_paths = ["docs/**"]\n', encoding="utf-8"
    )
    product_root = init_repo(tmp_path / "product")

    invalid = openspec_scope.material_change_scope_report(
        invalid_adopter,
        changed_paths=("docs/policy.md",),
        active_change_names=(),
    )
    product = openspec_scope.material_change_scope_report(
        product_root,
        changed_paths=("docs/policy.md",),
        active_change_names=(),
    )

    assert invalid["required_gaps"] == ["openspec_material_paths_profile_invalid"]
    assert product["state"] == "not_applicable"
    assert product["required_gaps"] == []


def test_prewrite_bootstraps_tracked_legacy_profile_from_fresh_official_change(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A fresh official Change admits only the legacy profile declaration first."""
    repo = init_repo(tmp_path / "repo")
    profile_path = repo / ".ethos" / "profile.toml"
    profile_path.parent.mkdir(exist_ok=True)
    profile_path.write_text('profile_id = "legacy-adopter"\n', encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add legacy adopted profile")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    (worktree / "openspec" / "changes" / "matching").mkdir(parents=True)
    _mock_official_active_change(monkeypatch, "matching", status="no-tasks")

    profile = worktree / ".ethos" / "profile.toml"
    admitted = prewrite_guard(
        root=worktree,
        paths=[profile],
        editor_root=worktree,
        require_editor_root=True,
    )
    widened = prewrite_guard(
        root=worktree,
        paths=[profile, worktree / "openspec" / "changes" / "matching" / "scope.toml"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert admitted["ok"] is True
    assert admitted["openspec_lifecycle"]["lifecycle"]["changes"] == []
    assert admitted["material_scope"]["state"] == "profile_material_paths_bootstrap"
    assert admitted["material_scope"]["profile_bootstrap"] == {
        "change": "matching",
        "profile_path": ".ethos/profile.toml",
    }
    assert widened["ok"] is False
    assert widened["error"] == "openspec_material_paths_missing"


@pytest.mark.parametrize(
    ("profile_body", "case", "change_names"),
    [
        ("[openspec]\nmaterial_paths = []\n", "empty", ("matching",)),
        ('profile_id = "legacy-adopter"\n', "untracked", ("matching",)),
        ('profile_id = "legacy-adopter"\n', "multiple", ("first", "second")),
        ('profile_id = "legacy-adopter"\n', "missing-change", ("matching",)),
    ],
)
def test_profile_material_paths_bootstrap_rejects_nonunique_or_nonlegacy_profile(
    tmp_path: Path,
    profile_body: str,
    case: str,
    change_names: tuple[str, ...],
) -> None:
    """Bootstrap requires one Change and a tracked profile with no declaration."""
    repo = init_repo(tmp_path / "repo")
    profile = repo / ".ethos" / "profile.toml"
    profile.parent.mkdir(exist_ok=True)
    profile.write_text(profile_body, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "add adopter profile")
    if case == "untracked":
        git(repo, "rm", "--cached", ".ethos/profile.toml")
    if case != "missing-change":
        for name in change_names:
            (repo / "openspec" / "changes" / name).mkdir(parents=True)

    report = openspec_scope.material_change_scope_report(
        repo,
        changed_paths=(".ethos/profile.toml",),
        active_change_names=change_names,
    )

    assert report["state"] == "material_paths_missing"
    assert report["profile_bootstrap"] == {}
    assert report["required_gaps"] == ["openspec_material_paths_missing"]


def test_prewrite_rejects_material_profile_write_without_scope_companion(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """A material profile write cannot borrow an arbitrary active Change."""
    repo = init_repo(tmp_path / "repo")
    (repo / ".ethos").mkdir(exist_ok=True)
    (repo / ".ethos" / "profile.toml").write_text(
        '[openspec]\nmaterial_paths = [".ethos/profile.toml"]\n', encoding="utf-8"
    )
    git(repo, "add", ".")
    git(repo, "commit", "-m", "declare profile material path")
    worktree = _worktree(repo, tmp_path, monkeypatch)
    (worktree / "openspec" / "changes" / "unrelated").mkdir(parents=True)
    _mock_official_active_change(monkeypatch, "unrelated")

    report = prewrite_guard(
        root=worktree,
        paths=[worktree / ".ethos" / "profile.toml"],
        editor_root=worktree,
        require_editor_root=True,
    )

    assert report["ok"] is False
    assert report["error"] == "openspec_material_path_uncovered:.ethos/profile.toml"
