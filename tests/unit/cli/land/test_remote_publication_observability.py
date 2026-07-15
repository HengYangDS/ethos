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


def test_publish_projects_peer_complete_gitlab_and_github_planes_separately(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    head = git(repo, "rev-parse", "HEAD")
    seed_executed_proof(repo, head)
    write_role_policy(repo)
    for path in (
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
        ".github/workflows/ci.yml",
        ".github/pull_request_template.md",
        ".github/ISSUE_TEMPLATE/task.md",
    ):
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("surface\n", encoding="utf-8")
    release = repo / ".ethos" / "release.toml"
    release.write_text(
        release.read_text(encoding="utf-8")
        + """
[publication_topology]
mode = "three_layer_peer_complete"
primary_remote = "origin"
github_remote = "github"
provider_capabilities = ["repository", "ci_cd", "update", "distribution"]

[provider_profiles.gitlab]
provider = "gitlab"
remote = "origin"
role = "organization_primary_publication"
capabilities = ["repository", "ci_cd", "update", "distribution"]

[provider_profiles.gitlab.surfaces]
ci = ".gitlab-ci.yml"
review_template = ".gitlab/merge_request_templates/default.md"
issue_template = ".gitlab/issue_templates/task.md"

[provider_profiles.github]
provider = "github"
remote = "github"
role = "independent_complete_repository"
capabilities = ["repository", "ci_cd", "update", "distribution"]

[provider_profiles.github.surfaces]
ci = ".github/workflows/ci.yml"
review_template = ".github/pull_request_template.md"
issue_template = ".github/ISSUE_TEMPLATE/task.md"
""",
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
    assert payload["data"]["github_availability"]["remote"] == "github"
    topology = payload["data"]["publication_topology"]
    assert topology["operating_state"] == "github_peer_plane_available"
    assert topology["provider_capability_parity"]["equal"] is True
    assert topology["available_provider_planes"] == ["github"]
    assert topology["github_repository_plane_claimed"] is False
    assert topology["gitlab_primary_publication_claimed"] is False
    assert topology["gitlab_hosted_status_claimed"] is False
    assert topology["remote_publication_claimed"] is False
