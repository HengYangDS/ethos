# These boundary tests preserve patched subprocess signatures.

from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import TYPE_CHECKING

import ethos.adapters.mutation.lane_lifecycle.projection_rebase.core as source_budget
import ethos.adapters.mutation.lane_lifecycle.refresh as lane_refresh
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from tests.support.subprocesses import completed as cp

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True)
class _ClaimFixture:
    claim_id: str = "fine-grained-source-budget-scope-20260718"
    change_id: str = "fine-grained-source-budget-scope-20260718"
    subject: str = "quality:source-budget-proof-scope"
    state: str = "archived"
    scope: str = (
        "Default fine-grained promotion proof versus global source-budget compression closeout."
    )
    carrier: str = "openspec/changes/archive/2026-07-18-fine-grained-source-budget-scope-20260718"
    targets: object = None
    create_carrier: bool = True


def _write_claim(root: Path, fixture: _ClaimFixture | None = None) -> Path:
    fixture = fixture or _ClaimFixture()
    claim = root / "evidence" / "claims" / "fine-grained-source-budget-scope-20260718.toml"
    claim.parent.mkdir(parents=True, exist_ok=True)
    if fixture.create_carrier:
        (root / fixture.carrier).mkdir(parents=True, exist_ok=True)
    paths = list(source_budget.SOURCE_BUDGET_SCOPE_PATHS)
    claim.write_text(
        "\n".join(
            (
                "[claim]",
                f'id = "{fixture.claim_id}"',
                f'change_id = "{fixture.change_id}"',
                f'subject = "{fixture.subject}"',
                f'state = "{fixture.state}"',
                "",
                "[boundary]",
                f'scope = "{fixture.scope}"',
                "",
                "[carriers]",
                f'openspec = "{fixture.carrier}"',
                "",
                "[promotion]",
                f"targets = {paths if fixture.targets is None else fixture.targets!r}",
                "",
            )
        ),
        encoding="utf-8",
    )
    return claim


def test_archived_scope_reader_requires_exact_valid_carrier(tmp_path: Path) -> None:
    paths = list(source_budget.SOURCE_BUDGET_SCOPE_PATHS)
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False
    assert source_budget.archived_source_budget_scope_bound(tmp_path, ["README.md"]) is False

    claim = _write_claim(tmp_path, _ClaimFixture(create_carrier=False))
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False
    claim.write_text("not valid = [toml", encoding="utf-8")
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False

    _write_claim(tmp_path, _ClaimFixture(carrier="unexpected/carrier"))
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False
    _write_claim(tmp_path, _ClaimFixture(targets="not-a-list"))
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False
    _write_claim(tmp_path, _ClaimFixture(targets=paths[:-1]))
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False
    _write_claim(tmp_path)
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is True

    claim.write_text(
        "\n".join(
            (
                'claim = "invalid"',
                "",
                "[boundary]",
                'scope = "Default fine-grained promotion proof versus global source-budget compression closeout."',
                "",
                "[carriers]",
                'openspec = "openspec/changes/archive/2026-07-18-fine-grained-source-budget-scope-20260718"',
                "",
                "[promotion]",
                f"targets = {paths!r}",
                "",
            )
        ),
        encoding="utf-8",
    )
    assert source_budget.archived_source_budget_scope_bound(tmp_path, paths) is False


def test_candidate_scope_invariants_fail_closed(tmp_path: Path) -> None:
    paths = source_budget.SOURCE_BUDGET_SCOPE_PATHS

    def valid_git(_root: Path, *args: str, check: bool = True):
        del check
        outputs = {
            f":2:{paths[0]}": "def global_compression_report(repo):\n    return source_budget_report(repo)\n",
            f":2:{paths[1]}": "def test_scorecard_surfaces_global_compression_separately():\n    pass\n",
            f":2:{paths[2]}": 'assert "source-budget" in gate_graph(full=True)\n',
        }
        return cp(stdout=outputs[args[1]]) if args[1] in outputs else cp(returncode=1)

    assert all(
        source_budget.candidate_source_budget_scope_invariant(tmp_path, path, git=valid_git)
        for path in paths
    )
    assert (
        source_budget.candidate_source_budget_scope_invariant(tmp_path, "missing.py", git=valid_git)
        is False
    )

    def invalid_git(_root: Path, *args: str, check: bool = True):
        del args, check
        return cp(stdout="def global_compression_report(repo):\n")

    assert not any(
        source_budget.candidate_source_budget_scope_invariant(tmp_path, path, git=invalid_git)
        for path in paths
    )


