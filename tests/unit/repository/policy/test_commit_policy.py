"""Compile optional commit policy once and reject malformed declarations."""

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
    ("old", "new", "error"),
    [
        ("[commit_policy]", "[commit_policy", "commit_policy_toml_invalid"),
        ("all", 'commit_policy = "implicit"', "commit_policy_invalid:must_be_table"),
        ("", 'identity_mode = "external"', "commit_policy_unknown_fields:identity_mode"),
        ('"^fix: .+"', "1", "commit_policy_invalid:subject_pattern"),
        ('"^fix: .+"', '"["', "commit_policy_subject_pattern_invalid"),
        ("", 'scopes = ["cli"]', "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', "scopes = []", "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', 'scopes = ["Cli"]', "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', 'scopes = ["cli", "cli"]', "commit_policy_invalid:scopes"),
        ('subject_pattern = "^fix: .+"', "scopes = [{}]", "commit_policy_invalid:scopes"),
        ("true", '"yes"', "commit_policy_invalid:signing_required"),
        ('"ssh"', '"openpgp"', "commit_policy_signing_format_unsupported:openpgp"),
    ],
)
def test_present_commit_policy_fails_closed(
    tmp_path: Path,
    old: str,
    new: str,
    error: str,
) -> None:
    valid = (
        '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
        'signing_required = true\nsigning_format = "ssh"\n'
    )
    text = new if old == "all" else valid.replace(old, new, 1) if old else valid + new
    assert text != valid
    _write_workspace(tmp_path, text)

    with pytest.raises((TypeError, ValueError), match=error):
        commit_policy.load_commit_policy(tmp_path)


@pytest.mark.parametrize(
    ("scopes", "accepted", "rejected"),
    [
        (
            "",
            ("feat(cli)!: drop the legacy flag", "fix: repair", "refactor(relay-core): split"),
            ("style: reformat", "spec(cli): add", "fix(Cli): repair", "fix:repair"),
        ),
        (
            'scopes = ["cli", "relay"]\n',
            ("fix(cli): repair", "feat(relay)!: rename", "docs: explain"),
            ("fix(other): repair", "style(cli): reformat"),
        ),
    ],
    ids=["shared-grammar", "declared-scopes"],
)
def test_an_omitted_subject_pattern_applies_the_shared_grammar(
    scopes: str, accepted: tuple[str, ...], rejected: tuple[str, ...]
) -> None:
    """Without a declared pattern the paradigm's grammar applies, restricted to declared scopes."""
    policy = commit_policy.commit_policy_from_text(
        f'[commit_policy]\n{scopes}signing_required = true\nsigning_format = "ssh"\n'
    )

    assert policy is not None
    assert all(policy.accepts_subject(subject) for subject in accepted)
    assert not any(policy.accepts_subject(subject) for subject in rejected)
    assert policy.projection().get("scopes", []) == list(policy.scopes)
