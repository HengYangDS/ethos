from __future__ import annotations

from pathlib import Path

from ethos_workspace.mutation import MutationRequest, evaluate_mutation


def test_mutation_requires_authorization_and_expected_head() -> None:
    request = MutationRequest(command="land", apply=True, authorized=False, expect_head=None)

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is False
    assert "authorization_required" in result.gaps
    assert "expect_head_required" in result.gaps


def test_mutation_allows_dry_run_without_authorization() -> None:
    request = MutationRequest(command="land", apply=False, authorized=False, expect_head=None)

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is True
    assert result.state == "dry_run"


def test_mutation_apply_requires_matching_expected_head() -> None:
    request = MutationRequest(
        command="publish",
        apply=True,
        authorized=True,
        expect_head="abc123",
    )

    result = evaluate_mutation(request, root=Path.cwd(), current_head="abc123")

    assert result.ok is True
    assert result.state == "publish_ready"
