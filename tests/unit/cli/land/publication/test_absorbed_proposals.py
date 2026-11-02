"""An accepted publication names the proposals it absorbed and their exact retirement."""

from __future__ import annotations

import shlex
import subprocess
from typing import TYPE_CHECKING
from typing import Any

import ethos.adapters.mutation.publication.absorption as absorption
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import apply_accepted_closeout
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.proof import seed_executed_proof
from tests.unit.cli.land.publication.support import PROPOSAL_REF
from tests.unit.cli.land.publication.support import apply_receipt
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

SIDE_REF = "refs/heads/proposal/side"


def accepted_with_proposals(tmp_path: Path) -> tuple[Path, str]:
    """Hold one absorbed and one unabsorbed proposal on plain Git peers behind accepted dev."""
    repo, remotes, old = branch_publication_fixture(tmp_path)
    release = repo / ".ethos/release.toml"
    text = release.read_text().replace('provider = "gitlab"', 'provider = "git"')
    release.write_text(text.replace('provider = "github"', 'provider = "git"'))
    head = commit_fixture(repo, "chore: declare plain Git peers")
    seed_executed_proof(repo, head)
    apply_accepted_closeout(repo, old, head)
    side = git(repo, "commit-tree", f"{old}^{{tree}}", "-p", old, "-m", "side proposal")
    for remote in remotes:
        git(repo, "push", remote, f"{head}:{PROPOSAL_REF}", f"{side}:{SIDE_REF}")
    return repo, head


def publish_dev(repo: Path, head: str) -> dict[str, Any]:
    preview = branch_publication(repo, head, target_ref="refs/heads/dev")
    return apply_receipt(repo, preview["data"]["request_receipt"], head)


def test_accepted_publication_names_the_proposals_it_absorbed(tmp_path: Path) -> None:
    repo, head = accepted_with_proposals(tmp_path)

    applied = publish_dev(repo, head)

    assert applied["state"] == "published"
    assert applied["data"]["absorbed_proposals"] == {
        "gitlab": [PROPOSAL_REF],
        "github": [PROPOSAL_REF],
    }
    assert applied["data"]["absorbed_proposals_unobserved"] == []
    command = shlex.split(str(applied["next_action"]))
    assert command[:3] == ["ethos", "publish", "--retire"]
    assert [command[i + 1] for i, word in enumerate(command) if word == "--ref"] == [PROPOSAL_REF]
    assert [command[i + 1] for i, word in enumerate(command) if word == "--peer"] == [
        "gitlab",
        "github",
    ]
    assert run_ethos(*command[1:], cwd=repo)["state"] == "ready_to_retire"


def test_an_unreadable_proposal_listing_is_reported_not_read_as_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, head = accepted_with_proposals(tmp_path)
    network = absorption.git.run_network_git

    def unavailable_listing(root, *args, **kwargs):
        if args[:2] == ("ls-remote", "github") and args[-1].endswith("*"):
            raise subprocess.TimeoutExpired(("git", *args), 30)
        return network(root, *args, **kwargs)

    monkeypatch.setattr(absorption.git, "run_network_git", unavailable_listing)

    applied = publish_dev(repo, head)

    assert (applied["verdict"], applied["state"]) == ("pass", "published")
    assert applied["data"]["absorbed_proposals"] == {"gitlab": [PROPOSAL_REF]}
    assert applied["data"]["absorbed_proposals_unobserved"] == ["github"]
