"""Legacy role refs and proposal refs that stand at commits made before the adoption.

A repository adopted under a legacy branch-role table can hold refs at commits that carry no
repository profile. Their retirement and their rename read the accepted head's declarations and
shared history, never an identity that such a commit cannot have.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import ethos.adapters.mutation.lane_retirement.abandonment as abandonment
from ethos.adapters.admission.ref_move_policy import prepared_deletion_gaps
from ethos.adapters.repo.hook.activation import install_hook_launchers
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import start_adopted_candidate
from tests.support.governed_repository import write_publication_topology
from tests.support.governed_repository import write_release_mirror
from tests.support.proof import seed_executed_proof
from tests.unit.cli.land.publication.support import accepted_release_fixture
from tests.unit.cli.land.publication.support import branch_publication_fixture

_TABLE = (
    "[branch_roles]\n"
    'release_branch = "master"\n'
    'accepted_branch = "dev"\n'
    'candidate_branch = "integration/dev"\n'
    'work_branch_prefix = "task/"\n'
    'proposal_branch_prefix = "submit/"\n'
)
_PLAIN = ("-c", "core.hooksPath=/dev/null")
_RETIRED_SCHEMA = '\n[retired]\nformat = "ruff-json"\n'
_REF = "submit/pre-adoption"
_ABANDON = (
    "lane",
    "retire",
    "abandon",
    "--branch",
    _REF,
    "--reason-code",
    "content-review",
    "--reason",
    "an equal patch is in the lane",
    "--review-content",
)
_ACTOR = "agent:test:case:agent-test"


def _run(root: Path, *words: str) -> dict[str, object]:
    done = run_ethos_raw(*words, "--json", cwd=root)
    return json.loads(done.stdout) | {"exit": done.returncode}


def _heads(repo: Path) -> dict[str, str]:
    rows = git(repo, "for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads")
    return dict(row.split() for row in rows.splitlines())


def _shape(tmp_path: Path, master_at: str = "before") -> tuple[Path, Path, str, dict[str, str]]:
    """The accepted head declares the legacy table and no release; legacy refs stand before it."""
    repo, candidate = start_adopted_candidate(tmp_path)
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    adopted = git(repo, "rev-parse", "HEAD")
    places = {"before": first, "profile": adopted}
    if master_at == "retired-schema":
        profile = repo / ".ethos/profile.toml"
        current = profile.read_text(encoding="utf-8")
        profile.write_text(current + _RETIRED_SCHEMA, encoding="utf-8")
        git(repo, "commit", "-am", "chore: accept a profile of a retired schema")
        places["retired-schema"] = git(repo, "rev-parse", "HEAD")
        profile.write_text(current, encoding="utf-8")
        git(repo, "commit", "-am", "chore: migrate the profile schema")
    if master_at == "deleted":
        git(repo, "rm", "-q", ".ethos/profile.toml")
        git(repo, "commit", "-m", "chore: drop the profile")
        places["deleted"] = git(repo, "rev-parse", "HEAD")
        git(repo, "revert", "--no-edit", "HEAD")
    (repo / ".ethos/workspace.toml").write_text(_TABLE, encoding="utf-8")
    git(repo, "add", ".ethos/workspace.toml")
    if (repo / ".ethos/release.toml").exists():
        git(repo, "rm", "-q", ".ethos/release.toml")
    git(repo, "commit", "-m", "chore: declare legacy branch roles and no release declaration")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    tree = git(repo, "rev-parse", f"{first}^{{tree}}")
    places["unrelated"] = git(repo, "commit-tree", tree, "-m", "chore: an unrelated root")
    git(repo, *_PLAIN, "update-ref", "refs/heads/master", places[master_at])
    old = git(repo, "commit-tree", tree, "-p", first, "-m", "fix: an old proposal")
    git(repo, *_PLAIN, "update-ref", f"refs/heads/{_REF}", old)
    git(repo, *_PLAIN, "worktree", "add", "-q", (tmp_path / "old-proposal").as_posix(), _REF)
    install_hook_launchers(repo)
    return repo, candidate, head, places


def _abandon(repo: Path) -> dict[str, object]:
    preview = _run(repo, *_ABANDON)
    step = preview.get("next") if isinstance(preview.get("next"), dict) else {}
    words = [str(word) for word in step.get("argv") or [] if word != "--json"][1:]
    return _run(repo, *words) if words else preview


def _closeout(repo: Path, head: str, *extra: str) -> dict[str, object]:
    return _run(repo, "land", "--closeout", *extra, "--expect-head", head)


def test_a_pre_adoption_proposal_ref_is_abandoned_whole(tmp_path: Path) -> None:
    repo, _candidate, _head, _places = _shape(tmp_path)

    retired = _abandon(repo)

    assert (retired["verdict"], retired["state"]) == ("pass", "retired")
    assert _REF not in _heads(repo)
    assert not (tmp_path / "old-proposal").exists()


def test_a_refused_deletion_blocks_the_abandonment_before_any_effect(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _candidate, _head, _places = _shape(tmp_path)
    monkeypatch.setattr(
        abandonment, "prepared_deletion_gaps", lambda *_args: ["ref_move_policy_unavailable"]
    )

    blocked = _run(repo, *_ABANDON)

    assert blocked["verdict"] == "block"
    assert "ref_move_policy_unavailable" in blocked["required_gaps"]
    step = blocked.get("next") if isinstance(blocked.get("next"), dict) else {}
    assert not step.get("argv")
    assert (tmp_path / "old-proposal").exists()
    assert _REF in _heads(repo)


def test_a_half_done_abandonment_is_finished_by_its_own_step(tmp_path: Path) -> None:
    """The reported state: the worktree is gone and the ref stays; the same step ends it."""
    repo, _candidate, _head, _places = _shape(tmp_path)
    preview = _run(repo, *_ABANDON)
    step = preview.get("next") if isinstance(preview.get("next"), dict) else {}
    words = [str(word) for word in step.get("argv") or [] if word != "--json"][1:]
    assert words
    lock = Path(git(repo, "rev-parse", "--git-common-dir")) / f"refs/heads/{_REF}.lock"
    lock = lock if lock.is_absolute() else repo / lock
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("", encoding="utf-8")

    stopped = _run(repo, *words)
    half_done = not (tmp_path / "old-proposal").exists() and _REF in _heads(repo)
    lock.unlink()
    finished = _run(repo, *words)

    assert stopped["verdict"] == "block"
    assert half_done
    assert (finished["verdict"], finished["state"]) == ("pass", "retired")
    assert _REF not in _heads(repo)
    assert not (tmp_path / "old-proposal").exists()


def test_a_legacy_release_ref_is_protected_before_its_rename(tmp_path: Path) -> None:
    repo, _candidate, _head, places = _shape(tmp_path)

    gaps = prepared_deletion_gaps(repo, "refs/heads/master", places["before"])

    assert gaps == ["legacy_role_ref_protected"]


# "retired-schema" waits for the owner's answer on the identity requirement's second
# sentence (rule b1): this case is the one that needs it, so it stays out until then.
@pytest.mark.parametrize("master_at", ["before", "profile"])
def test_closeout_renames_a_legacy_release_ref_that_predates_the_table(
    tmp_path: Path, master_at: str
) -> None:
    repo, _candidate, head, places = _shape(tmp_path, master_at)
    assert _abandon(repo)["state"] == "retired"

    preview = _closeout(repo, head)
    applied = _closeout(repo, head, "--apply", "--authorize")

    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_rename")
    assert (applied["verdict"], applied["state"]) == ("pass", "branch_roles_renamed")
    heads = _heads(repo)
    assert heads.get("main") == places[master_at]
    assert "master" not in heads
    assert _run(repo, "status")["state"] == "ready"


def test_closeout_renames_a_pre_adoption_release_ref_beside_a_legacy_accepted_name(
    tmp_path: Path,
) -> None:
    """The accepted root's own head is the source when the accepted ref has a legacy name too."""
    repo, candidate = start_adopted_candidate(tmp_path)
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    (repo / ".ethos/workspace.toml").write_text(
        "[branch_roles]\n"
        'release_branch = "master"\n'
        'accepted_branch = "accepted/train"\n'
        'candidate_branch = "candidate/train"\n',
        encoding="utf-8",
    )
    git(repo, "add", ".ethos/workspace.toml")
    git(repo, "commit", "-m", "chore: declare legacy branch roles")
    git(repo, "branch", "-m", "dev", "accepted/train")
    git(repo, "branch", "-m", "candidate/dev", "candidate/train")
    head = git(repo, "rev-parse", "HEAD")
    git(candidate, "reset", "--hard", head)
    git(repo, *_PLAIN, "update-ref", "refs/heads/master", first)
    install_hook_launchers(repo)

    preview = _closeout(repo, head)
    applied = _closeout(repo, head, "--apply", "--authorize")

    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_rename")
    assert (applied["verdict"], applied["state"]) == ("pass", "branch_roles_renamed")
    heads = _heads(repo)
    assert (heads.get("dev"), heads.get("candidate/dev"), heads.get("main")) == (head, head, first)
    assert not {"master", "accepted/train", "candidate/train"} & set(heads)


