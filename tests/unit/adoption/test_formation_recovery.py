"""Formation recovery observes a created repository instead of replaying or deleting it."""

from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.repo.starter.formation as formation_effect
from ethos.domain.adoption import adopt_repository
from ethos.domain.inspection import inspect_repository
from tests.support.fixture_signer import fixture_signer_inputs
from tests.support.governed_repository import git
from tests.support.runtime_scenarios import install_fixture_hook_runtime


def test_greenfield_copy_failure_preserves_unknown_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial output is observed, not deleted or blindly regenerated."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Steward a new project with verifiable changes.",
        "starter": "foundation",
        **fixture_signer_inputs(),
    }
    preview = adopt_repository(target, **request)

    def partial_copy(_candidate: Path, destination: Path, **_options: object) -> None:
        destination.mkdir()
        (destination / "foreign.txt").write_text("preserve", encoding="utf-8")
        message = "copy interrupted"
        raise OSError(message)

    monkeypatch.setattr(formation_effect.shutil, "copytree", partial_copy)
    result = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert result.verdict == "unknown"
    assert (target / "foreign.txt").read_text(encoding="utf-8") == "preserve"
    assert "Inspect" in result.next_action


def test_greenfield_runtime_failure_reobserves_created_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-copy runtime failure keeps the exact Git repository for safe recovery."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Verifiable changes.",
        "starter": "foundation",
        **fixture_signer_inputs(),
    }
    preview = adopt_repository(target, **request)

    def fail_activation(_root: Path) -> None:
        message = "runtime unavailable"
        raise ValueError(message)

    monkeypatch.setattr(candidate_projection, "install_hook_launchers", fail_activation)
    result = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert result.verdict == "unknown"
    assert git(target, "symbolic-ref", "--short", "HEAD") == "dev"
    assert result.next_action.startswith("ethos status --root ")
    candidate = target.with_name("new-project-candidate-dev")
    assert candidate.is_dir()
    head = git(target, "rev-parse", "HEAD")
    blocked = inspect_repository(target)
    assert blocked.verdict == "block"
    assert " -I -m ethos.cli hook install --root " in blocked.next_action
    assert str(target) in blocked.next_action

    monkeypatch.setattr(
        candidate_projection, "install_hook_launchers", install_fixture_hook_runtime
    )
    recovered = candidate_projection.bootstrap_candidate(
        root=target, path=candidate, expect_head=head, apply=True
    )

    assert recovered["verdict"] == "pass"
    assert recovered["state"] == "present"
    assert git(target, "rev-parse", "HEAD") == head
    assert git(candidate, "rev-parse", "HEAD") == head
    assert inspect_repository(target).verdict == "pass"


def test_greenfield_worktree_failure_selects_recovery_before_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A completed ref effect must lead to worktree recovery, not a fresh formation."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Verifiable changes.",
        "starter": "foundation",
        **fixture_signer_inputs(),
    }
    preview = adopt_repository(target, **request)

    def fail_worktree(*_args: object, **_kwargs: object) -> None:
        message = "worktree unavailable"
        raise OSError(message)

    with monkeypatch.context() as failure:
        failure.setattr(candidate_projection, "add_worktree", fail_worktree)
        result = adopt_repository(
            target,
            **request,
            apply=True,
            authorize=True,
            expect_plan_digest=str(preview.data["plan_digest"]),
        )

    candidate = target.with_name("new-project-candidate-dev")
    head = git(target, "rev-parse", "HEAD")
    assert result.verdict == "unknown"
    assert git(target, "rev-parse", "candidate/dev") == head
    assert not candidate.exists()
    blocked = inspect_repository(target)
    assert blocked.verdict == "block"
    assert "lane candidate" in blocked.next_action
    assert blocked.user_decision_required

    monkeypatch.setattr(
        candidate_projection, "install_hook_launchers", install_fixture_hook_runtime
    )
    recovered = candidate_projection.bootstrap_candidate(
        root=target, path=candidate, expect_head=head, apply=True
    )
    assert recovered["verdict"] == "pass"
    assert git(target, "rev-parse", "HEAD") == head
    assert git(candidate, "rev-parse", "HEAD") == head
    assert inspect_repository(target).verdict == "pass"


@pytest.mark.parametrize(
    ("failure", "gap"),
    [
        ("copied-bytes", "formation_postimage_mismatch"),
        ("runtime-observation", "formation_runtime_observation_required"),
        ("candidate-exception", "formation_effect_observation_required"),
    ],
)
def test_greenfield_postpublication_failures_preserve_recovery_boundary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str, gap: str
) -> None:
    """A published target is observed, not silently rolled back or replayed."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Verifiable changes.",
        "starter": "foundation",
        "author_name": "Test Contributor",
        "author_email": "test@example.invalid",
        **fixture_signer_inputs(),
    }
    preview = adopt_repository(target, **request)
    assert preview.verdict == "pass"
    monkeypatch.setattr(
        candidate_projection, "install_hook_launchers", install_fixture_hook_runtime
    )
    if failure == "copied-bytes":
        original_copy = formation_effect.shutil.copytree

        def altered_copy(source: Path, destination: Path, *args, **kwargs):
            copied = original_copy(source, destination, *args, **kwargs)
            if Path(destination) == target:
                (target / "README.md").write_text("changed after copy\n", encoding="utf-8")
            return copied

        monkeypatch.setattr(formation_effect.shutil, "copytree", altered_copy)
    elif failure == "runtime-observation":
        monkeypatch.setattr(
            formation_effect,
            "hook_runtime_binding",
            lambda _target: {"current": False, "required_gaps": ["runtime_unavailable"]},
        )
    else:

        def no_candidate(**_kwargs):
            message = "candidate observation unavailable"
            raise OSError(message)

        monkeypatch.setattr(formation_effect, "bootstrap_candidate", no_candidate)
    result = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )
    assert result.verdict == "unknown"
    assert result.required_gaps == (gap,)
    assert git(target, "symbolic-ref", "--short", "HEAD") == "dev"
    assert git(target, "rev-parse", "HEAD")