def test_candidate_scope_context_requires_scorecard_and_proof_floor(
    tmp_path: Path,
) -> None:
    report = 'global_compression_report(repo)\n"global_compression": global_compression\n'
    gates = '[proof_sets]\nproduct_default = []\nproduct_full = ["source-budget"]\n'

    def valid_git(_root: Path, *args: str, check: bool = True):
        del check
        return cp(
            stdout=report if args[1].endswith(source_budget.SOURCE_BUDGET_REPORT_PATH) else gates
        )

    assert source_budget.candidate_source_budget_scope_context(tmp_path, "candidate", git=valid_git)

    def missing_git(_root: Path, *args: str, check: bool = True):
        del args, check
        return cp(returncode=1)

    assert (
        source_budget.candidate_source_budget_scope_context(tmp_path, "candidate", git=missing_git)
        is False
    )

    def malformed_git(_root: Path, *args: str, check: bool = True):
        del check
        return cp(stdout=report if args[1].endswith("report.py") else "[proof_sets")

    assert (
        source_budget.candidate_source_budget_scope_context(
            tmp_path, "candidate", git=malformed_git
        )
        is False
    )

    def incomplete_git(_root: Path, *args: str, check: bool = True):
        del check
        return cp(
            stdout=(
                report
                if args[1].endswith("report.py")
                else '[proof_sets]\nproduct_default = ["source-budget"]\nproduct_full = []\n'
            )
        )

    assert (
        source_budget.candidate_source_budget_scope_context(
            tmp_path, "candidate", git=incomplete_git
        )
        is False
    )


def test_archived_scope_resolver_refuses_each_missing_recovery_fact(
    monkeypatch, tmp_path: Path
) -> None:
    paths = list(source_budget.SOURCE_BUDGET_SCOPE_PATHS)
    _write_claim(tmp_path)

    def run_git(_root: Path, *args: str, check: bool = True):
        del check
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            return cp(stdout="\n".join(paths) + "\n")
        if args[:1] == ("checkout",):
            return cp(returncode=1)
        return cp(returncode=0)

    monkeypatch.setattr(source_budget, "run_git", run_git)
    monkeypatch.setattr(
        source_budget,
        "candidate_source_budget_scope_invariant",
        lambda *_args, **_kwargs: False,
    )
    assert source_budget.resolve_archived_source_budget_scope_conflict(tmp_path)["ok"] is False

    monkeypatch.setattr(
        source_budget,
        "candidate_source_budget_scope_invariant",
        lambda *_args, **_kwargs: True,
    )
    monkeypatch.setattr(
        source_budget,
        "candidate_source_budget_scope_context",
        lambda *_args, **_kwargs: False,
    )
    assert (
        source_budget.resolve_archived_source_budget_scope_conflict(
            tmp_path, candidate_head="candidate"
        )["ok"]
        is False
    )

    monkeypatch.setattr(
        source_budget,
        "candidate_source_budget_scope_context",
        lambda *_args, **_kwargs: True,
    )
    assert source_budget.resolve_archived_source_budget_scope_conflict(tmp_path)["ok"] is False

    def add_failure(_root: Path, *args: str, check: bool = True):
        del check
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            return cp(stdout="\n".join(paths) + "\n")
        if args[:1] == ("checkout",):
            return cp(returncode=0)
        if args[:1] == ("add",):
            return cp(returncode=1)
        return cp(returncode=0)

    monkeypatch.setattr(source_budget, "run_git", add_failure)
    assert source_budget.resolve_archived_source_budget_scope_conflict(tmp_path)["ok"] is False