@pytest.mark.parametrize(
    ("master_at", "gap"),
    [
        ("unrelated", "legacy_role_rename_history_unshared:master"),
        ("deleted", "repository_historical_identity_invalid:.ethos/profile.toml"),
    ],
)
def test_closeout_refuses_a_legacy_ref_outside_the_accepted_line(
    tmp_path: Path, master_at: str, gap: str
) -> None:
    """No shared history, or a profile that the line carried and then dropped, is not adopted."""
    repo, _candidate, head, places = _shape(tmp_path, master_at)
    assert _abandon(repo)["state"] == "retired"

    preview = _closeout(repo, head)
    applied = _closeout(repo, head, "--apply", "--authorize")

    assert preview["verdict"] == applied["verdict"] == "block"
    assert gap in preview["required_gaps"]
    assert gap in applied["required_gaps"]
    assert _heads(repo).get("master") == places[master_at]
    assert "main" not in _heads(repo)


def test_the_release_mirror_advances_from_a_pre_adoption_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    repo, candidate, head, places = _shape(tmp_path)
    assert _abandon(repo)["state"] == "retired"
    assert _closeout(repo, head, "--apply", "--authorize")["state"] == "branch_roles_renamed"
    git(candidate, "rm", "-q", ".ethos/workspace.toml")
    write_release_mirror(candidate, "accepted_ff")
    write_publication_topology(candidate)
    git(candidate, "add", "-A")
    git(candidate, "commit", "-q", "-m", "chore: declare the release and drop the legacy table")
    landed = git(candidate, "rev-parse", "HEAD")
    seed_executed_proof(candidate, landed)
    accepted = _closeout(repo, head, "--apply", "--authorize", "--candidate-head", landed)
    assert accepted["verdict"] == "pass"
    assert _heads(repo)["main"] == places["before"]

    mirrored = _closeout(repo, landed, "--apply", "--authorize")

    assert (mirrored["verdict"], mirrored["state"]) == ("pass", "accepted_current")
    assert _heads(repo)["main"] == landed


