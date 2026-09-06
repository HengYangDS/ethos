from __future__ import annotations

from pathlib import Path

import pytest

import ethos.repository.policy.commit as commit_policy

ROOT = Path(__file__).resolve().parents[4]


def _write_workspace(root: Path, text: str) -> None:
    path = root / ".ethos/workspace.toml"
    path.parent.mkdir(parents=True)
    path.write_text(text, encoding="utf-8")


def test_missing_commit_policy_adds_no_repository_constraint(tmp_path: Path) -> None:
    assert commit_policy.load_commit_policy(tmp_path) is None


def test_current_repository_commit_policy_compiles_through_the_unique_owner() -> None:
    policy = commit_policy.load_commit_policy(ROOT)

    assert policy is not None
    assert policy.accepts_subject("fix(policy): close commit authority")


def test_commit_policy_compiles_the_exact_supported_shape(tmp_path: Path) -> None:
    _write_workspace(
        tmp_path,
        r"""[commit_policy]
subject_pattern = "^(feat|fix)(\\([a-z-]+\\))?: .+"
signing_required = true
signing_format = "ssh"
""",
    )

    policy = commit_policy.load_commit_policy(tmp_path)

    assert policy is not None
    assert policy.subject_pattern == r"^(feat|fix)(\([a-z-]+\))?: .+"
    assert policy.signing_required is True
    assert policy.signing_format == "ssh"
    assert policy.accepts_subject("fix(runtime): bind signer") is True
    assert policy.accepts_subject("bootstrap Commitment v2") is False


def test_commit_policy_compiles_from_one_already_observed_snapshot() -> None:
    policy = commit_policy.commit_policy_from_text(
        r"""[commit_policy]
subject_pattern = "^fix: .+"
signing_required = true
signing_format = "ssh"
"""
    )

    assert policy is not None
    assert policy.accepts_subject("fix: replay current intent")


@pytest.mark.parametrize(
    ("text", "error"),
    [
        ("[commit_policy\n", "commit_policy_toml_invalid"),
        ('commit_policy = "implicit"\n', "commit_policy_invalid:must_be_table"),
        (
            """[commit_policy]
subject_pattern = "^fix: .+"
signing_required = true
signing_format = "ssh"
identity_mode = "external"
""",
            "commit_policy_unknown_fields:identity_mode",
        ),
        (
            '[commit_policy]\nsigning_required = true\nsigning_format = "ssh"\n',
            "commit_policy_invalid:subject_pattern",
        ),
        (
            """[commit_policy]
subject_pattern = "["
signing_required = true
signing_format = "ssh"
""",
            "commit_policy_subject_pattern_invalid",
        ),
        (
            """[commit_policy]
subject_pattern = "^fix: .+"
signing_required = "yes"
signing_format = "ssh"
""",
            "commit_policy_invalid:signing_required",
        ),
        (
            """[commit_policy]
subject_pattern = "^fix: .+"
signing_required = true
signing_format = "openpgp"
""",
            "commit_policy_signing_format_unsupported:openpgp",
        ),
    ],
)
def test_present_commit_policy_fails_closed(
    tmp_path: Path,
    text: str,
    error: str,
) -> None:
    _write_workspace(tmp_path, text)

    with pytest.raises((TypeError, ValueError), match=error):
        commit_policy.load_commit_policy(tmp_path)
