from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_lifecycle.projection_rebase.core as projection_rebase
import ethos.adapters.mutation.lane_lifecycle.refresh as lane_refresh
from ethos_core.contracts.branch.roles import ROLE_WORK_LANE
from tests.support.subprocesses import completed as cp

if TYPE_CHECKING:
    from pathlib import Path

SCOPE_ID = "fine-grained-source-budget-scope-20260718"
SCOPE_PATHS = (
    "packages/ethos/src/ethos/domain/reporting/scoring.py",
    "tests/unit/domain/test_report.py",
    "tests/unit/governance/validation/test_gates.py",
)
REPORT_PATH = "packages/ethos/src/ethos/domain/report.py"
GATES_PATH = "system/gates.toml"
CARRIER = f"openspec/changes/archive/2026-07-18-{SCOPE_ID}"


def _write_claim(
    root: Path,
    *,
    targets: object = SCOPE_PATHS,
    carrier: str = CARRIER,
    create_carrier: bool = True,
) -> None:
    claim = root / "evidence" / "claims" / f"{SCOPE_ID}.toml"
    claim.parent.mkdir(parents=True, exist_ok=True)
    if create_carrier:
        (root / carrier).mkdir(parents=True, exist_ok=True)
    claim.write_text(
        "\n".join(
            (
                "[claim]",
                f'id = "{SCOPE_ID}"',
                f'change_id = "{SCOPE_ID}"',
                'subject = "quality:source-budget-proof-scope"',
                'state = "archived"',
                "",
                "[boundary]",
                'scope = "Default fine-grained promotion proof versus global source-budget compression closeout."',
                "",
                "[carriers]",
                f'openspec = "{carrier}"',
                "",
                "[promotion]",
                f"targets = {list(targets) if isinstance(targets, (list, tuple)) else targets!r}",
            )
        ),
        encoding="utf-8",
    )


def _git(  # noqa: C901
    calls: list[tuple[str, ...]],
    *,
    case: str = "",
):
    candidate = {
        SCOPE_PATHS[
            0
        ]: "def global_compression_report(repo):\n    return source_budget_report(repo)\n",
        SCOPE_PATHS[1]: "def test_scorecard_surfaces_global_compression_separately():\n    pass\n",
        SCOPE_PATHS[2]: 'assert "source-budget" in gate_graph(full=True)\n',
    }
    report = 'global_compression_report(repo)\n"global_compression": global_compression\n'
    gates = '[proof_sets]\nproduct_default = []\nproduct_full = ["source-budget"]\n'

    def run(  # noqa: C901, PLR0911, RUF100 - test double enumerates exact Git responses
        _root: Path, *args: str, check: bool = True
    ):
        del check
        calls.append(args)
        if args[:1] == ("diff",):
            return cp(stdout="\n".join(SCOPE_PATHS) + "\n")
        if args[:1] == ("show",):
            ref = args[1]
            if ref.startswith(":0:"):
                return cp(returncode=1)
            if ref.startswith(":2:"):
                if case == "missing_candidate":
                    return cp(returncode=1)
                text = candidate[ref.removeprefix(":2:")]
                return cp(stdout="invalid" if case == "invalid_candidate" else text)
            if ref.endswith(REPORT_PATH):
                return cp(returncode=1) if case == "invalid_context" else cp(stdout=report)
            if ref.endswith(GATES_PATH):
                if case == "malformed_context":
                    return cp(stdout="[proof_sets")
                if case == "wrong_proof_boundary":
                    return cp(
                        stdout='[proof_sets]\nproduct_default = ["source-budget"]\nproduct_full = []\n'
                    )
                return cp(stdout=gates)
        if args[:1] == (case.removesuffix("_failure"),) and case.endswith("_failure"):
            return cp(returncode=1)
        if args[:1] in {("checkout",), ("add",)}:
            return cp()
        if args == ("-c", "core.editor=true", "rebase", "--continue"):
            return cp()
        return cp(returncode=1, stderr="unexpected git call")

    return run