def test_a_release_advances_the_release_ref_from_a_pre_adoption_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    accepted, main, _old, head = accepted_release_fixture(tmp_path)
    base = git(accepted, "rev-list", "--max-parents=0", head)
    assert not git(accepted, "ls-tree", "-r", "--name-only", base, ".ethos")
    git(main, *_PLAIN, "reset", "-q", "--hard", base)
    release = (
        "land",
        "--release",
        "--expect-head",
        head,
        "--release-head",
        base,
        "--tag",
        "v1.2.3",
    )

    preview = _run(accepted, *release)
    applied = _run(accepted, *release, "--apply", "--authorize")

    assert (preview["verdict"], preview["state"]) == ("pass", "ready_to_release")
    assert (applied["verdict"], applied["state"]) == ("pass", "released")
    assert git(accepted, "rev-parse", "main") == head


@pytest.mark.parametrize("ref", ["refs/heads/master", f"refs/heads/{_REF}"])
def test_publication_retirement_still_refuses_a_peer_s_legacy_ref(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ref: str
) -> None:
    """Unchanged by the repairs: a peer's legacy ref is no proposal, so a person deletes it."""
    monkeypatch.setenv("ETHOS_ACTOR", _ACTOR)
    repo, peers, _proposal = branch_publication_fixture(tmp_path, source_branch="dev", proof=False)
    policy = repo / ".ethos/release.toml"
    plain = policy.read_text(encoding="utf-8")
    for provider in ("gitlab", "github"):
        plain = plain.replace(f'provider = "{provider}"', 'provider = "git"')
    policy.write_text(plain, encoding="utf-8")
    git(repo, "add", ".ethos/release.toml")
    git(repo, "commit", "-m", "chore: declare plain Git peers")
    head = git(repo, "rev-parse", "HEAD")
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    for remote in peers:
        git(repo, *_PLAIN, "push", "-q", remote, f"{head}:refs/heads/dev", f"{first}:{ref}")

    refused = _run(
        repo, "publish", "--retire", "--ref", ref, "--probe-remote", "--expect-head", head
    )

    assert refused["verdict"] == "block"
    assert {f"proposal_retirement_target_not_proposal:{remote}:{ref}" for remote in peers} <= set(
        refused["required_gaps"]
    )
    for peer in peers.values():
        assert git(peer, "rev-parse", ref) == first
