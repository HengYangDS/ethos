from __future__ import annotations

from typing import TYPE_CHECKING

from tests.support.contract_helpers import git
from tests.support.contract_helpers import init_git_repo
from tests.support.ethos_cli_runner import run_ethos

if TYPE_CHECKING:
    from pathlib import Path


def test_plan_changed_in_work_lane_includes_committed_delta_from_candidate(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    rules = repo / ".ethos" / "rules.toml"
    rules.write_text(
        """
[gates.unit]
command = "pytest tests/unit"
blocking = true

[[rule]]
id = "python-source"
risk = "source-change"
paths = ["src/**"]
requires = ["unit"]
evidence = ["unit-test"]
""".lstrip(),
        encoding="utf-8",
    )
    source = repo / "src" / "demo.py"
    source.parent.mkdir()
    source.write_text("VALUE = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-gpg-sign",
        "--no-verify",
        "-m",
        "seed governed source",
    )
    git(repo, "branch", "candidate/dev")
    git(repo, "checkout", "-b", "work/feature", "candidate/dev")
    source.write_text("VALUE = 2\n", encoding="utf-8")
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--no-gpg-sign",
        "--no-verify",
        "-m",
        "change governed source",
    )

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert git(repo, "status", "--porcelain") == ""
    assert payload["data"]["changed_paths"] == ["src/demo.py"]
    assert payload["summary"]["matched_rule_count"] == 1
    assert payload["summary"]["required_gate_count"] == 1
    assert payload["data"]["matched_rules"][0]["matched_paths"] == ["src/demo.py"]


def test_plan_changed_in_work_lane_tolerates_missing_candidate_ref(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    git(repo, "checkout", "-b", "work/feature")

    payload = run_ethos("plan", "--root", repo.as_posix(), "--changed", "--json", cwd=repo)

    assert payload["summary"]["changed"] is True
    assert payload["data"]["changed_paths"] == []
