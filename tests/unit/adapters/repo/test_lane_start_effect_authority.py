"""Exact command-owned ref authority for fresh lane creation."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest

from ethos.adapters.repo.git_effect_admission import require_effect_permission
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Commitment
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

ZERO_OID = "0" * 40
HOLDER = "agent:test:lane-start"


def _plan(tmp_path: Path, flaw: str = "", *, source: bool = False):
    repo = init_git_repo(tmp_path / "repo")
    commit_fixture_file(
        repo,
        ".ethos/commitment.toml",
        'schema_version = 1\nid = "repository:repo"\n'
        'intent = "Govern."\nsubjects = ["repository:repo"]\n',
        "declare identity",
    )
    base = git(repo, "rev-parse", "HEAD")
    desired = git(repo, "commit-tree", "HEAD^{tree}", "-p", base, "-m", "lane carrier")
    branch = "work/example"
    candidate = "" if flaw == "candidate-absent" else "candidate/dev"
    update_ref = "refs/heads/work/other" if flaw == "ref" else f"refs/heads/{branch}"
    assertions = (
        {}
        if flaw in {"candidate-missing", "candidate-absent"}
        else {f"refs/heads/{candidate}": desired if flaw == "candidate-head" else base}
    )
    policy = {
        "operation": "other" if flaw == "operation" else "lane.start",
        "branch": "work/other" if flaw == "branch" else branch,
        "holder_ref": "agent:test:other" if flaw == "holder" else HOLDER,
        "candidate_branch": candidate,
    }
    if source:
        source_branch = "dev"
        source_head = desired if flaw == "source-head" else base
        policy |= {"source_branch": source_branch, "source_head": source_head}
        assertions[f"refs/heads/{source_branch}"] = base
    elif flaw == "unexpected-assertion":
        assertions["refs/heads/dev"] = base
    effect = GitEffect(
        updates={
            update_ref: GitRefUpdate(
                expected=base if flaw == "expected" else ZERO_OID,
                desired=desired,
            )
        },
        assertions=assertions,
    )
    generation = {
        "branch": branch,
        "lease_id": "lease:test",
        "epoch": 1,
        "holder_ref": HOLDER,
        "expected_head": base if flaw == "desired" else desired,
        "expected_tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "base_commitment_path": ".ethos/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "a" * 64,
        "expires_at": "2026-08-11T00:00:00+00:00",
        "payload_sha256": "b" * 64,
    }
    facts = Facts(
        repository="repository:repo",
        head=base,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={
            "refs": {name: update.expected for name, update in effect.updates.items()},
            "assertions": effect.assertions,
            "lease_generation": generation,
        },
    )
    commitment = Commitment(
        id="authority:test:lane-start",
        intent="Create one leased work lane.",
        subjects=("repository:repo",),
        permissions=("repository.read",) if flaw == "permission" else ("work-lane.write",),
    )
    return compile_git_effect_plan(
        commitment,
        facts,
        prior_attestations={},
        policy=policy,
        effect=effect,
    )


@pytest.mark.parametrize("mode", ["fresh", "source"])
def test_lane_start_authority_accepts_only_the_bound_creation(tmp_path: Path, mode: str) -> None:
    plan = _plan(tmp_path, source=mode == "source")

    require_effect_permission(git_effect_from_plan(plan), plan)


@pytest.mark.parametrize(
    "flaw",
    [
        "operation",
        "permission",
        "ref",
        "expected",
        "desired",
        "branch",
        "holder",
        "candidate-missing",
        "candidate-absent",
        "candidate-head",
        "unexpected-assertion",
        "source-head",
    ],
)
def test_lane_start_authority_rejects_every_unbound_dimension(tmp_path: Path, flaw: str) -> None:
    plan = _plan(tmp_path, flaw, source=flaw == "source-head")

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        require_effect_permission(git_effect_from_plan(plan), plan)
