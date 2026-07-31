from __future__ import annotations

from pathlib import Path

from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked


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
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    docs = repo / "docs"
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
        repo.as_posix(),
        "--json",
    )

    assert payload["ok"] is False
    assert payload["state"] == "gapped"
    assert "gate_failed:docs-registry" in payload["required_gaps"]
    attestation = payload["data"]["attestation"]
    assert attestation["predicate"] == "proof:execution"
    assert attestation["subject"] == f"git:commit:{git(repo, 'rev-parse', 'HEAD')}"
    assert attestation["verdict"] == "block"
    assert len(attestation["commitment_digest"]) == 64
    assert len(attestation["facts_digest"]) == 64
    assert len(attestation["plan_digest"]) == 64
    assert len(attestation["policy_digest"]) == 64
    assert len(attestation["effect_digest"]) == 64
    assert attestation["evidence_refs"] == [f"sha256:{attestation['effect_digest']}"]
    statement = attestation["statement"]
    assert statement["repository"].startswith("repository:")
    assert statement["scope"]
    assert statement["plane"] == "local"
    assert statement["context"] == {"boundary": statement["boundary"]}
    assert statement["inputs"]["plan"] == attestation["plan_digest"]
    assert statement["output"]["artifact"] == attestation["effect_digest"]
    assert statement["freshness"]["head"] == git(repo, "rev-parse", "HEAD")
    assert not {"kind", "content", "mints_authority"} & set(attestation)
    assert "evidence" not in payload["data"]
    assert "provenance" not in payload["data"]


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
    assert "candidate_diverged_from_accepted" in payload["required_gaps"]
    assert payload["next_actions"] == [
        f"ethos lane candidate --refresh-from-accepted --apply --authorize --expect-head {accepted_head} --json"
    ]
    assert payload["data"]["accepted_update"] == {}
    assert payload["data"]["mutation"]["decision"]["verdict"] == "block"
    assert (
        "candidate_diverged_from_accepted" in payload["data"]["closeout_bootstrap"]["required_gaps"]
    )
