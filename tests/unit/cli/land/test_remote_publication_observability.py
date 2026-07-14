from __future__ import annotations

import json
from typing import TYPE_CHECKING

import ethos.surface.cli.root.lifecycle as lifecycle_cli
from ethos.domain.land.publication import local_ci_fallback_evidence_status
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import write_role_policy

if TYPE_CHECKING:
    from pathlib import Path


def test_publish_labels_current_fallback_as_unprobed_when_origin_is_configured(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    git(repo, "remote", "add", "origin", "ssh://example.invalid/ethos.git")
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"ok": True, "head": head}) + "\n",
        encoding="utf-8",
    )

    payload = run_ethos("publish", "--json", cwd=repo)

    assert payload["data"]["remote_availability"]["state"] == "not_probed"
    assert payload["summary"]["next_publication_action"] == (
        "remote availability not probed; local-ci fallback evidence is current at HEAD"
    )


def test_current_fallback_marks_observed_remote_without_claiming_publication(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")
    manifest = repo / "build" / "evidence" / "local-ci" / "fallback.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({"ok": True, "head": head}) + "\n",
        encoding="utf-8",
    )

    status = local_ci_fallback_evidence_status(
        repo,
        current_head=head,
        remote_availability_state="available",
    )

    assert status["state"] == "current"
    assert status["next_action"] == (
        "remote availability observed; local-ci fallback evidence is current at HEAD"
    )


def test_publish_projects_gitlab_primary_and_github_mirror_separately(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    write_role_policy(repo)
    (repo / ".github" / "workflows").mkdir(parents=True)
    (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    release = repo / ".ethos" / "release.toml"
    release.write_text(
        release.read_text(encoding="utf-8")
        + """\n[publication_topology]\nmode = \"three_layer_dual_remote\"\nprimary_remote = \"origin\"\nprimary_provider = \"gitlab\"\nmirror_remote = \"github\"\nmirror_provider = \"github\"\nmirror_role = \"independent_mirror_distribution\"\nmirror_may_substitute_for = [\"update\", \"distribution\"]\nmirror_may_not_substitute_for = [\"gitlab_primary_publication\", \"gitlab_hosted_status\"]\n\n[mirror_profile]\nprovider = \"github\"\nremote = \"github\"\nrole = \"independent_mirror_distribution\"\n\n[mirror_profile.surfaces]\nci = \".github/workflows/ci.yml\"\n""",
        encoding="utf-8",
    )
    git(repo, "remote", "add", "origin", "ssh://gitlab.invalid/ethos.git")
    git(repo, "remote", "add", "github", "ssh://github.invalid/ethos.git")

    def availability(_repo: Path, remote: str = "origin") -> dict[str, object]:
        return {
            "kind": "git_remote_availability",
            "remote": remote,
            "state": "available" if remote == "github" else "unavailable",
            "available": remote == "github",
            "blocking": False,
            "required_gaps": [],
            "advisory_gaps": [],
        }

    monkeypatch.setattr(lifecycle_cli.git, "remote_availability", availability)
    payload = run_ethos("publish", "--probe-remote", "--json", cwd=repo)

    assert payload["data"]["remote_availability"]["remote"] == "origin"
    assert payload["data"]["mirror_availability"]["remote"] == "github"
    topology = payload["data"]["publication_topology"]
    assert topology["operating_state"] == "mirror_fallback_available"
    assert topology["github_mirror_substitutes_for"] == ["update", "distribution"]
    assert topology["gitlab_primary_publication_claimed"] is False
    assert topology["gitlab_hosted_status_claimed"] is False
    assert topology["remote_publication_claimed"] is False
