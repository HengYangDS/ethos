from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_gitlab_visible_project_files_exist() -> None:
    required = {
        "CHANGELOG.md",
        "CONTRIBUTING.md",
        "LICENSE",
        ".gitlab-ci.yml",
        ".gitlab/merge_request_templates/default.md",
        ".gitlab/issue_templates/task.md",
    }

    files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if path.is_file()}

    assert required <= files


def test_contributing_declares_commit_and_signature_policy() -> None:
    text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

    assert "Conventional Commits" in text
    assert "SSH signing" in text
    assert "Yang HENG <heng.yang.ds@hotmail.com>" in text


def test_gitlab_ci_uses_ethos_public_command_plane() -> None:
    text = (ROOT / ".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "ethos self audit" in text
    assert "ethos report" in text
    assert "uv run --group dev pytest tests/unit tests/architecture -q" in text
    assert "wt " not in text
    assert "proof " not in text
