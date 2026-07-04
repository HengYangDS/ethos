from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.ethos_cli_runner import run_ethos
from tests.unit.context.test_retrieval import init_repo

if TYPE_CHECKING:
    from pathlib import Path


def test_assistants_context_index_is_dry_run_by_default(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos("assistants", "context-index", "--root", repo.as_posix(), "--json")

    assert payload["command"] == "assistants context-index"
    assert payload["state"] == "dry_run"
    assert payload["summary"]["storage"].endswith(".ethos/state/retrieval.sqlite")


def test_assistants_search_returns_source_verified_results(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    run_ethos(
        "assistants",
        "context-index",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--json",
    )

    payload = run_ethos(
        "assistants",
        "search",
        "workspace status schema validation",
        "--root",
        repo.as_posix(),
        "--json",
    )

    assert payload["command"] == "assistants search"
    assert payload["ok"] is True
    assert payload["data"]["selection"]["verified_count"] >= 1
    assert payload["data"]["selection"]["untrusted_context_label"] == "UNTRUSTED CONTEXT"
    assert payload["data"]["selection"]["query"] == "<redacted-query>"
    assert payload["data"]["selection"]["query_digest"].startswith("sha256:")
    assert "workspace status schema validation" not in str(payload["data"]["selection"])


def test_assistants_context_query_includes_projection_report(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    run_ethos(
        "assistants",
        "context-index",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--json",
    )

    payload = run_ethos(
        "assistants",
        "context",
        "--root",
        repo.as_posix(),
        "--query",
        "workspace status schema validation",
        "--json",
    )

    assert payload["command"] == "assistants context"
    assert payload["data"]["context"]["context_projection"]["untrusted_context_label"] == (
        "UNTRUSTED CONTEXT"
    )
    assert payload["data"]["context"]["context_projection"]["query"] == "<redacted-query>"
    assert payload["data"]["context"]["context_projection"]["selection"]["query"] == (
        "<redacted-query>"
    )
    assert "workspace status schema validation" not in str(payload["data"]["context"])


def test_assistants_context_query_redacts_secret_like_text(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos(
        "assistants",
        "context",
        "--root",
        repo.as_posix(),
        "--query",
        "sk-proj-1234567890abcdef1234567890abcdef",
        "--json",
    )

    projection = payload["data"]["context"]["context_projection"]
    assert projection["query"] == "<redacted-query>"
    assert projection["selection"]["query"] == "<redacted-query>"
    assert projection["query_digest"].startswith("sha256:")
    assert "sk-proj-1234567890abcdef1234567890abcdef" not in str(projection)


def test_assistants_context_query_propagates_missing_index_gap(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")

    payload = run_ethos(
        "assistants",
        "context",
        "--root",
        repo.as_posix(),
        "--query",
        "workspace status schema validation",
        "--json",
    )

    assert payload["state"] == "gapped"
    assert "context_index_missing" in payload["required_gaps"]
    assert payload["data"]["context"]["context_projection"]["selection"]["verified_count"] == 0


def test_context_retrieval_cannot_close_proof_gaps(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    before = run_ethos("prove", "--root", repo.as_posix(), "--json")

    run_ethos(
        "assistants",
        "context-index",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--json",
    )
    context = run_ethos(
        "assistants",
        "context",
        "--root",
        repo.as_posix(),
        "--query",
        "workspace status schema validation",
        "--json",
    )
    after = run_ethos("prove", "--root", repo.as_posix(), "--json")

    assert context["data"]["context"]["context_projection"]["selection"]["verified_count"] >= 1
    assert after["ok"] == before["ok"]
    assert after["state"] == before["state"]
    assert after["required_gaps"] == before["required_gaps"]
    assert "context_projection" not in after["data"]


def test_assistants_context_purge_requires_authorization(tmp_path: Path) -> None:
    repo = init_repo(tmp_path / "repo")
    run_ethos(
        "assistants",
        "context-index",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--json",
    )

    blocked = run_ethos(
        "assistants", "context-purge", "--root", repo.as_posix(), "--apply", "--json"
    )
    applied = run_ethos(
        "assistants",
        "context-purge",
        "--root",
        repo.as_posix(),
        "--apply",
        "--authorize",
        "--json",
    )

    assert blocked["state"] == "blocked"
    assert "context_purge_requires_authorization" in blocked["required_gaps"]
    assert applied["state"] == "purged"
    assert not (repo / ".ethos" / "state" / "retrieval.sqlite").exists()


def test_report_labels_context_projection_as_advisory() -> None:
    payload = run_ethos("report", "--json")

    assert payload["data"]["scores"]["context_projection"] == 1
    assert payload["data"]["context_projection"]["authority"] == "projection"
    assert payload["data"]["context_projection"]["can_close_required_gaps"] is False
    assert payload["data"]["context_projection"]["can_satisfy_proof"] is False
