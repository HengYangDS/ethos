from __future__ import annotations

from pathlib import Path

import tomli_w

from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos
from tests.support.playbooks import write_v2_playbook_package


def _playbook_repo(
    path: Path,
    *,
    identifier: str = "docs-governance",
    subject: str = "changed-scope",
) -> Path:
    root = init_git_repo(path)
    skills_root = root / ".agents/skills"
    manifest = Path(write_v2_playbook_package(skills_root, identifier))
    (skills_root / "README.md").write_text("# Skills\n", encoding="utf-8")
    record = {
        "id": identifier,
        "package_manifest": manifest.relative_to(root).as_posix(),
        "subject": subject,
        "operation": "govern",
        "authority": "primary",
        "lifecycle": "active",
        "path_globs": ["docs/**"],
        "pre_reads": ["README.md"],
        "post_checks": ["ethos report --json"],
        "commands": ["ethos status"],
        "boundary": "workflow-package-projection",
    }
    (skills_root / "activation.toml").write_text(
        tomli_w.dumps({"meta": {"version": 2}, "skill": [record]}), encoding="utf-8"
    )
    git(root, "add", ".agents")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add playbook routing",
    )
    return root


def test_playbooks_changed_scope_in_work_lane_includes_committed_delta(
    tmp_path: Path,
) -> None:
    root = _playbook_repo(tmp_path / "repo")
    git(root, "branch", "candidate/dev")
    git(root, "checkout", "-b", "work/docs", "candidate/dev")
    (root / "docs").mkdir()
    (root / "docs/guide.md").write_text("# guide\n", encoding="utf-8")
    git(root, "add", "docs/guide.md")
    git(
        root,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        "add docs guide",
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert git(root, "status", "--porcelain") == ""
    assert payload["ok"] is True
    assert payload["data"]["changed_paths"] == ["docs/guide.md"]
    selected = payload["data"]["selected"][0]
    assert selected["id"] == "docs-governance"
    assert selected["matched_paths"] == ["docs/guide.md"]
    assert payload["data"]["unmatched_paths"] == []


def test_playbooks_changed_scope_without_changed_paths_selects_nothing(
    tmp_path: Path,
) -> None:
    root = _playbook_repo(tmp_path / "repo")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["required_gaps"] == []
    assert payload["data"]["changed_paths"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["unmatched_paths"] == []


def test_playbooks_changed_scope_reports_matched_changed_path_evidence(
    tmp_path: Path,
) -> None:
    root = _playbook_repo(tmp_path / "repo")
    (root / "docs").mkdir()
    (root / "docs/guide.md").write_text("# guide\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["data"]["changed_paths"] == ["docs/guide.md"]
    selected = payload["data"]["selected"][0]
    assert selected["id"] == "docs-governance"
    assert selected["matched_paths"] == ["docs/guide.md"]
    assert payload["data"]["unmatched_paths"] == []


def test_playbooks_changed_scope_reports_unmatched_changed_paths(
    tmp_path: Path,
) -> None:
    root = _playbook_repo(tmp_path / "repo")
    (root / "src").mkdir()
    (root / "src/app.py").write_text("print('hello')\n", encoding="utf-8")

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is False
    assert payload["data"]["selected"] == []
    assert "src/app.py" in payload["data"]["unmatched_paths"]
    assert "playbook_changed_path_unmatched:src/app.py" in payload["required_gaps"]


def test_playbooks_route_accepts_changed_scope_alias_without_changed_paths(
    tmp_path: Path,
) -> None:
    root = _playbook_repo(
        tmp_path / "repo", identifier="repository-governance", subject="repository-governance"
    )

    payload = run_ethos("playbooks", "route", "--changed", "--root", str(root), "--json")

    assert payload["ok"] is True
    assert payload["command"] == "playbooks route"
    assert payload["data"]["subject"] == "changed-scope"
    assert payload["data"]["changed"] is True
    assert payload["data"]["changed_paths"] == []
    assert payload["data"]["selected"] == []
    assert payload["data"]["unmatched_paths"] == []
