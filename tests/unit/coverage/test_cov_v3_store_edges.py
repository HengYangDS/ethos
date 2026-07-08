"""Coverage-closure v3: store reachable branches (100% no-exemption)."""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from ethos.adapters.store import state
from ethos.adapters.store.retrieval import common as retrieval_common
from ethos.adapters.store.retrieval import indexing as retrieval_indexing
from ethos.adapters.store.retrieval import query as retrieval_query
from ethos.adapters.store.retrieval import schema as retrieval_schema
from ethos.adapters.store.retrieval import sources as retrieval_sources
from ethos_core.contracts.context.projection import redact_secret_like

if TYPE_CHECKING:
    import pytest


def _init_repo(root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Isolate from ambient git identity/config so nothing leaks into the fixture repo.
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", "/dev/null")
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=root, check=True, capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
        capture_output=True,
    )


def _commit_all(root: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=root, check=True, capture_output=True)


def test_tracked_files_returns_empty_outside_git_repo(tmp_path: Path) -> None:
    # git ls-tree exits non-zero when root is not a repo -> sources.py returns [].
    assert retrieval_sources.tracked_files(tmp_path) == []


def test_dirty_allowed_sources_returns_empty_outside_git_repo(tmp_path: Path) -> None:
    # git status exits non-zero when root is not a repo -> sources.py returns [].
    assert retrieval_sources.dirty_allowed_sources(tmp_path) == []


def test_is_allowed_source_rel_accepts_package_readme() -> None:
    # A README under packages/ matches the endswith/startswith guard -> sources.py.
    assert retrieval_sources.is_allowed_source_rel("packages/foo/README.md") is True


def test_unsafe_source_reason_flags_symlink(tmp_path: Path) -> None:
    # A symlink whose resolved target stays inside the repo reaches sources.py.
    repo = tmp_path.resolve()
    target = repo / "real.md"
    target.write_text("x", encoding="utf-8")
    link = repo / "link.md"
    link.symlink_to(target)

    assert retrieval_sources.unsafe_source_reason(repo, link) == "symlink_source"


def test_chunks_for_splits_on_headings_and_falls_back_to_rel_title() -> None:
    # A heading past index 0 triggers the mid-loop flush; a bare "#" heading
    # yields an empty title so the code takes the `or rel` fallback.
    chunks = retrieval_indexing.chunks_for(
        "packages/x.py", "intro\n# Heading\nbody\n## Sub\nmore\n#\ntail\n"
    )
    titles = [chunk["title"] for chunk in chunks]

    assert "Heading" in titles
    assert "Sub" in titles
    assert titles.count("packages/x.py") >= 2


def test_signature_for_returns_empty_for_non_callable_node() -> None:
    # A non-class/non-function node falls past both isinstance guards.
    node = ast.parse("x = 1").body[0]

    assert retrieval_indexing.signature_for(node) == ""


def test_kind_for_classifies_claim_and_schema() -> None:
    # evidence/claims/ prefix; schemas/ prefix.
    assert retrieval_indexing.kind_for("evidence/claims/c.md", Path("c.md")) == "claim"
    assert retrieval_indexing.kind_for("schemas/s.json", Path("s.json")) == "schema"


def test_verify_candidate_flags_state_path_as_not_allowed(tmp_path: Path) -> None:
    # A candidate under .ethos/state/ satisfies the first disjunct.
    repo = tmp_path.resolve()
    candidate = {
        "path": ".ethos/state/secret.txt",
        "start_line": 1,
        "end_line": 1,
        "digest": "d0",
        "file_digest": "f0",
        "head": "untracked",
        "score": 1.0,
    }

    result = retrieval_query.verify_candidate(repo, candidate)

    assert result["verification"]["status"] == "unverified"
    assert result["verification"]["reason"] == "path_not_allowed_source"


def test_redact_secret_like_masks_secret() -> None:
    # Delegates to the contract redactor for a secret-like value.
    redacted = redact_secret_like("api_key=ABCDEFGHIJKLMNOP")

    assert "<redacted-secret>" in redacted
    assert "ABCDEFGHIJKLMNOP" not in redacted


def test_rebuild_unlinks_existing_index_files_on_second_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A second authorized rebuild finds the prior index file present, exercising the
    # `if path.exists(): path.unlink()` cleanup.
    repo = tmp_path.resolve()
    _init_repo(repo, monkeypatch)
    (repo / "README.md").write_text("# Title\n\ncontent about ethos retrieval\n", encoding="utf-8")
    module = repo / "packages" / "demo" / "mod.py"
    module.parent.mkdir(parents=True)
    module.write_text("def alpha():\n    return 1\n", encoding="utf-8")
    _commit_all(repo)

    first = retrieval_indexing.rebuild_context_index(repo, apply=True, authorized=True)
    second = retrieval_indexing.rebuild_context_index(repo, apply=True, authorized=True)

    assert first["state"] == "indexed"
    assert second["state"] == "indexed"


def test_context_eval_report_counts_stale_search_as_critical(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # An initialized-but-empty index in a committed repo makes search return ok=False (stale
    # head), so context_eval_report increments critical_stale_hits.
    repo = tmp_path.resolve()
    _init_repo(repo, monkeypatch)
    (repo / "README.md").write_text("# Title\n\nseed\n", encoding="utf-8")
    _commit_all(repo)
    retrieval_schema.initialize_context_index(retrieval_common.default_retrieval_db_path(repo))

    report = retrieval_query.context_eval_report(repo, suite="smoke")

    assert report["ok"] is False
    assert report["required_gaps"] == ["context_eval_smoke_failed"]
    assert report["data"]["metrics"]["critical_stale_hits"] == 1


def test_verify_candidate_digest_mismatch_falls_through_to_return(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A tracked, allowed, head-matching, existing path whose digests differ makes the final
    # verification `if` False, so control flows straight to the return.
    repo = tmp_path.resolve()
    _init_repo(repo, monkeypatch)
    (repo / "README.md").write_text("# Title\n\nactual body\n", encoding="utf-8")
    _commit_all(repo)
    candidate = {
        "path": "README.md",
        "start_line": 1,
        "end_line": 1,
        "digest": "deadbeef",
        "file_digest": "deadbeef",
        "head": retrieval_common.git_head(repo),
        "score": 1.0,
    }

    result = retrieval_query.verify_candidate(repo, candidate)

    assert result["verification"]["status"] == "stale"
    assert result["verification"]["reason"] == "digest_mismatch"


def test_json_object_returns_empty_on_invalid_json() -> None:
    # Non-JSON payload raises JSONDecodeError -> state.py:281-282 returns {}.
    assert state._json_object("{not valid json") == {}
