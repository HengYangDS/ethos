"""Public lifecycle projections preserve native command inputs and boundary reports."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.lane_lifecycle.archive.command as archive
import ethos.adapters.mutation.lane_lifecycle.change_overlay as overlay
import ethos.application.lane.admission as admission
import ethos.application.lane.lifecycle as lifecycle
import ethos.application.lane.repair as repair
from ethos.application.catalog import invoke
from ethos.application.land.closeout import closeout_continuation
from ethos.application.land.closeout import land_next_action
from ethos.application.lane.result import lane_result
from ethos.contracts.operations.catalog import COMMANDS
from tests.support.ethos_cli_runner import PYTHONPATH
from tests.support.ethos_cli_runner import run_ethos_raw

ARCHIVE_BRANCH = "work/feature"
ARCHIVE_HEAD = "old-head"
ARCHIVE_CHANGE = "fixture-change"


def test_lane_halves_forward_their_exact_requests(monkeypatch, tmp_path):
    """A start keeps its explicit base, and a signer trust its exact authority coordinates."""
    captured: dict[str, object] = {}

    def capture(*args: object, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs, args=args)
        return {"verdict": "pass", "state": "planned"}

    monkeypatch.setattr(lifecycle, "start_work_lane", capture)
    monkeypatch.setattr(repair, "authorize_configured_commit_signer", capture)
    invoke("lane start", tmp_path, {"name": "work", "base": "b" * 40, "holder_ref": "agent:t"})
    assert (captured["root"], captured["base"], captured["path"]) == (tmp_path, "b" * 40, None)
    request = {"target_commit": "a" * 40, "expected_anchor_sha256": "b" * 64, "apply": True}
    invoke("lane trust-commit-signer", tmp_path, request | {"authorize": True})
    assert captured["args"] == (tmp_path, "a" * 40)
    assert captured["expected_anchor_sha256"] == "b" * 64
    assert captured["authorized"] is captured["apply"] is True


@pytest.mark.parametrize("gap", ["proof_not_proven", "full_proof_required"])
def test_transition_continuations_request_the_admitted_proof_floor(gap):
    """Missing and insufficient proof must not lead through a knowingly weaker run."""
    command = f"ethos prove --full --execute --expect-head {ARCHIVE_HEAD} --json"
    assert land_next_action(verdict="block", gaps=(gap,), current_head=ARCHIVE_HEAD) == command


@pytest.mark.parametrize(
    "gap",
    [
        "gate_registry_invalid:system/gates.toml",
        "proof_attestation_repository_policy_mismatch",
        "predecessor_policy_probe_timeout",
    ],
)
def test_predecessor_policy_gap_does_not_recommend_repeating_proof(gap: str) -> None:
    """A source proof cannot repair a predecessor reader or policy mismatch."""
    assert land_next_action(verdict="block", gaps=(gap,), current_head=ARCHIVE_HEAD) == (
        "inspect and repair installed-runtime policy compatibility before landing"
    )


@pytest.mark.parametrize(("source", "current"), [("old", False), ("old", True), ("", False)])
def test_closeout_bootstraps_when_its_advance_stales_the_hook_runtime(
    tmp_path: Path, source: str, *, current: bool
) -> None:
    """Only a hook runtime armed at the replaced accepted head leads through bootstrap first."""
    binding = {"current": current, "source_commit": source}
    root = tmp_path.resolve().as_posix()
    action = closeout_continuation(
        binding, root=tmp_path, accepted_head="old", candidate_head="new"
    )
    publish = f"ethos publish --expect-head new --root {root} --json"
    assert action == (f"mise --cd {root} run bootstrap" if source and not current else publish)


_ACTION = "ethos lane prewrite <path>"


@pytest.mark.parametrize(
    ("report", "passed", "state"),
    [
        ({"verdict": "pass", "next_action": _ACTION}, "ready", "ready"),
        ({"verdict": "pass", "state": "planned", "role": "work_lane"}, "admitted", "admitted"),
        (
            {"verdict": "unknown", "required_gaps": ["editor_root_unavailable"]},
            "admitted",
            "unknown",
        ),
        ({"verdict": "block", "required_gaps": ["lane_start_blocked"]}, "", "blocked"),
        ({"verdict": "pass", "next_action": _ACTION}, "", "ready"),
        ({"verdict": "pass", "state": "refreshed", "next_action": "ethos land"}, "", "refreshed"),
        (
            {"verdict": "block", "state": "partial_transition", "required_gaps": ["x"]},
            "",
            "partial_transition",
        ),
    ],
)
def test_public_projection_is_structured_and_actionable(
    report: dict[str, Any], passed: str, state: str
) -> None:
    """A report keeps its verdict, gaps and next action; its state is the command's own reading."""
    result = lane_result("lane x", report, passed=passed)

    assert (result.verdict, result.state) == (report["verdict"], state)
    assert result.required_gaps == tuple(report.get("required_gaps", ()))
    assert result.next_action == report.get("next_action", "")
    assert result.to_dict()["data"] == report


