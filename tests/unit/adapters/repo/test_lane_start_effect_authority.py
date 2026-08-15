"""Exact command-owned ref authority for fresh lane creation."""

from datetime import UTC
from datetime import datetime
from pathlib import Path

import pytest
import tomli_w

from ethos.adapters.repo.commitment import load_repository_commitment
from ethos.adapters.repo.git_effect_admission import require_effect_permission
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.plan import compile_git_effect_plan
from ethos.contracts.plan import git_effect_from_plan
from ethos.contracts.semantic import Facts
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import commitment_v2

ZERO_OID = "0" * 40
HOLDER = "agent:test:lane-start"


def _plan(tmp_path: Path, flaw: str = "", *, source: bool = False):
    repo = init_git_repo(tmp_path / "repo")
    repository_id = f"repository:{repo.name}"
    commit_fixture_file(
        repo,
        ".ethos/commitment.toml",
        tomli_w.dumps(
            commitment_v2(
                id=repository_id,
                intent="Govern.",
                subjects=(repository_id,),
            ).model_dump(mode="python")
        ),
        "declare identity",
    )
    repository_id = load_repository_commitment(repo).id
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
    if source:
        source_branch = "dev"
        source_head = desired if flaw == "source-head" else base
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
    policy = {
        "operation": "other" if flaw == "operation" else "git.ref.compare-and-swap",
        "transition": "lane.start",
        "effect_digest": "0" * 64 if flaw == "effect-digest" else effect.digest(),
        "branch": "work/other" if flaw == "branch" else branch,
        "holder_ref": "agent:test:other" if flaw == "holder" else HOLDER,
        "candidate_branch": candidate,
    }
    if source:
        policy |= {"source_branch": source_branch, "source_head": source_head}
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
        repository=repository_id,
        head=base,
        tree=git(repo, "rev-parse", "HEAD^{tree}"),
        observed_at=datetime(2026, 8, 10, tzinfo=UTC),
        values={
            "refs": {name: update.expected for name, update in effect.updates.items()},
            "assertions": effect.assertions,
            "lease_generation": generation,
        },
    )
    commitment = commitment_v2(
        id="authority:test:lane-start",
        intent="Create one leased work lane.",
        subjects=(repository_id,),
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


@pytest.mark.parametrize("flaw", ["operation", "effect-digest"])
def test_lane_start_authority_rejects_nonprimitive_or_digest_mismatch(
    tmp_path: Path, flaw: str
) -> None:
    plan = _plan(tmp_path, flaw, source=flaw == "source-head")

    with pytest.raises(ValueError, match="git_effect_permission_denied"):
        require_effect_permission(git_effect_from_plan(plan), plan)
