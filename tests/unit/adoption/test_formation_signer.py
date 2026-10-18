"""Exercise the reviewed SSH signer that signs a formed repository's initial commit."""

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.starter.formation as formation_effect
from ethos.domain.adoption import adopt_repository
from tests.support.fixture_signer import fixture_signer_inputs


def test_greenfield_unverified_initial_commit_publishes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A signing or trust failure in scratch leaves no target and no candidate worktree."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Verifiable changes.",
        "starter": "foundation",
        **fixture_signer_inputs(),
    }
    preview = adopt_repository(target, **request)
    monkeypatch.setattr(
        formation_effect,
        "create_git_commit",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            (), 1, "", "commit_signature_untrusted"
        ),
    )

    result = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert result.verdict == "block"
    assert result.required_gaps == ("formation_git_commit_failed",)
    assert result.data["detail"] == "commit_signature_untrusted"
    assert not target.exists()
    assert not target.with_name("new-project-candidate-dev").exists()


@pytest.mark.parametrize("missing", ["signing_key", "trust_anchor"])
def test_greenfield_without_a_signer_refuses_before_any_effect(
    tmp_path: Path, missing: str
) -> None:
    """Formation cannot start a governed repository with an unsigned commit."""
    target = tmp_path / "new-project"

    result = adopt_repository(
        target,
        create=True,
        purpose="Verifiable changes.",
        starter="foundation",
        **(fixture_signer_inputs() | {missing: ""}),
    )

    assert result.verdict == "block"
    assert result.required_gaps == ("formation_commit_signer_missing",)
    assert "--signing-key" in result.next_action
    assert "--trust-anchor" in result.next_action
    assert result.user_decision_required
    assert not target.exists()
    assert not target.with_name("new-project-candidate-dev").exists()


@pytest.mark.parametrize(
    ("field", "gap"),
    [
        ("signing_key", "git_effect_signing_key_invalid"),
        ("trust_anchor", "commit_trust_anchor_not_absolute"),
        ("signing_program", "git_effect_signing_program_invalid"),
    ],
)
def test_greenfield_rejects_an_invalid_signer_before_any_effect(
    tmp_path: Path, field: str, gap: str
) -> None:
    """An unusable signer is refused with the gap that a lifecycle commit reports."""
    target = tmp_path / "new-project"

    result = adopt_repository(
        target,
        create=True,
        purpose="Verifiable changes.",
        starter="foundation",
        **(fixture_signer_inputs() | {field: "relative-path"}),
    )

    assert result.verdict == "block"
    assert result.required_gaps == (gap,)
    assert "--signing-key" in result.next_action
    assert result.user_decision_required
    assert not target.exists()
