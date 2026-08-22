from __future__ import annotations

import pytest
import tomli_w

from ethos.adapters.openspec.change_lineage.predecessor_resolution import (
    resolve_predecessor_commitments,
)
from ethos.adapters.repo.commitment import load_repository_commitment
from tests.support.governed_repository import git
from tests.support.governed_repository import init_repo_with_candidate
from tests.support.semantic import commitment_fixture


def test_resolve_predecessor_commitments_reads_one_exact_unambiguous_git_tree(
    tmp_path,
) -> None:
    repo, candidate = init_repo_with_candidate(tmp_path)
    historical = commitment_fixture(
        id="change:historical-change",
        intent="Preserve one exact historical predecessor.",
        subjects=(load_repository_commitment(candidate).id,),
    )
    carrier = candidate / ("openspec/changes/archive/2026-08-01-historical-change/commitment.toml")
    carrier.parent.mkdir(parents=True)
    carrier.write_text(
        tomli_w.dumps(historical.model_dump(mode="python")),
        encoding="utf-8",
    )
    git(candidate, "add", carrier.relative_to(candidate).as_posix())
    git(candidate, "commit", "-m", "record exact predecessor")
    exact_tree = git(candidate, "rev-parse", "HEAD")
    carrier.write_text("not the committed Commitment\n", encoding="utf-8")

    resolved = resolve_predecessor_commitments(
        repo,
        tree_ref=exact_tree,
        predecessors=(historical.digest(),),
    )
    assert resolved == (historical,)

    duplicate = candidate / (
        "openspec/changes/archive/2026-08-02-historical-change/commitment.toml"
    )
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text(tomli_w.dumps(historical.model_dump(mode="python")), encoding="utf-8")
    git(candidate, "add", duplicate.relative_to(candidate).as_posix())
    git(candidate, "commit", "-m", "duplicate predecessor carrier")

    with pytest.raises(
        ValueError,
        match=f"change_lineage_predecessor_ambiguous:{historical.digest()}",
    ):
        resolve_predecessor_commitments(
            repo,
            tree_ref=git(candidate, "rev-parse", "HEAD"),
            predecessors=(historical.digest(),),
        )
