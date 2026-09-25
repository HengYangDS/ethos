"""Exercise formation as a distinct, explicit adoption request."""

import json
import os
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_lifecycle.candidate_projection as candidate_projection
import ethos.adapters.repo.formation as formation_effect
from ethos.domain.adoption import adopt_repository
from ethos.domain.inspection import inspect_repository
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.runtime_scenarios import install_fixture_hook_runtime

ROOT = Path(__file__).resolve().parents[3]


def test_brownfield_public_adopt_remains_two_binding_only(tmp_path: Path) -> None:
    """Minimal adoption is not silently upgraded into a project scaffolder."""
    root = init_git_repo(tmp_path / "existing")
    console = Path(sys.prefix) / ("Scripts/ethos.exe" if os.name == "nt" else "bin/ethos")

    def invoke(*options: str) -> dict[str, object]:
        completed = subprocess.run(
            [str(console), *options],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        return json.loads(completed.stdout)

    preview = invoke("adopt", "--root", str(root), "--json")
    assert preview["data"]["planned_files"] == [
        ".ethos/profile.toml",
        "openspec/config.yaml",
    ]
    assert not (root / ".ethos/profile.toml").exists()
    applied = invoke(
        "adopt",
        "--root",
        str(root),
        "--apply",
        "--authorize",
        "--expect-head",
        git(root, "rev-parse", "HEAD"),
        "--expect-plan-digest",
        str(preview["data"]["plan_digest"]),
        "--json",
    )
    status = invoke("status", "--root", str(root), "--json")

    assert applied["verdict"] == "pass"
    assert status["verdict"] == "block"
    assert "candidate_branch_missing" in status["required_gaps"]
    assert "lane candidate" not in status["next_action"]
    assert not (root / "AGENTS.md").exists()


def test_greenfield_preview_has_no_target_effect(tmp_path: Path) -> None:
    """A reviewed foundation exists before any repository or Git ref does."""
    target = tmp_path / "new-project"

    result = adopt_repository(
        target,
        create=True,
        purpose="Steward a new project with verifiable changes.",
        starter="foundation",
    )

    assert result.verdict == "pass"
    assert result.state == "planned"
    assert result.data["planned_files"] == (
        ".ethos/profile.toml",
        "AGENTS.md",
        "README.md",
        "openspec/config.yaml",
    )
    assert not target.exists()
    assert not list(tmp_path.glob(".ethos-preview-*"))


def test_greenfield_preview_is_public_cli_output(tmp_path: Path) -> None:
    """The installed-style CLI must not resolve an absent target as an existing repository."""
    target = tmp_path / "new-project"
    direct = adopt_repository(
        target,
        create=True,
        purpose="Steward a new project with verifiable changes.",
        starter="foundation",
    )
    console = Path(sys.prefix) / ("Scripts/ethos.exe" if os.name == "nt" else "bin/ethos")
    completed = subprocess.run(
        [
            str(console),
            "adopt",
            "--create",
            "--root",
            str(target),
            "--purpose",
            "Steward a new project with verifiable changes.",
            "--starter",
            "foundation",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["verdict"] == "pass"
    assert result["data"]["planned_files"] == [
        ".ethos/profile.toml",
        "AGENTS.md",
        "README.md",
        "openspec/config.yaml",
    ]
    assert result["data"]["plan_digest"] == direct.data["plan_digest"]
    assert result["data"]["write_plan"] == direct.to_dict()["data"]["write_plan"]
    assert not target.exists()


def test_greenfield_console_refuses_linked_target_before_runtime_selection(tmp_path: Path) -> None:
    """An existing linked target cannot select its own product to judge creation."""
    target = tmp_path / "linked-project"
    try:
        target.symlink_to(ROOT, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    console = Path(sys.prefix) / ("Scripts/ethos.exe" if os.name == "nt" else "bin/ethos")
    completed = subprocess.run(
        [
            str(console),
            "adopt",
            "--create",
            "--root",
            str(target),
            "--purpose",
            "Verifiable changes.",
            "--starter",
            "foundation",
            "--json",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["required_gaps"] == ["formation_target_exists"]


def test_greenfield_apply_forms_one_author_attributed_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The actual file and ref effects use one approved candidate and real Git identity."""
    target = tmp_path / "new-project"
    monkeypatch.setattr(
        candidate_projection,
        "install_hook_launchers",
        install_fixture_hook_runtime,
    )
    request = {
        "create": True,
        "purpose": "Steward a new project with verifiable changes.",
        "starter": "foundation",
    }
    preview = adopt_repository(target, **request)

    applied = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert applied.verdict == "pass"
    assert applied.state == "applied"
    assert git(target, "symbolic-ref", "--short", "HEAD") == "dev"
    assert git(target, "rev-parse", "HEAD") == git(target, "rev-parse", "candidate/dev")
    candidate = target.with_name("new-project-candidate-dev")
    assert candidate.is_dir()
    assert str(candidate) in git(target, "worktree", "list", "--porcelain")
    assert applied.data["candidate_worktree_path"] == str(candidate)
    assert git(target, "log", "-1", "--format=%an <%ae>") == ("ETHOS Test <test@example.invalid>")
    for row in preview.data["write_plan"]:
        path = target / str(row["path"])
        assert path.is_file()
        assert sha256(path.read_bytes()).hexdigest() == row["content_sha256"]
    guidance = (target / "AGENTS.md").read_text(encoding="utf-8")
    assert "ethos status --root . --json" in guidance
    assert str(ROOT) not in guidance
    assert not list(tmp_path.glob(".ethos-preview-*"))


@pytest.mark.parametrize("defect", ["unauthorized", "stale", "collision"])
def test_greenfield_apply_rejects_unadmitted_effects(tmp_path: Path, defect: str) -> None:
    """A stale request or foreign target cannot be overwritten."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Steward a new project with verifiable changes.",
        "starter": "foundation",
    }
    preview = adopt_repository(target, **request)
    if defect == "collision":
        target.mkdir()
        (target / "foreign.txt").write_text("preserve", encoding="utf-8")
    result = adopt_repository(
        target,
        **request,
        apply=True,
        authorize=defect != "unauthorized",
        expect_plan_digest="0" * 64 if defect == "stale" else str(preview.data["plan_digest"]),
    )

    assert result.verdict == "block"
    assert result.required_gaps
    if defect == "collision":
        assert (target / "foreign.txt").read_text(encoding="utf-8") == "preserve"
    else:
        assert not target.exists()


def test_greenfield_copy_failure_preserves_unknown_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial output is observed, not deleted or blindly regenerated."""
    target = tmp_path / "new-project"
    request = {
        "create": True,
        "purpose": "Steward a new project with verifiable changes.",
        "starter": "foundation",
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


def test_greenfield_candidate_path_collision_preserves_foreign_content(tmp_path: Path) -> None:
    """The candidate worktree is a reviewed effect, not an implicit sibling overwrite."""
    sibling = tmp_path / "new-project-candidate-dev"
    sibling.mkdir()
    (sibling / "foreign.txt").write_text("preserve", encoding="utf-8")
    target = tmp_path / "new-project"

    result = adopt_repository(
        target, create=True, purpose="Verifiable changes.", starter="foundation"
    )

    assert result.verdict == "block"
    assert result.required_gaps == ("formation_candidate_path_exists",)
    assert result.data["candidate_worktree_path"] == str(sibling)
    assert result.next_action.startswith(f"Inspect {sibling}")
    assert not target.exists()
    assert (sibling / "foreign.txt").read_text(encoding="utf-8") == "preserve"


def test_greenfield_preview_binds_purpose_and_identity(tmp_path: Path) -> None:
    """A changed semantic input invalidates a prior reviewed candidate."""
    target = tmp_path / "new-project"
    first = adopt_repository(target, create=True, purpose="First purpose.", starter="foundation")
    second = adopt_repository(target, create=True, purpose="Second purpose.", starter="foundation")
    third = adopt_repository(
        target,
        create=True,
        purpose="First purpose.",
        starter="foundation",
        author_name="Another Contributor",
        author_email="another@example.invalid",
    )

    assert (
        len({first.data["plan_digest"], second.data["plan_digest"], third.data["plan_digest"]}) == 3
    )


def test_greenfield_missing_identity_blocks_before_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Formation cannot fabricate a Git author or inherit another repository's identity."""
    for role in ("AUTHOR", "COMMITTER"):
        for field in ("NAME", "EMAIL"):
            monkeypatch.delenv(f"GIT_{role}_{field}", raising=False)
    target = tmp_path / "new-project"

    result = adopt_repository(
        target, create=True, purpose="Verifiable changes.", starter="foundation"
    )

    assert result.verdict == "block"
    assert result.required_gaps == ("formation_git_identity_missing",)
    assert "--author-name" in result.next_action
    assert "--author-email" in result.next_action
    assert not target.exists()


def test_greenfield_binds_canonical_parent_and_refuses_retarget(tmp_path: Path) -> None:
    """A reviewed alias cannot silently move the effect to a new destination."""
    actual = tmp_path / "actual"
    actual.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")

    preview = adopt_repository(
        linked / "new-project", create=True, purpose="Verifiable changes.", starter="foundation"
    )

    assert preview.verdict == "pass"
    assert preview.data["root"] == str(actual / "new-project")
    replacement = tmp_path / "replacement"
    replacement.mkdir()
    linked.unlink()
    linked.symlink_to(replacement, target_is_directory=True)

    result = adopt_repository(
        linked / "new-project",
        create=True,
        purpose="Verifiable changes.",
        starter="foundation",
        apply=True,
        authorize=True,
        expect_plan_digest=str(preview.data["plan_digest"]),
    )

    assert result.verdict == "block"
    assert result.required_gaps == ("formation_plan_digest_mismatch",)
    assert not (actual / "new-project").exists()
    assert not (replacement / "new-project").exists()


@pytest.mark.parametrize(
    ("starter", "purpose", "parent_kind", "gap", "hint"),
    [
        (
            "",
            "Verifiable changes.",
            "present",
            "formation_starter_unavailable",
            "Choose a supported",
        ),
        ("foundation", "", "present", "formation_purpose_missing", "Supply --purpose"),
        (
            "foundation",
            "Verifiable changes.",
            "missing",
            "formation_parent_unsafe",
            "Choose an existing",
        ),
    ],
)
def test_greenfield_missing_input_has_a_non_looping_action(
    tmp_path: Path, starter: str, purpose: str, parent_kind: str, gap: str, hint: str
) -> None:
    """A blocking preview asks for the missing decision instead of replaying itself."""
    target = (tmp_path / "absent" if parent_kind == "missing" else tmp_path) / "new-project"

    result = adopt_repository(target, create=True, purpose=purpose, starter=starter)

    assert result.required_gaps == (gap,)
    assert hint in result.next_action
    assert result.user_decision_required
    assert not target.exists()


def test_greenfield_runtime_failure_reobserves_created_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Post-copy runtime failure keeps the exact Git repository for safe recovery."""
    target = tmp_path / "new-project"
    request = {"create": True, "purpose": "Verifiable changes.", "starter": "foundation"}
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
    request = {"create": True, "purpose": "Verifiable changes.", "starter": "foundation"}
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