def test_projection_rebase_preserves_exact_candidate_source_budget_scope(
    monkeypatch, tmp_path: Path
) -> None:
    paths = list(source_budget.SOURCE_BUDGET_SCOPE_PATHS)
    candidate = {
        paths[0]: "def global_compression_report(repo):\n    return source_budget_report(repo)\n",
        paths[1]: "def test_scorecard_surfaces_global_compression_separately():\n    pass\n",
        paths[2]: 'assert "source-budget" in [node.id for node in gate_graph(full=True).nodes]\n',
    }
    calls: list[tuple[str, ...]] = []
    diff_calls = 0

    def run_git(_root: Path, *args: str, check: bool = True):
        nonlocal diff_calls
        del check
        calls.append(args)
        if args[:3] == ("diff", "--name-only", "--diff-filter=U"):
            diff_calls += 1
            return cp(stdout="\n".join(paths) + "\n" if diff_calls <= 2 else "")
        if args[:1] == ("show",):
            stage_path = args[1]
            return (
                cp(returncode=1)
                if stage_path.startswith(":0:")
                else cp(stdout=candidate[stage_path.removeprefix(":2:")])
            )
        if args[:1] in {("checkout",), ("add",)}:
            return cp(returncode=0)
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp(returncode=0)
        return cp(returncode=1, stderr="unexpected git call")

    monkeypatch.setattr(source_budget, "run_git", run_git)
    monkeypatch.setattr(
        source_budget,
        "archived_source_budget_scope_bound",
        lambda _root, requested: requested == paths,
    )
    monkeypatch.setattr(
        source_budget,
        "candidate_source_budget_scope_context",
        lambda _root, _head, **_kwargs: True,
    )
    monkeypatch.setattr(
        source_budget,
        "candidate_source_budget_scope_invariant",
        lambda _root, path, **_kwargs: path in paths,
    )

    resolved = source_budget.resolve_projection_rebase(
        tmp_path, cp(returncode=1, stderr="source budget scope conflict")
    )

    assert resolved["ok"] is True
    assert resolved["paths"] == paths
    assert ("checkout", "--ours", "--", *paths) in calls
    assert ("add", *paths) in calls


def test_projection_rebase_rejects_unbound_source_budget_scope(monkeypatch, tmp_path: Path) -> None:
    paths = list(source_budget.SOURCE_BUDGET_SCOPE_PATHS)

    def run_git(_root: Path, *args: str, check: bool = True):
        del check
        return cp(stdout="\n".join(paths) + "\n") if args[:1] == ("diff",) else cp(returncode=1)

    monkeypatch.setattr(source_budget, "run_git", run_git)
    monkeypatch.setattr(
        source_budget,
        "archived_source_budget_scope_bound",
        lambda _root, _requested: False,
    )
    resolved = source_budget.resolve_projection_rebase(
        tmp_path, cp(returncode=1, stderr="unbound source budget scope conflict")
    )

    assert resolved["ok"] is False
    assert resolved["paths"] == []


def test_refresh_base_keeps_semantic_recovery_out_of_stale_projection_paths(
    monkeypatch, tmp_path: Path
) -> None:
    paths = list(source_budget.SOURCE_BUDGET_SCOPE_PATHS)
    heads = iter(("lane", "lane", "candidate", "rebased", "rebased"))
    ancestors = iter((False, True))

    def run_git(_root: Path, *args: str, check: bool = True):
        del check
        if args[:1] == ("rev-parse",):
            return cp(stdout=f"{next(heads)}\n")
        if args[:3] == ("-c", "rebase.updateRefs=false", "rebase"):
            return cp(returncode=1, stderr="source budget scope conflict")
        return cp(returncode=0)

    runtime = lane_refresh.LaneRefreshRuntime(
        load_branch_role_policy=lambda _root: SimpleNamespace(candidate_branch="candidate/dev"),
        workspace_status=lambda _root: {
            "role": ROLE_WORK_LANE,
            "dirty": False,
            "branch": "work/source-budget",
            "candidate": {
                "exists": True,
                "worktree_exists": True,
                "worktree_path": "candidate",
                "head": "candidate",
            },
        },
        changed_paths=lambda _path: [],
        is_ancestor=lambda *_args: next(ancestors),
        run_git=run_git,
    )
    monkeypatch.setattr(
        lane_refresh,
        "resolve_projection_rebase",
        lambda *_args, **_kwargs: {
            "ok": True,
            "paths": paths,
            "gaps": ["semantic_scope_preserved:source_budget_proof_scope"],
            "next_actions": ["rerun source-budget validation and HEAD-bound proof"],
            "stderr": "",
        },
    )

    report = lane_refresh.refresh_work_lane_base(
        root=tmp_path,
        apply=True,
        authorized=True,
        expect_head="lane",
        runtime=runtime,
    )

    assert report["state"] == "base_refreshed"
    assert report["projection_refresh_required"] is False
    assert report["stale_projection_paths"] == []
    assert report["semantic_recovery_paths"] == paths
