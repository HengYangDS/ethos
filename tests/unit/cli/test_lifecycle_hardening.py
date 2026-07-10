from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.repository.adoption.planner import adoption_plan
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


def git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "dev")
    (path / ".gitignore").write_text(".ethos/state/*\n!.ethos/state/.gitignore\n", encoding="utf-8")
    (path / "README.md").write_text("# sample\n", encoding="utf-8")
    (path / ".ethos" / "state").mkdir(parents=True)
    (path / ".ethos" / "state" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    git(path, "add", ".")
    git(
        path,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "init",
    )
    return path


def adopt_and_commit(repo: Path) -> None:
    plan = adoption_plan(repo, profile="generic", apply=True)
    assert plan["applied"] is True
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "adopt ethos governance",
    )


def seed_executed_proof(repo: Path, head: str) -> None:
    from ethos.adapters.mutation.proof import record_executed_proof
    from ethos.repository.evidence.core import EvidenceSet
    from ethos.repository.evidence.core import ProofRun

    run = ProofRun(
        action_id="python-tests",
        command=("pytest",),
        exit_code=0,
        stdout="",
        stderr="",
        state="proven",
        evidence_class="test",
        verdict="passed",
        trust_bearing=True,
        diagnostics=(),
    )
    record_executed_proof(repo, EvidenceSet.from_runs(id="proof", head=head, runs=(run,)).to_dict())


def _advance(repo: Path, path: str, text: str, message: str) -> str:
    target = repo / path
    target.write_text(text, encoding="utf-8")
    git(repo, "add", path)
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )
    return git(repo, "rev-parse", "HEAD")


def _diverged_candidate_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    candidate = tmp_path / "repo-candidate-dev"
    git(repo, "worktree", "add", "-b", "candidate/dev", candidate.as_posix(), "dev")
    old_candidate_head = _advance(candidate, "CANDIDATE.md", "# candidate\n", "advance candidate")
    accepted_head = _advance(repo, "ACCEPTED.md", "# accepted\n", "advance accepted")
    return repo, candidate, accepted_head, old_candidate_head


def test_prove_execute_reports_failed_gate_as_required_gap(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "guide.md").write_text(
        "---\nsubject: sample:guide\nrole: how-to\nstate: active\nrelations: {}\n---\n\n# Guide\n\nBody without required visible sections.",
        encoding="utf-8",
    )

    payload = run_ethos_blocked(
        "prove",
        "--execute",
        "--gate",
        "docs-registry",
        "--root",
        tmp_path.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "gate_failed:docs-registry" in payload["required_gaps"]


def test_lane_candidate_refresh_from_accepted_resets_clean_diverged_candidate(
    tmp_path: Path,
) -> None:
    repo, candidate, accepted_head, old_candidate_head = _diverged_candidate_repo(tmp_path)

    payload = run_ethos(
        "lane",
        "candidate",
        "--refresh-from-accepted",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "refreshed_from_accepted"
    assert payload["required_gaps"] == []
    assert payload["data"]["previous_head"] == old_candidate_head
    assert payload["data"]["head"] == accepted_head
    assert git(candidate, "rev-parse", "HEAD") == accepted_head


def test_lane_candidate_refresh_from_accepted_uses_official_ref_move_context(
    tmp_path: Path,
) -> None:
    repo, candidate, accepted_head, old_candidate_head = _diverged_candidate_repo(tmp_path)
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    hook_src = Path(__file__).resolve().parents[3] / ".githooks" / "reference-transaction"
    (hooks / "reference-transaction").write_text(
        hook_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (hooks / "reference-transaction").chmod(0o755)
    git(repo, "config", "core.hooksPath", hooks.as_posix())
    git(repo, "config", "ethos.acceptedBranch", "dev")

    payload = run_ethos(
        "lane",
        "candidate",
        "--refresh-from-accepted",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is True
    assert payload["state"] == "refreshed_from_accepted"
    assert payload["data"]["previous_head"] == old_candidate_head
    assert payload["data"]["head"] == accepted_head
    assert git(candidate, "rev-parse", "HEAD") == accepted_head
    assert git(candidate, "status", "--short") == ""


def test_land_closeout_reports_actionable_candidate_divergence(
    tmp_path: Path,
) -> None:
    repo, _candidate, accepted_head, _old_candidate_head = _diverged_candidate_repo(tmp_path)
    seed_executed_proof(repo, accepted_head)

    payload = run_ethos_blocked(
        "land",
        "--closeout",
        "--apply",
        "--authorize",
        "--expect-head",
        accepted_head,
        "--json",
        cwd=repo,
    )

    assert payload["ok"] is False
    assert payload["state"] == "blocked"
    assert payload["required_gaps"] == ["candidate_diverged_from_accepted"]
    assert payload["next_actions"] == [
        f"ethos lane candidate --refresh-from-accepted --apply --authorize --expect-head {accepted_head} --json"
    ]
    assert payload["data"]["accepted_update"] == {}
    assert payload["data"]["mutation"]["decision"]["verdict"] == "block"
    assert payload["data"]["closeout_bootstrap"]["required_gaps"] == [
        "candidate_diverged_from_accepted"
    ]
