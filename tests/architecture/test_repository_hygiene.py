from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_repository_hygiene_policy_owns_hidden_root_residue_gate() -> None:
    policy = (ROOT / ".config/checks/repository-hygiene/policy.toml").read_text(encoding="utf-8")
    runner = (ROOT / "tools/ci/scripts/run-repository-hygiene.sh").read_text(encoding="utf-8")
    tools = (ROOT / "system/tools.toml").read_text(encoding="utf-8")

    assert "root_host_residue = [" in policy
    assert '".DS_Store"' in policy
    assert '"Thumbs.db"' in policy
    assert '"Desktop.ini"' in policy
    assert '"not handoff carrier"' in policy
    assert "stash_guidance_excluded_prefixes = [" in policy
    assert 'POLICY_PATH = Path(".config/checks/repository-hygiene/policy.toml")' in runner
    assert '"not handoff carrier"' in runner
    assert '"stash_guidance_excluded_prefixes"' in runner
    assert "host-local root residue is not repository truth" in runner
    assert 'concern = "repository_hygiene"' in tools
    assert 'config = ".config/checks/repository-hygiene/policy.toml"' in tools


def test_repository_hygiene_rejects_global_ignored_ds_store(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".config/checks/repository-hygiene").mkdir(parents=True)
    (repo / "tools/ci/scripts").mkdir(parents=True)
    shutil.copy2(
        ROOT / ".config/checks/repository-hygiene/policy.toml",
        repo / ".config/checks/repository-hygiene/policy.toml",
    )
    runner = repo / "tools/ci/scripts/run-repository-hygiene.sh"
    shutil.copy2(ROOT / "tools/ci/scripts/run-repository-hygiene.sh", runner)

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    (repo / ".DS_Store").write_bytes(b"host-local residue")

    completed = subprocess.run(
        ["tools/ci/scripts/run-repository-hygiene.sh"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert ".DS_Store: host-local root residue is not repository truth; remove it" in (
        completed.stdout + completed.stderr
    )


@pytest.mark.parametrize("policy_mode", ["default", "configured"])
@pytest.mark.parametrize(
    ("relative", "guidance", "expected"),
    [
        (
            "guidance.md",
            "Git stash\nand chat transcripts are not handoff carriers.\n",
            (0, ""),
        ),
        ("guidance.md", "Never use git stash as a closeout carrier.\n", (0, "")),
        ("guidance.md", "No git stash is permitted in this workflow.\n", (0, "")),
        (
            "guidance.md",
            "No remote, release, branch cleanup, or Git stash operation was performed.\n",
            (0, ""),
        ),
        (
            "guidance.md",
            "No foreign lane, dirty lane, remote, runner, branch cleanup, or worktree removal was\n"
            "performed; Git stash was not modified.\n",
            (0, ""),
        ),
        (
            "guidance.md",
            "No foreign lane, dirty lane, remote, runner, branch cleanup, or worktree removal,\n"
            "Git stash, or credential was\n"
            "modified.\n",
            (0, ""),
        ),
        (
            "guidance.md",
            "This bootstrap does not use Git stash as recovery machinery.\n",
            (0, ""),
        ),
        (
            "guidance.md",
            "## Out Of Scope\n\n- Wholesale merge, cherry-pick, or git stash.\n",
            (0, ""),
        ),
        (
            "guidance.md",
            "When blocked, git stash, then retry.\n",
            (1, "stash is not an accepted backup or closeout carrier"),
        ),
        (
            "guidance.md",
            "No review is required; git stash, then retry.\n",
            (1, "stash is not an accepted backup or closeout carrier"),
        ),
        (
            "evidence/chronicle/example/2026-07-18.md",
            "When blocked, git stash, then retry.\n",
            (0, ""),
        ),
        (
            "openspec/changes/archive/2026-07-18-example/proposal.md",
            "When blocked, git stash, then retry.\n",
            (0, ""),
        ),
    ],
)
def test_repository_hygiene_distinguishes_negative_and_positive_stash_guidance(
    tmp_path: Path,
    policy_mode: str,
    relative: str,
    guidance: str,
    expected: tuple[int, str],
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "tools/ci/scripts").mkdir(parents=True)
    runner = repo / "tools/ci/scripts/run-repository-hygiene.sh"
    shutil.copy2(ROOT / "tools/ci/scripts/run-repository-hygiene.sh", runner)
    if policy_mode == "configured":
        policy_path = repo / ".config/checks/repository-hygiene/policy.toml"
        policy_path.parent.mkdir(parents=True)
        shutil.copy2(ROOT / ".config/checks/repository-hygiene/policy.toml", policy_path)
    guidance_path = repo / relative
    guidance_path.parent.mkdir(parents=True, exist_ok=True)
    guidance_path.write_text(guidance, encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    completed = subprocess.run(
        ["tools/ci/scripts/run-repository-hygiene.sh"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    expected_returncode, expected_message = expected
    assert completed.returncode == expected_returncode
    assert expected_message in (completed.stdout + completed.stderr)
