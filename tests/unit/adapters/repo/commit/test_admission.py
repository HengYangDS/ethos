"""Exercise commit policy over exact messages, identities and introduced ranges."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import cast

import pytest

import ethos.adapters.repo.commit.admission as admission
import ethos.adapters.repo.commit.integration as integration
import ethos.adapters.repo.trust_anchor.verification as verification
from ethos.adapters.repo.git_object import observe_commit
from ethos.adapters.repo.git_object import zero_oid
from ethos.repository.policy.commit import CommitPolicy
from ethos.repository.policy.commit import commit_policy_from_text
from tests.support.ethos_cli_runner import run_ethos
from tests.support.governed_repository import commit_fixture_file
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import lane_start_arguments
from tests.unit.cli.land.publication.support import branch_publication_fixture


def _policy() -> CommitPolicy:
    return CommitPolicy(subject_pattern=r"^fix: .+", signing_format="ssh")


def _policy_text() -> str:
    return '[commit_policy]\nsubject_pattern = "^fix: .+"\n'


def _commit(repo: Path, subject: str, name: str, *, policy: str | None = None) -> str:
    if policy is not None:
        path = repo / ".ethos/workspace.toml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(policy, encoding="utf-8")
    (repo / f"{name}.txt").write_text(f"{name}\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-m", subject)
    return git(repo, "rev-parse", "HEAD")


def _report(
    repo: Path,
    *,
    proposed: str,
    remote: str,
    target: str = "refs/heads/dev",
    remote_name: str = "origin",
    trusted_baseline: str = "",
) -> dict[str, object]:
    return integration.commit_range_admission_report(
        repo,
        target_ref=target,
        proposed_head=proposed,
        remote_head=remote,
        remote_name=remote_name,
        trusted_baseline=trusted_baseline,
    )


@pytest.mark.parametrize(
    ("returncode", "records", "expected"),
    [
        (1, b"", "commit_policy_index_unreadable"),
        (0, b"", None),
        (0, b"100644 a 0\twrong\0", "commit_policy_index_invalid"),
        (0, b"100644 a 1\t.ethos/workspace.toml\0", "commit_policy_index_unmerged"),
        (0, b"120000 a 0\t.ethos/workspace.toml\0", "commit_policy_index_invalid"),
        (
            0,
            b"100644 a 1\t.ethos/workspace.toml"
            + bytes([0])
            + b"100644 b 2\t.ethos/workspace.toml"
            + bytes([0]),
            "commit_policy_index_unmerged",
        ),
        (0, b"100644 a 0\t.ethos/workspace.toml\0", "valid"),
    ],
)
def test_indexed_policy_projection_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    records: bytes,
    expected: str | None,
) -> None:
    monkeypatch.setattr(admission, "peel_commit", lambda *_args: "")
    message = tmp_path / "COMMIT_EDITMSG"
    message.write_text("fix: indexed policy\n", encoding="utf-8")
    monkeypatch.setattr(
        admission,
        "run_git",
        lambda _root, *args, **_kwargs: subprocess.CompletedProcess(
            args,
            0 if args[0] == "cat-file" else returncode,
            _policy_text().encode() if args[0] == "cat-file" else records,
            b"",
        ),
    )
    if isinstance(expected, str) and expected != "valid":
        with pytest.raises(ValueError, match=f"^{expected}$"):
            admission.commit_message_report(tmp_path, message)
    else:
        report = admission.commit_message_report(tmp_path, message)
        assert report["state"] == "subject_admitted"


@pytest.mark.parametrize(
    ("subject", "policy", "state", "gap"),
    [
        (None, None, "blocked", "commit_message_unreadable"),
        ("chore: paradigm grammar", None, "subject_admitted", ""),
        ("anything", None, "blocked", "commit_subject_invalid:anything"),
        ("fix: accepted", _policy(), "subject_admitted", ""),
        ("invalid", _policy(), "blocked", "commit_subject_invalid:invalid"),
    ],
)
def test_commit_message_report_matrix(
    tmp_path: Path,
    subject: str | None,
    policy: CommitPolicy | None,
    state: str,
    gap: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    if policy is not None:
        (repo / ".ethos").mkdir(exist_ok=True)
        (repo / ".ethos/workspace.toml").write_text(_policy_text(), encoding="utf-8")
        git(repo, "add", ".ethos/workspace.toml")
    message = repo / "COMMIT_EDITMSG"
    if subject is not None:
        message.write_text(subject + "\nbody\n", encoding="utf-8")
    report = admission.commit_message_report(repo, message)

    assert report["state"] == state
    assert report["required_gaps"] == ([gap] if gap else [])


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_fast_forward_range_is_oldest_first_and_excludes_old_history(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    object_format: str,
) -> None:
    repo = init_git_repo(tmp_path / object_format, object_format=object_format)
    baseline = git(repo, "rev-parse", "HEAD")
    first = _commit(repo, "fix: first", "first", policy=_policy_text())
    second = _commit(repo, "fix: second", "second")
    batches: list[tuple[str, ...]] = []

    def observe(root: Path, revisions: tuple[str, ...]) -> tuple[dict[str, object], ...]:
        batches.append(revisions)
        return tuple(observe_commit(root, revision) for revision in revisions)

    monkeypatch.setattr(integration, "observe_commits", observe, raising=False)

    report = _report(repo, proposed=second, remote=baseline)

    assert report["verdict"] == "pass"
    assert report["update_kind"] == "existing"
    assert report["baseline_commit"] == baseline
    assert report["revisions"] == [first, second]
    assert report["checked_commit_count"] == 2
    assert batches == [(first, second)]


def test_non_fast_forward_range_is_the_newly_reachable_set(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-b", "remote-line")
    remote = _commit(repo, "legacy remote subject", "remote")
    git(repo, "checkout", "dev")
    proposed = _commit(repo, "fix: replacement", "replacement", policy=_policy_text())

    report = _report(repo, proposed=proposed, remote=remote)

    assert git(repo, "rev-parse", "HEAD~1") == baseline
    assert report["verdict"] == "pass"
    assert report["revisions"] == [proposed]


@pytest.mark.parametrize(
    "case",
    ["proposal", "diverged", "explicit", "missing", "unreadable"],
)
def test_new_ref_baseline_matrix(tmp_path: Path, case: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    remote_name = "upstream" if case == "proposal" else "origin"
    target = (
        "refs/heads/proposal/feature" if case in {"proposal", "diverged"} else "refs/heads/topic"
    )
    trusted = baseline if case == "explicit" else "missing" if case == "unreadable" else ""
    if case == "diverged":
        git(repo, "checkout", "-b", "remote-line")
        remote = _commit(repo, "remote history", "remote")
        git(repo, "update-ref", "refs/remotes/origin/dev", remote)
        git(repo, "checkout", "dev")
    elif case == "proposal":
        git(repo, "update-ref", "refs/remotes/upstream/dev", baseline)
    proposed = _commit(repo, "fix: proposed", "proposed", policy=_policy_text())

    report = _report(
        repo,
        proposed=proposed,
        remote=zero_oid(repo),
        target=target,
        remote_name=remote_name,
        trusted_baseline=trusted,
    )

    if case in {"proposal", "explicit"}:
        assert report["verdict"] == "pass"
        assert report["baseline_commit"] == baseline
        assert report["revisions"] == [proposed]
        expected_source = (
            "declared_remote_accepted_ref" if case == "proposal" else "explicit_trusted_baseline"
        )
        assert report["baseline_source"] == expected_source
    else:
        assert report["verdict"] == "block"
        assert report["checked_commit_count"] == 0
        marker = {
            "diverged": "commit_range_trusted_baseline_not_ancestor:",
            "missing": "commit_range_trusted_baseline_required:",
            "unreadable": "commit_range_trusted_baseline_unreadable:missing",
        }[case]
        assert cast("list[str]", report["required_gaps"])[0].startswith(marker)


def test_diverged_proposal_selects_its_accepted_native_lane_birth(tmp_path: Path) -> None:
    """Real lane.start and candidate.accept effects select the range; a lane name alone cannot."""
    accepted_root, _, accepted = branch_publication_fixture(tmp_path, accepted=True)
    started = run_ethos(*lane_start_arguments(accepted_root), cwd=accepted_root, full_payload=True)[
        "data"
    ]
    lane = Path(started["path"])
    proposed = commit_fixture_file(lane, "FIX.md", "# fix\n", "fix: historical maintenance")
    git(lane, "checkout", "-q", "--detach", f"{accepted}~1")
    later = commit_fixture_file(lane, "LATER.md", "# later\n", "fix: later accepted line")
    git(lane, "checkout", "-q", "-")
    git(lane, "update-ref", "refs/remotes/origin/dev", later)

    reports = {
        root: _report(
            root, proposed=proposed, remote=zero_oid(lane), target="refs/heads/proposal/feature"
        )
        for root in (lane, accepted_root)
    }

    assert reports[lane]["verdict"] == "pass"
    assert reports[lane]["baseline_commit"] == accepted
    assert reports[lane]["baseline_source"] == "native_lane_birth_accepted_provenance"
    assert reports[lane]["revisions"] == [proposed]
    gap = cast("list[str]", reports[accepted_root]["required_gaps"])[0]
    assert gap.startswith("commit_range_trusted_baseline_not_ancestor:")


@pytest.mark.parametrize("tagged_endpoint", ["baseline", "proposed"])
def test_delete_and_annotated_tag_endpoints(
    tmp_path: Path,
    tagged_endpoint: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: tagged", "tagged", policy=_policy_text())
    commit = baseline if tagged_endpoint == "baseline" else proposed
    tag = f"{tagged_endpoint}-tag"
    git(repo, "tag", "-a", "-m", tag, tag, commit)
    tag_object = git(repo, "rev-parse", f"refs/tags/{tag}")

    report = _report(
        repo,
        proposed=tag_object if tagged_endpoint == "proposed" else proposed,
        remote=tag_object if tagged_endpoint == "baseline" else baseline,
    )
    deleted = _report(repo, proposed=zero_oid(repo), remote=proposed)

    assert report["verdict"] == "pass"
    assert (report["baseline_commit"], report["proposed_commit"]) == (baseline, proposed)
    assert deleted["state"] == "no_range"
    assert deleted["revisions"] == []


@pytest.mark.parametrize("case", ["absent", "malformed", "unreadable"])
def test_tip_policy_projection_matrix(tmp_path: Path, case: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    policy = (
        None if case == "absent" else "[commit_policy\n" if case == "malformed" else _policy_text()
    )
    proposed = _commit(
        repo, "unconstrained subject" if policy is None else "fix: policy", case, policy=policy
    )
    if case == "unreadable":
        oid = git(repo, "rev-parse", f"{proposed}:.ethos/workspace.toml")
        (repo / ".git/objects" / oid[:2] / oid[2:]).unlink()

    report = _report(repo, proposed=proposed, remote=baseline)

    if case == "absent":
        assert report["verdict"] == "block"
        assert cast("list[str]", report["required_gaps"])[0].startswith(
            f"commit_subject_invalid:{proposed}:"
        )
    else:
        assert report["verdict"] == "block"
        assert report["checked_commit_count"] == 0
        marker = (
            "commit_policy_toml_invalid:"
            if case == "malformed"
            else f"commit_policy_projection_unreadable:{proposed}"
        )
        assert cast("list[str]", report["required_gaps"])[0].startswith(marker)


def test_invalid_subject_identifies_the_exact_introduced_commit(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "invalid subject", "invalid", policy=_policy_text())

    report = _report(repo, proposed=proposed, remote=baseline)

    gap = f"commit_subject_invalid:{proposed}:invalid subject"
    assert report["violations"] == [
        {"commit": proposed, "subject": "invalid subject", "required_gaps": [gap]}
    ]
    assert report["required_gaps"] == [gap]


@pytest.mark.parametrize(
    ("policy", "signature", "trust", "expected", "state"),
    [
        (
            _policy(),
            "ssh",
            None,
            ["commit_subject_invalid:{revision}:invalid"],
            "present",
        ),
        (_policy(), "", None, ["commit_signature_missing:{revision}"], "missing"),
        (
            _policy(),
            "openpgp",
            None,
            ["commit_signature_format_mismatch:{revision}:expected=ssh:observed=openpgp"],
            "format_mismatch",
        ),
        (_policy(), "ssh", [], [], "present"),
        (
            _policy(),
            "ssh",
            ["git_signature_untrusted"],
            ["git_signature_untrusted"],
            "present",
        ),
    ],
)
def test_object_policy_and_optional_trust_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: CommitPolicy,
    signature: str,
    trust: list[str] | None,
    expected: list[str],
    state: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    revision = _commit(repo, "fix: signed", "signed")
    monkeypatch.setattr(
        admission,
        "observe_commit",
        lambda *_args: {
            "state": "current",
            "object_oid": revision,
            "author": {"name": "Author"},
            "committer": {"name": "Committer"},
            "subject": "invalid" if expected and "subject" in expected[0] else "fix: valid",
            "signature": {"present": bool(signature), "format": signature},
            "required_gaps": [],
        },
    )
    monkeypatch.setattr(
        integration,
        "observe_commits",
        lambda root, revisions: tuple(admission.observe_commit(root, item) for item in revisions),
    )
    verified: list[str] = []
    monkeypatch.setattr(
        verification,
        "verify_git_object_trust",
        lambda _root, value, _kind: verified.append(value) or {"required_gaps": trust or []},
    )
    monkeypatch.setattr(integration, "verify_commit_trust", admission.verify_commit_trust)

    report = admission.commit_policy_report(
        tmp_path,
        policy,
        revision,
        verify_trust=trust is not None,
    )

    formatted = [gap.format(revision=revision) for gap in expected]
    assert report["required_gaps"] == formatted
    assert report["verdict"] == ("block" if formatted else "pass")
    assert verified == ([revision] if trust is not None else [])
    if trust is not None:
        assert (
            integration.validate_replayed_commits(
                repo, baseline_commit=baseline, proposed_commit=revision, policy=policy
            )
            == formatted
        )
        # Both policy evaluations share one fresh native signature verification.
        assert verified == [revision] * 2
    assert report["head"] == {
        "object_oid": revision,
        "subject": "invalid" if expected and "subject" in expected[0] else "fix: valid",
        "author": {"name": "Author"},
        "committer": {"name": "Committer"},
    }
    assert cast("dict[str, object]", report["signature"])["state"] == state


@pytest.mark.parametrize(
    ("coordinate", "expected"),
    [
        ("proposed", "commit_range_proposed_unreadable:missing"),
        ("remote", "commit_range_remote_unreadable:missing"),
    ],
)
def test_unreadable_endpoint_fails_closed(
    tmp_path: Path,
    coordinate: str,
    expected: str,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    head = git(repo, "rev-parse", "HEAD")

    report = _report(
        repo,
        proposed="missing" if coordinate == "proposed" else head,
        remote="missing" if coordinate == "remote" else head,
    )

    assert report["required_gaps"] == [expected]


def test_unreadable_introduced_range_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    proposed = _commit(repo, "fix: range", "range", policy=_policy_text())
    run_git = integration.run_git
    monkeypatch.setattr(
        integration,
        "run_git",
        lambda root, *args, **kwargs: (
            subprocess.CompletedProcess(args, 1, "", "range unreadable")
            if args[0] == "rev-list"
            else run_git(root, *args, **kwargs)
        ),
    )

    report = _report(repo, proposed=proposed, remote=baseline)

    assert report["required_gaps"] == [f"commit_range_unreadable:{baseline}:{proposed}"]


@pytest.mark.parametrize(
    "case", ["valid", "invalid", "unreadable", "absent", "candidate_subject", "incumbent_subject"]
)
def test_replay_admission_owns_range_and_candidate_policy(tmp_path: Path, case: str) -> None:
    repo = init_git_repo(tmp_path / "repo")
    baseline = git(repo, "rev-parse", "HEAD")
    candidate = _policy()
    if case in {"candidate_subject", "incumbent_subject"}:
        narrower = _policy_text().replace("^fix: .+", "^fix: declared .+")
        baseline = _commit(
            repo,
            "fix: declared baseline",
            "baseline",
            policy=narrower if case == "incumbent_subject" else _policy_text(),
        )
        candidate = commit_policy_from_text(
            narrower if case == "candidate_subject" else _policy_text()
        )
    proposed = _commit(repo, "invalid" if case == "invalid" else "fix: replay", "replay")
    tip = "missing" if case == "unreadable" else proposed
    gaps = integration.validate_replayed_commits(
        repo,
        baseline_commit=baseline,
        proposed_commit=tip,
        policy=commit_policy_from_text("") if case == "absent" else candidate,
    )
    assert gaps == (
        [f"commit_subject_invalid:{proposed}:invalid"]
        if case == "invalid"
        else [f"commit_subject_invalid:{proposed}:fix: replay"]
        if case in {"candidate_subject", "incumbent_subject"}
        else [f"commit_range_unreadable:{baseline}:missing"]
        if case == "unreadable"
        else []
    )
