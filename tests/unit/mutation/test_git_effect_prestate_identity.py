"""Pre-state revisions keep their historical identity; produced revisions meet today's schema."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.admission.evidence.external as evidence
from ethos.adapters.admission.control.replacement import control_replacement_report
from ethos.adapters.repo.git_effect_observation import observe_git_effect
from ethos.adapters.repo.git_effect_observation import resolve_git_effect_repository
from ethos.contracts.plan import GitEffect
from ethos.contracts.plan import GitRefUpdate
from ethos.contracts.semantic import canonical_json_digest
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.git_effect import fixture
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import start_adopted_candidate
from tests.support.lane_scenarios import add_candidate_worktree
from tests.support.proof import seed_executed_proof

if TYPE_CHECKING:
    from pathlib import Path

RETIRED_SCHEMA = '\n[retired]\nformat = "ruff-json"\n'


@pytest.mark.parametrize(
    ("retired_role", "retired_identity", "expected"),
    [
        ("expected", "repo", "repository:repo"),
        ("asserted", "repo", "repository:repo"),
        ("desired", "repo", "repository_profile_invalid"),
        ("expected", "other", "git_effect_repository_identity_mismatch"),
    ],
)
def test_prestate_identity_survives_a_retired_profile_schema(
    tmp_path: Path, retired_role: str, retired_identity: str, expected: str
) -> None:
    """A retired accepted schema keeps its identity; the produced revision stays strict."""
    case = fixture(tmp_path)
    profile = (case.repo / ".ethos/profile.toml").read_text(encoding="utf-8")
    retired = commit_fixture_file(
        case.repo,
        ".ethos/profile.toml",
        profile.replace('"repo"', f'"{retired_identity}"') + RETIRED_SCHEMA,
        "accepted with a retired profile schema",
    )
    migrated = commit_fixture_file(
        case.repo, ".ethos/profile.toml", profile, "migrate the profile schema"
    )
    git(case.repo, "update-ref", "refs/heads/candidate", retired)
    git(case.repo, "update-ref", "refs/heads/topic", case.old)
    git(case.repo, "checkout", "-q", "--detach", case.old)
    value = {
        "expected": GitEffect(
            updates={"refs/heads/candidate": GitRefUpdate(expected=retired, desired=migrated)}
        ),
        "asserted": GitEffect(
            updates={"refs/heads/topic": GitRefUpdate(expected=case.old, desired=migrated)},
            assertions={"refs/heads/candidate": retired},
        ),
        "desired": GitEffect(
            updates={"refs/heads/topic": GitRefUpdate(expected=case.old, desired=retired)}
        ),
    }[retired_role]
    before = observe_git_effect(case.repo, value)
    if expected.startswith("repository:"):
        assert resolve_git_effect_repository(case.repo, value, before) == expected
        return
    with pytest.raises(ValueError, match=expected):
        resolve_git_effect_repository(case.repo, value, before)


@pytest.mark.parametrize(
    ("defect", "gap"),
    [
        ("", ""),
        ("edited", "repository_profile_invalid:.ethos/profile.toml"),
        ("candidate", "repository_profile_invalid"),
        ("identity", "git_effect_repository_identity_mismatch"),
        ("unreadable", "repository_profile_invalid:.ethos/profile.toml"),
    ],
)
def test_closeout_advances_an_accepted_checkout_from_a_retired_profile_schema(
    tmp_path: Path, defect: str, gap: str
) -> None:
    """The closed-out accepted checkout keeps its committed identity; the candidate stays strict."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    profile = (repo / ".ethos/profile.toml").read_text(encoding="utf-8")
    identity = git(repo, "show", "HEAD:.ethos/profile.toml").split('"')[1]
    accepted = commit_fixture_file(
        repo,
        ".ethos/profile.toml",
        {"identity": profile.replace(identity, "other"), "unreadable": "profile_id = ["}.get(
            defect, profile
        )
        + RETIRED_SCHEMA,
        "accepted with a retired profile schema",
    )
    candidate = add_candidate_worktree(repo, tmp_path / "repo-candidate-dev")
    (candidate / "README.md").write_text("# migrated\n", encoding="utf-8")
    if defect != "candidate":
        (candidate / ".ethos/profile.toml").write_text(profile, encoding="utf-8")
    head = commit_fixture(candidate, "test: migrate the profile schema")
    if defect != "candidate":
        seed_executed_proof(candidate, head)
    if defect == "edited":
        (repo / ".ethos/profile.toml").write_text(profile + "\n[edited]\n", encoding="utf-8")
    command = ("land", "--closeout", "--apply", "--authorize", "--expect-head", accepted)
    command += ("--candidate-head", head, "--json")
    if not defect:
        assert run_ethos(*command, cwd=repo)["state"] == "accepted_validated"
        assert git(repo, "rev-parse", "dev") == head
        return
    payload = run_ethos_blocked(*command, cwd=repo)
    assert payload["verdict"] == "block"
    assert gap in json.dumps(payload), payload["required_gaps"]
    assert git(repo, "rev-parse", "dev") == accepted


@pytest.mark.parametrize(
    ("declared", "required"),
    [
        ('mode = "disabled"', False),
        ('actions.control_replacement.mode = "disabled"', False),
        ('mode = "required"', True),
        ('mode = "sometimes"', True),
        ("actions = 1", True),
        ("mode = [", True),
    ],
)
def test_retired_accepted_profile_keeps_its_committed_verification_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, declared: str, *, required: bool
) -> None:
    """A retired predecessor keeps the verification it declared; unknown modes fail closed."""
    monkeypatch.setattr(evidence, "_SYSTEM_PROVIDER_CONFIGS", (tmp_path / "provider.toml",))
    _repo, candidate = start_adopted_candidate(tmp_path, docs_only=True)
    profile = (candidate / ".ethos/profile.toml").read_text(encoding="utf-8")
    declaration = f"\n[independent_verification]\n{declared}\n{RETIRED_SCHEMA}"
    accepted = commit_fixture_file(
        candidate, ".ethos/profile.toml", profile + declaration, "accepted under a retired schema"
    )
    head = commit_fixture_file(candidate, ".ethos/profile.toml", profile, "migrate the schema")
    seed_executed_proof(candidate, head)
    report = control_replacement_report(
        candidate_root=candidate, accepted_head=accepted, candidate_head=head
    )
    floor = report["subject"]["verification_floor"]
    assert floor["accepted_policy"] == {"gaps": ["repository_profile_invalid:.ethos/profile.toml"]}
    assert floor["accepted_policy_digest"] == canonical_json_digest(floor["accepted_policy"])
    gaps = ["independent_verification_provider_config_missing"] if required else []
    assert report["required_gaps"] == gaps
