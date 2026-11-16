"""One hosted observation covers every CI peer: the command gates on it, the landing states it."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING

import pytest

import ethos.application.publication.hosted as hosted
from ethos.application.publication.hosted import hosted_observation
from ethos.contracts.codes.gaps import repair_for
from tests.support.ethos_cli_runner import full_result
from tests.support.ethos_cli_runner import run_ethos
from tests.support.ethos_cli_runner import run_ethos_blocked
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.unit.cli.land.publication.support import branch_publication
from tests.unit.cli.land.publication.support import branch_publication_fixture
from tests.unit.cli.land.publication.test_hosted_runs import URLS
from tests.unit.cli.land.publication.test_hosted_runs import job_row
from tests.unit.cli.land.publication.test_hosted_runs import recorded_forge
from tests.unit.cli.land.publication.test_hosted_runs import run_row

if TYPE_CHECKING:
    from pathlib import Path


def _repository(tmp_path: Path, *, ci_peers: bool = True) -> tuple[Path, str]:
    """Adopt one repository whose two declared CI peers, if any, name their web repositories."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo, docs_only=not ci_peers)
    for peer, url in URLS.items():
        git(repo, "remote", "add", peer, f"{url}.git")
    return repo, git(repo, "rev-parse", "HEAD")


def _forge(monkeypatch: pytest.MonkeyPatch, head: str, **runs: str) -> list[tuple[str, ...]]:
    """Record each peer's answer: one run of the head in a state, no run, or a refusal."""
    denied = subprocess.CompletedProcess((), 1, "", "authentication required")
    answers = {
        peer: denied
        if run == "denied"
        else ([run_row(peer, run, head=head)] if run != "none" else [], [job_row(peer, "passed")])
        for peer, run in runs.items()
    }
    return recorded_forge(monkeypatch, answers)


@pytest.mark.parametrize(
    ("gitlab", "github", "verdict", "state", "gaps"),
    [
        ("passed", "passed", "pass", "passed", []),
        ("none", "passed", "block", "no_run", ["hosted_run_missing:gitlab"]),
        ("passed", "failed", "block", "failed", ["hosted_run_failed:github"]),
        ("running", "passed", "unknown", "running", ["hosted_run_running:gitlab"]),
        ("denied", "passed", "unknown", "unknown", ["hosted_run_unknown:gitlab"]),
        (
            "denied",
            "none",
            "block",
            "no_run",
            ["hosted_run_missing:github", "hosted_run_unknown:gitlab"],
        ),
    ],
)
def test_the_observation_names_each_peer_that_did_not_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gitlab: str,
    github: str,
    verdict: str,
    state: str,
    gaps: list[str],
) -> None:
    """Two peers that disagree stay two facts; no credentials is `unknown`, never a pass.

    The gaps come in the order that decides the verdict, so the first is the one that decided.
    """
    repo, head = _repository(tmp_path)
    _forge(monkeypatch, head, gitlab=gitlab, github=github)
    argv = ("publish", "--observe-hosted", "--expect-head", head, "--json")
    completed = run_ethos_raw(*argv, cwd=repo)
    result = full_result(completed)
    assert (result["verdict"], result["state"], result["required_gaps"]) == (verdict, state, gaps)
    assert completed.returncode == (0 if verdict == "pass" else 1)
    observation = result["data"]["hosted_observation"]
    assert (observation["head"], observation["observation_gaps"]) == (head, gaps)
    wanted = {"none": "no_run", "denied": "unknown"}
    assert {peer: item["state"] for peer, item in observation["peers"].items()} == {
        "gitlab": wanted.get(gitlab, gitlab),
        "github": wanted.get(github, github),
    }
    assert result["summary"]["ci_peers"] == 2
    # Only an observation that may still conclude asks for itself again; any other names the
    # registered repair of its first gap, which is the gap that decided.
    assert (result["next"]["form"] == "publish.hosted.observe") == (state == "running")
    assert state == "running" or result["next_action"] == (repair_for(gaps[0]) if gaps else "")


