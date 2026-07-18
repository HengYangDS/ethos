from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ethos.domain.land.publication import local_ci_fallback_evidence_status
from tests.support.contract_helpers import adopt_and_commit
from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.contract_helpers import seed_executed_proof
from tests.support.ethos_cli_runner import run_ethos

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
