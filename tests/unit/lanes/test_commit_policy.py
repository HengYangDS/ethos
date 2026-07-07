# ruff: noqa: TC003
from __future__ import annotations

import subprocess
from pathlib import Path

from ethos.adapters.gates.signature import commit_subject_ok
from ethos.adapters.gates.signature import load_commit_policy
from ethos.adapters.gates.signature import signature_policy_report


def test_default_subject_policy_accepts_any_nonempty_subject() -> None:
    # The product ships without a house commit style: any nonempty subject passes.
    assert commit_subject_ok("Harden ETHOS framework core") is True
    assert commit_subject_ok("feat: mature ETHOS product governance") is True
    assert commit_subject_ok("") is False


def test_configured_subject_pattern_is_enforced() -> None:
    conventional = r"^(feat|fix|docs|test|refactor|perf|build|ci|chore|revert)(\([a-z0-9-]+\))?: .+"
    assert commit_subject_ok("feat: add gate", pattern=conventional) is True
    assert commit_subject_ok("Harden core", pattern=conventional) is False


def test_commit_policy_defaults_to_identity_agnostic(tmp_path: Path) -> None:
    # No .ethos/workspace.toml: the product enforces no author identity or signing.
    policy = load_commit_policy(tmp_path)
    assert policy["expected_name"] == ""
    assert policy["expected_email"] == ""
    assert policy["signing_required"] is False


def test_commit_policy_reads_adopter_binding(tmp_path: Path) -> None:
    ethos_dir = tmp_path / ".ethos"
    ethos_dir.mkdir()
    (ethos_dir / "workspace.toml").write_text(
        "[commit_policy]\n"
        'expected_name = "Ada Lovelace"\n'
        'expected_email = "ada@example.com"\n'
        "signing_required = true\n"
        'signing_format = "ssh"\n',
        encoding="utf-8",
    )
    policy = load_commit_policy(tmp_path)
    assert policy["expected_name"] == "Ada Lovelace"
    assert policy["expected_email"] == "ada@example.com"
    assert policy["signing_required"] is True
    assert policy["signing_format"] == "ssh"


def test_signature_policy_self_certifies_without_configured_identity(tmp_path: Path) -> None:
    # In a repo with no commit_policy binding, a present git identity self-certifies:
    # no mismatch gap is raised, and expected_author is empty (nothing to enforce).
    # Use an isolated git repo with its own identity so no ambient (global/parent)
    # git config leaks into the assertion.
    def _git(*args: str) -> None:
        subprocess.run(
            ["git", *args],
            cwd=tmp_path,
            check=True,
            text=True,
            capture_output=True,
        )

    _git("init", "-b", "main")
    _git("config", "user.name", "Some Contributor")
    _git("config", "user.email", "contributor@example.com")

    report = signature_policy_report(tmp_path)
    assert report["expected_author"] == ""
    assert "git_user_name_mismatch" not in report["required_gaps"]
    assert "git_user_email_mismatch" not in report["required_gaps"]
    assert "git_user_name_missing" not in report["required_gaps"]
    assert "git_user_email_missing" not in report["required_gaps"]


def test_signature_policy_uses_machine_readable_head_signature_status() -> None:
    report = signature_policy_report()

    assert report["head_signature_status"] in {"G", "B", "U", "X", "Y", "R", "E", "N", ""}
    assert report["head_signature_ok"] is (report["head_signature_status"] == "G")


def test_commit_policy_defaults_on_malformed_workspace_toml(tmp_path: Path) -> None:
    # Unparseable workspace.toml -> tomllib.TOMLDecodeError -> identity-agnostic default.
    ethos_dir = tmp_path / ".ethos"
    ethos_dir.mkdir()
    (ethos_dir / "workspace.toml").write_text("[commit_policy\n", encoding="utf-8")
    policy = load_commit_policy(tmp_path)
    assert policy["expected_name"] == ""
    assert policy["signing_required"] is False