def test_prewrite_binds_each_path_spelling_and_reads_the_patch_on_stdin(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`--paths X`, `--paths=X` and `--patch -` bind through the CLI, which reads standard input."""
    captured: dict[str, object] = {}
    monkeypatch.setattr(
        admission,
        "prewrite_guard",
        lambda **kwargs: captured.update(kwargs) or {"verdict": "block", "required_gaps": ["gap"]},
    )
    monkeypatch.setattr(sys, "stdin", io.StringIO("diff --git a/a b/a\n"))
    root = tmp_path.resolve()
    paths = ("--paths", "README.md", "--paths=bad\npath", "--patch", "-")
    completed = run_ethos_raw(
        *("lane", "prewrite", *paths, "--editor-root", str(root), "--require-editor-root"),
        *("--root", str(root), "--json"),
        cwd=root,
    )

    assert completed.returncode == 1, completed.stderr
    assert captured["paths"] == [root / "README.md", Path("bad\npath")]
    assert (captured["editor_root"], captured["patch"]) == (root, "diff --git a/a b/a\n")
    assert json.loads(completed.stdout)["data"]["path_count"] == 2


def test_lane_prewrite_builds_only_its_own_half_and_group(tmp_path: Path) -> None:
    """A `lane prewrite` run imports no other command's half and builds no other group's App."""
    program = (
        "import json, sys\n"
        f"sys.argv = ['ethos', 'lane', 'prewrite', 'README.md', '--root', {str(tmp_path)!r}]\n"
        "from ethos import cli\n"
        "from ethos.application.catalog import IMPLEMENTATIONS\n"
        "from ethos.surface.cli.application import app\n"
        "try:\n    cli.main()\nexcept SystemExit:\n    pass\n"
        "halves = {row.partition(':')[0] for row in IMPLEMENTATIONS.values()} & set(sys.modules)\n"
        "groups = (app.resolved_commands(), app['lane'].resolved_commands())\n"
        "print(json.dumps([sorted(halves), *map(sorted, groups)]))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-B", "-c", program],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": PYTHONPATH},
        cwd=tmp_path,
        timeout=120,
    )

    assert completed.stdout.strip(), completed.stderr
    halves, roots, lane = (
        [name for name in names if not name.startswith("-")]
        for names in json.loads(completed.stdout.splitlines()[-1])
    )
    assert (halves, roots) == (["ethos.application.lane.admission"], ["lane"])
    assert lane == sorted({name.split()[1] for name in COMMANDS if name.startswith("lane ")})


class _WorkLanePolicy:
    def role_for_branch(self, _branch: str) -> str:
        return "work_lane"


@pytest.mark.parametrize(
    ("lease", "actor", "expected_gap", "expected_state", "expected_action"),
    [
        (
            {},
            "agent:test",
            f"work_lane_missing_lease:{ARCHIVE_BRANCH}",
            "lease_missing",
            "ethos lane status --json",
        ),
        (
            {
                "lease_state": "expired",
                "lane_ref": ARCHIVE_BRANCH,
                "holder_ref": "agent:test",
                "generation": 7,
                "expires_at": "2026-08-20T00:00:00Z",
            },
            "agent:test",
            f"work_lane_lease_expired:{ARCHIVE_BRANCH}",
            "lease_expired",
            (
                "ethos lane lease resume --generation 7 "
                "--expires-at 2026-08-20T00:00:00Z "
                f"--branch {ARCHIVE_BRANCH} "
                "--holder-ref agent:test --apply --json"
            ),
        ),
        (
            {
                "lease_state": "valid",
                "lane_ref": ARCHIVE_BRANCH,
                "holder_ref": "agent:other",
                "generation": 1,
                "expires_at": "2026-08-30T00:00:00Z",
            },
            "agent:test",
            "lease_actor_mismatch",
            "different_holder",
            (
                "ethos attestation query --predicate lane-resolution:takeover "
                f"--subject git:branch:{ARCHIVE_BRANCH} --json"
            ),
        ),
    ],
)
def test_work_lane_transition_reports_the_first_exact_lease_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    lease: dict[str, object],
    actor: str,
    expected_gap: str,
    expected_state: str,
    expected_action: str,
) -> None:
    monkeypatch.setattr(overlay, "load_branch_role_policy", lambda _root: _WorkLanePolicy())
    monkeypatch.setattr(overlay, "git_stdout", lambda *_args: "")

    gaps = overlay.work_lane_transition_gaps(
        tmp_path,
        branch=ARCHIVE_BRANCH,
        head=ARCHIVE_HEAD,
        expect_head=ARCHIVE_HEAD,
        lease=lease,
        actor=actor,
        role_gap="archive_requires_work_lane",
    )

    assert gaps == [expected_gap]
    report = archive.archive_preflight_report(
        ARCHIVE_BRANCH, ARCHIVE_HEAD, ARCHIVE_CHANGE, gaps, lease=lease
    )
    assert report["state"] == expected_state
    assert report["next_action"] == expected_action
