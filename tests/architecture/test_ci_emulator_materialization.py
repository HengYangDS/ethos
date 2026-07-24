from __future__ import annotations

import importlib.util
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_ci_templates_module():
    module_path = ROOT / "tools/ci/ci_templates.py"
    spec = importlib.util.spec_from_file_location("ethos_test_ci_templates", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_local_emulator_wrappers_do_not_require_optional_flag_environment() -> None:
    base_env = os.environ.copy()
    base_env.pop("ETHOS_LOCAL_EMULATOR_DRY_RUN", None)
    base_env.pop("ETHOS_LOCAL_EMULATOR_ALLOW_UNTRACKED", None)
    cases = [
        (
            "tools/ci/scripts/run-github-local-emulator.sh",
            {"ETHOS_LOCAL_EMULATOR_DRY_RUN": "1"},
            True,
        ),
        ("tools/ci/scripts/run-gitlab-local-emulator.sh", {}, False),
    ]
    for script, extra_env, expected_dry_run in cases:
        result = subprocess.run(
            ["/bin/bash", script, "doctor"],
            cwd=ROOT,
            env=base_env | extra_env,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        assert payload["dry_run"] is expected_dry_run
        assert "unbound variable" not in result.stderr
        assert payload["hosted_github_status_claimed"] is False
        assert payload["hosted_gitlab_status_claimed"] is False


def test_local_emulator_wrappers_emit_non_claim_evidence_in_dry_run() -> None:
    env = os.environ.copy()
    env["ETHOS_LOCAL_EMULATOR_DRY_RUN"] = "1"
    for script, provider, output_dir in [
        (
            "tools/ci/scripts/run-github-local-emulator.sh",
            "github",
            "build/evidence/local-ci/github",
        ),
        (
            "tools/ci/scripts/run-gitlab-local-emulator.sh",
            "gitlab",
            "build/evidence/local-ci/gitlab",
        ),
    ]:
        result = subprocess.run(
            ["/bin/bash", script, "doctor"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        evidence_path = ROOT / output_dir / "doctor.json"
        persisted = json.loads(evidence_path.read_text(encoding="utf-8"))
        assert payload == persisted
        assert payload["provider"] == provider
        assert payload["dry_run"] is True
        assert payload["head_start"] == payload["head_end"] == payload["head"]
        assert payload["head_stable"] is True
        assert payload["git_start"]["changed_scope"]["untracked_count"] >= 0
        assert payload["git_end"]["changed_scope"]["untracked_preview_limit"] == 12
        assert payload["files"]["config"]["exists"] is True
        assert payload["files"]["projected_file"]["exists"] is True
        assert payload["files"]["template_file"]["exists"] is True
        assert payload["materialization"] == {
            "issue": "",
            "mode_allows_untracked": True,
            "normal_run_refuses_untracked_by_default": True,
            "untracked_allowed": False,
            "untracked_policy": "refuse_before_emulator_run",
        }
        assert payload["hosted_github_status_claimed"] is False
        assert payload["hosted_gitlab_status_claimed"] is False
        assert "local provider emulator evidence only" in payload["claim_boundary"]


def test_gitlab_emulator_runtime_state_stays_under_build_runtime() -> None:
    root_state = ROOT / ".gitlab-ci-local"
    if root_state.exists():
        for child in sorted(root_state.rglob("*"), reverse=True):
            if child.is_file() or child.is_symlink():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        root_state.rmdir()
    env = os.environ.copy()
    env["ETHOS_LOCAL_EMULATOR_DRY_RUN"] = "1"
    result = subprocess.run(
        ["/bin/bash", "tools/ci/scripts/run-gitlab-local-emulator.sh", "doctor"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["provider"] == "gitlab"
    assert "--state-dir" in payload["command"]
    assert "build/runtime/work/gitlab-ci-local" in payload["command"]
    assert not root_state.exists()


def test_gitlab_materialization_creates_an_independent_git_snapshot(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    git_commands: list[tuple[str, ...]] = []
    real_git = vars(ci_templates)["_git"]

    def recording_git(root: Path, *args: str, **kwargs) -> bytes:
        git_commands.append(args)
        return real_git(root, *args, **kwargs)

    monkeypatch.setattr(ci_templates, "_git", recording_git)
    repository = tmp_path / "repository"
    linked_worktree = tmp_path / "linked-worktree"
    state_dir = tmp_path / "runtime"
    subprocess.run(["git", "init", "--quiet", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(repository), "config", "user.name", "ETHOS test"], check=True)
    tracked = repository / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    deleted = repository / "deleted.txt"
    deleted.write_text("delete me\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "tracked.txt", "deleted.txt"], check=True)
    subprocess.run(["git", "-C", str(repository), "commit", "--quiet", "-m", "base"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "worktree", "add", "--detach", str(linked_worktree)],
        check=True,
    )
    (linked_worktree / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (linked_worktree / "deleted.txt").unlink()
    (linked_worktree / "added.txt").write_text("added\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(linked_worktree), "add", "-A"], check=True)
    expected_head = subprocess.run(
        ["git", "-C", str(linked_worktree), "rev-parse", "HEAD"],
        capture_output=True,
        check=True,
        text=True,
    ).stdout.strip()
    materialization = ci_templates.materialize_emulator_source(
        source_root=linked_worktree, state_dir=state_dir, expected_head=expected_head
    )
    snapshot = state_dir / "source"
    assert (linked_worktree / ".git").is_file()
    assert (snapshot / ".git").is_dir()
    assert (snapshot / "tracked.txt").read_text(encoding="utf-8") == "changed\n"
    assert not (snapshot / "deleted.txt").exists()
    assert (snapshot / "added.txt").read_text(encoding="utf-8") == "added\n"
    assert (
        subprocess.run(
            ["git", "-C", str(snapshot), "ls-files"], capture_output=True, check=True, text=True
        ).stdout
        == "added.txt\ntracked.txt\n"
    )
    assert materialization["kind"] == "independent_git_checkout"
    assert materialization["source_head"] == expected_head
    assert materialization["source_head_matches_expected"] is True
    assert materialization["uses_external_object_alternates"] is False
    assert any(command[:2] == ("bundle", "create") for command in git_commands)
    assert all(command[0] != "clone" for command in git_commands)
    assert not (state_dir / "source.bundle").exists()
    assert (
        subprocess.run(
            ["git", "-C", str(snapshot), "status", "--short"],
            capture_output=True,
            check=True,
            text=True,
        ).stdout
        == "A  added.txt\nD  deleted.txt\nM  tracked.txt\n"
    )


def test_local_emulator_normal_run_refuses_untracked_materialization(
    monkeypatch, tmp_path: Path
) -> None:
    ci_templates = _load_ci_templates_module()
    monkeypatch.setattr(ci_templates, "ROOT", tmp_path)
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    output = tmp_path / "github-run.json"
    untracked = tmp_path / "tests/provider-emulator-untracked.txt"
    untracked.parent.mkdir(parents=True, exist_ok=True)
    untracked.write_text("untracked\n", encoding="utf-8")
    result_code = ci_templates.emulator_evidence(
        "github", mode="run", dry_run=False, allow_untracked=False, output=output
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert result_code == 1
    assert payload["ok"] is False
    assert payload["materialization"]["mode_allows_untracked"] is False
    assert payload["materialization"]["untracked_allowed"] is False
    assert (
        "provider materialization can omit untracked files" in payload["materialization"]["issue"]
    )
    assert "tests/provider-emulator-untracked.txt" in payload["materialization"]["issue"]
    assert payload["hosted_github_status_claimed"] is False
    assert payload["hosted_gitlab_status_claimed"] is False