def test_projection_rebase_preserves_exact_candidate_source_budget_scope(
    monkeypatch, tmp_path: Path
) -> None:
    _write_claim(tmp_path)
    calls: list[tuple[str, ...]] = []
    monkeypatch.setattr(projection_rebase, "run_git", _git(calls))

    resolved = projection_rebase.resolve_projection_rebase(
        tmp_path,
        cp(returncode=1, stderr="source budget scope conflict"),
        candidate_head="candidate",
    )

    assert resolved["ok"] is True
    assert resolved["paths"] == list(SCOPE_PATHS)
    assert resolved["gaps"] == ["semantic_scope_preserved:source_budget_proof_scope"]
    assert ("checkout", "--ours", "--", *SCOPE_PATHS) in calls
    assert ("add", *SCOPE_PATHS) in calls


@pytest.mark.parametrize(
    "case",
    [
        "missing_claim",
        "invalid_claim",
        "wrong_carrier",
        "missing_carrier",
        "non_list_targets",
        "wrong_targets",
        "invalid_candidate",
        "missing_candidate",
        "invalid_context",
        "malformed_context",
        "wrong_proof_boundary",
        "checkout_failure",
        "add_failure",
    ],
)
def test_projection_rebase_rejects_unbound_or_unwritable_source_budget_scope(
    monkeypatch,
    tmp_path: Path,
    case: str,
) -> None:
    if case != "missing_claim":
        _write_claim(
            tmp_path,
            targets=(
                "not-a-list"
                if case == "non_list_targets"
                else (SCOPE_PATHS[0],)
                if case == "wrong_targets"
                else SCOPE_PATHS
            ),
            carrier="unexpected/carrier" if case == "wrong_carrier" else CARRIER,
            create_carrier=case != "missing_carrier",
        )
    if case == "invalid_claim":
        (tmp_path / "evidence" / "claims" / f"{SCOPE_ID}.toml").write_text(
            '[claim]\nid = "bad"\n', encoding="utf-8"
        )
    monkeypatch.setattr(
        projection_rebase,
        "run_git",
        _git([], case=case),
    )

    resolved = projection_rebase.resolve_projection_rebase(
        tmp_path,
        cp(returncode=1, stderr="unbound source budget scope conflict"),
        candidate_head="candidate",
    )

    assert resolved["ok"] is False
    assert resolved["paths"] == []


def test_projection_rebase_has_a_bounded_recovery_loop(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(projection_rebase, "MAX_PROJECTION_REBASE_STEPS", 0)
    report = projection_rebase.resolve_projection_rebase(tmp_path, cp(returncode=1))
    assert report["stderr"] == "projection rebase recovery exceeded bounded step limit"


def test_refresh_base_keeps_semantic_recovery_out_of_stale_projection_paths(
    monkeypatch, tmp_path: Path
) -> None:
    heads = iter(("lane", "lane", "candidate", "rebased", "rebased"))
    ancestors = iter((False, True))

    def run_git(_root: Path, *args: str, check: bool = True):
        del check
        if args[:1] == ("rev-parse",):
            return cp(stdout=f"{next(heads)}\n")
        if args[:3] == ("-c", "rebase.updateRefs=false", "rebase"):
            return cp(returncode=1, stderr="source budget scope conflict")
        return cp()

    monkeypatch.setattr(
        lane_refresh,
        "load_branch_role_policy",
        lambda _root: SimpleNamespace(candidate_branch="candidate/dev"),
    )
    monkeypatch.setattr(
        lane_refresh,
        "workspace_status",
        lambda _root: {
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
    )
    monkeypatch.setattr(lane_refresh, "changed_paths", lambda _path: [])
    monkeypatch.setattr(lane_refresh, "is_ancestor", lambda *_args: next(ancestors))
    monkeypatch.setattr(lane_refresh, "run_git", run_git)
    monkeypatch.setattr(
        lane_refresh,
        "resolve_projection_rebase",
        lambda *_args, **_kwargs: {
            "ok": True,
            "paths": list(SCOPE_PATHS),
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
    )

    assert report["state"] == "base_refreshed"
    assert report["projection_refresh_required"] is False
    assert report["stale_projection_paths"] == []
    assert report["semantic_recovery_paths"] == list(SCOPE_PATHS)