def test_the_observation_reads_only_the_head_it_was_asked_for(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Another expected head runs no provider command, and the operation takes no other mode."""
    repo, head = _repository(tmp_path)
    commands = _forge(monkeypatch, head, gitlab="passed", github="passed")
    blocked = run_ethos_blocked(
        "publish", "--observe-hosted", "--expect-head", "b" * 40, "--json", cwd=repo
    )
    assert (blocked["required_gaps"], commands) == (["expect_head_mismatch"], [])
    refused = run_ethos_raw("publish", "--observe-hosted", "--probe-remote", "--json", cwd=repo)
    assert (refused.returncode, full_result(refused)["required_gaps"]) == (
        2,
        ["command_field_refused:probe_remote"],
    )


def test_a_repository_without_a_readable_ci_peer_runs_no_provider_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No declared CI peer is no hosted plane; an unreadable declaration is named, not skipped."""
    repo, head = _repository(tmp_path, ci_peers=False)
    commands = recorded_forge(monkeypatch, {})
    result = run_ethos("publish", "--observe-hosted", "--json", cwd=repo)
    assert (result["verdict"], result["state"]) == ("pass", "no_ci_peer")
    # The pass is of no peer, and the summary says how many were observed.
    assert result["summary"]["ci_peers"] == 0
    (repo / ".ethos/release.toml").write_text("not valid TOML [", encoding="utf-8")
    unreadable = hosted_observation(repo, head)
    gap = "release_config_invalid:.ethos/release.toml"
    assert (unreadable["state"], unreadable["observation_gaps"]) == ("topology_invalid", [gap])
    # The observation itself names the step, so the landing preview and the probe carry it too.
    assert unreadable["next_action"] == "repair the publication declaration, then observe again"
    assert commands == []


_RETIRED = '[publication]\nlocal_verification_command = "true"\n\n[[publication.peers]]'


@pytest.mark.parametrize(
    ("declaration", "step"),
    [
        (("[[publication.peers]]", _RETIRED), "ethos lane repair-paradigm --apply --json"),
        (('"repository", "ci_cd", "publication"', '"ci_cd"'), ""),
        ((None, "not valid TOML ["), ""),
    ],
    ids=["retired-field", "peer-capabilities", "unparsable"],
)
def test_a_declaration_that_cannot_be_observed_blocks_with_a_next_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    declaration: tuple[str | None, str],
    step: str,
) -> None:
    """The topology's own repair comes first, then a registered one, then a general step."""
    repo, _head = _repository(tmp_path)
    recorded_forge(monkeypatch, {})
    binding = repo / ".ethos/release.toml"
    old, new = declaration
    text = binding.read_text(encoding="utf-8")
    binding.write_text(new if old is None else text.replace(old, new, 1), encoding="utf-8")
    result = full_result(run_ethos_raw("publish", "--observe-hosted", "--json", cwd=repo))
    assert (result["verdict"], result["state"]) == ("block", "topology_invalid")
    assert result["next_action"] == (
        step or "repair the publication declaration, then observe again"
    )
    # A repair that the registry gains for such a gap replaces the general step alone.
    monkeypatch.setattr(hosted, "repair_for", lambda _gap: "a registered repair")
    again = full_result(run_ethos_raw("publish", "--observe-hosted", "--json", cwd=repo))
    assert again["next_action"] == (step or "a registered repair")


def test_a_peer_state_that_no_gap_names_is_never_dropped(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A state outside the table is unknown for its peer; left out it would read as passed."""
    repo, head = _repository(tmp_path)
    monkeypatch.setattr(hosted, "observe_hosted_runs", lambda *_peer: {"state": "paused"})
    observation = hosted_observation(repo, head)
    unknown = ["hosted_run_unknown:github", "hosted_run_unknown:gitlab"]
    assert (observation["state"], sorted(observation["observation_gaps"])) == ("unknown", unknown)
    result = full_result(run_ethos_raw("publish", "--observe-hosted", "--json", cwd=repo))
    assert (result["verdict"], sorted(result["required_gaps"])) == ("unknown", unknown)
    # Every gap of a peer names a registered repair, so no such result is without a step.
    assert all(repair_for(code) for code in hosted.HOSTED_GAPS.values())


def test_the_landing_preview_states_the_observation_and_refuses_nothing_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The preview carries each CI peer's state as data; its verdict and gaps do not change.

    A head whose runs passed costs one call for each peer and an entry that stays inline; an
    apply reads no forge.
    """
    repo, head = _repository(tmp_path)
    clean = _forge(monkeypatch, head, gitlab="passed", github="passed")
    before = run_ethos("land", "--json", cwd=repo)
    assert before["data"]["hosted_observation"]["state"] == "passed"
    assert len(clean) == 2
    assert len(json.dumps(before["data"]["hosted_observation"], indent=2)) < 1024
    commands = _forge(monkeypatch, head, gitlab="none", github="failed")
    preview = run_ethos("land", "--json", cwd=repo)
    observation = preview["data"]["hosted_observation"]
    assert (observation["state"], observation["head"]) == ("failed", head)
    assert observation["observation_gaps"] == [
        "hosted_run_failed:github",
        "hosted_run_missing:gitlab",
    ]
    assert {peer: item["state"] for peer, item in observation["peers"].items()} == {
        "gitlab": "no_run",
        "github": "failed",
    }
    assert (preview["verdict"], preview["required_gaps"]) == (
        before["verdict"],
        before["required_gaps"],
    )
    apply = ("land", "--apply", "--authorize", "--expect-head", head, "--json")
    assert "hosted_observation" not in full_result(run_ethos_raw(*apply, cwd=repo))["data"]
    assert len(commands) == 3


def test_a_release_ref_probe_states_the_observation_and_refuses_nothing_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The probe of a release ref reports its proof head's runs; any other ref reads no forge."""
    repo, _peers, head = branch_publication_fixture(tmp_path, accepted=True)
    for peer, url in URLS.items():
        git(repo, "config", "--local", f"remote.{peer}.forgeRepository", url)
    _forge(monkeypatch, head, gitlab="passed", github="passed")
    passed = branch_publication(repo, head, target_ref="refs/heads/main")
    assert passed["data"]["hosted_observation"]["state"] == "passed"
    commands = _forge(monkeypatch, head, gitlab="none", github="failed")
    probe = branch_publication(repo, head, target_ref="refs/heads/main")
    observation = probe["data"]["hosted_observation"]
    assert (observation["head"], observation["observation_gaps"]) == (
        head,
        ["hosted_run_failed:github", "hosted_run_missing:gitlab"],
    )
    assert (probe["verdict"], probe["required_gaps"]) == (passed["verdict"], [])
    accepted = branch_publication(repo, head, target_ref="refs/heads/dev")
    assert "hosted_observation" not in accepted["data"]
    assert len(commands) == 3
