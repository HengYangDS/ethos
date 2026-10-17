"""Native commit integrity rejects misleading identity and signature projections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest
from ruff import find_ruff_bin

import ethos.adapters.repo.git_object as git_object
import ethos.adapters.repo.trust_anchor.verification as verification
from ethos.adapters.repo.commit.admission import commit_message_report
from ethos.adapters.repo.commit.creation import create_git_commit
from ethos.adapters.repo.commit.integration import commit_range_admission_report
from ethos.adapters.repo.commit.integration import validate_replayed_commits
from ethos.adapters.repo.git import run_git
from ethos.repository.policy.commit import commit_policy_from_text
from tests.support.architecture import architecture_projection_fixture
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import prepared_work_lane
from tests.support.governed_repository import write_publication_topology
from tests.support.runtime_scenarios import git_process
from tests.support.runtime_scenarios import install_fixture_hook_runtime
from tests.support.signature import configure_signer

_POLICY = '[commit_policy]\nsubject_pattern = "^fix: .+"\n'
_IDENTITY = (
    '[commit_policy.author]\nname = "ETHOS Test"\nemail = "test@example.invalid"\n'
    '[commit_policy.committer]\nname = "ETHOS Test"\nemail = "test@example.invalid"\n'
)


def _repository(tmp_path: Path) -> tuple[Path, str, str]:
    repo = init_git_repo(tmp_path / "repo")
    configure_signer(repo, tmp_path)
    (repo / ".ethos").mkdir()
    (repo / ".ethos/workspace.toml").write_text(_POLICY)
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    baseline = git(repo, "commit-tree", tree, "-m", "fix: baseline")
    return repo, baseline, tree


@pytest.mark.parametrize("invalid_middle", [False, True])
@pytest.mark.parametrize("distinct_policy", [False, True])
@pytest.mark.parametrize("consumer", ["range", "replay"])
def test_range_consumes_one_native_trust_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    consumer: str,
    *,
    invalid_middle: bool,
    distinct_policy: bool,
) -> None:
    """Every introduced object retains admission while sharing one current trust input."""
    repo, baseline, tree = _repository(tmp_path)
    candidate_text = _POLICY
    if distinct_policy:
        candidate_text = _POLICY.replace("^fix: .+", "^fix: item .+")
        (repo / ".ethos/workspace.toml").write_text(candidate_text)
        git(repo, "add", ".ethos/workspace.toml")
        tree = git(repo, "write-tree")
    revisions = []
    parent = baseline
    for index in range(3):
        parent = git(repo, "commit-tree", "-S", tree, "-p", parent, "-m", f"fix: item {index}")
        if invalid_middle and index == 1:
            raw = run_git(repo, "cat-file", "commit", parent, text=False).stdout
            parent = (
                run_git(
                    repo,
                    "hash-object",
                    "-w",
                    "-t",
                    "commit",
                    "--stdin",
                    stdin=raw.replace(b"fix: item 1", b"fix: item changed"),
                    text=False,
                )
                .stdout.decode()
                .strip()
            )
        revisions.append(parent)
    native = verification.run_git
    native_object = git_object.run_git
    selections = []
    observations = []

    def observed(root, *args, **kwargs):
        if "verify-commit" in args:
            selections.append(args[args.index("--raw") + 1 :])
        return native(root, *args, **kwargs)

    def observed_object(root, *args, **kwargs):
        if args[0] == "show":
            observations.append(tuple(str(kwargs["stdin"]).splitlines()))
        return native_object(root, *args, **kwargs)

    monkeypatch.setattr(verification, "run_git", observed)
    monkeypatch.setattr(git_object, "run_git", observed_object)
    if consumer == "replay":
        gaps = validate_replayed_commits(
            repo,
            baseline_commit=baseline,
            proposed_commit=parent,
            policy=commit_policy_from_text(candidate_text),
        )
    else:
        report = commit_range_admission_report(
            repo,
            target_ref="refs/heads/dev",
            proposed_head=parent,
            remote_head=baseline,
            remote_name="origin",
        )
        gaps = report["required_gaps"]
        assert report["revisions"] == revisions
        assert report["verdict"] == ("block" if invalid_middle else "pass"), report
        violations = cast("list[dict[str, object]]", report["violations"])
        assert [item["commit"] for item in violations] == ([revisions[1]] if invalid_middle else [])

    assert observations == [tuple(revisions)]
    assert selections[0] == tuple(revisions)
    assert selections[1:] == ([(value,) for value in revisions] if invalid_middle else [])
    assert gaps == (["commit_signature_untrusted"] if invalid_middle else [])
    if not invalid_middle:
        (tmp_path / "trust/allowed-signers").unlink()
        assert validate_replayed_commits(
            repo,
            baseline_commit=baseline,
            proposed_commit=parent,
            policy=commit_policy_from_text(candidate_text),
        ) == ["commit_trust_anchor_missing"]
        assert observations == [tuple(revisions)] * 2


@pytest.mark.parametrize("select_policy", [False, True])
def test_signed_pathspec_commit_reads_only_the_selected_policy(
    tmp_path: Path, *, select_policy: bool
) -> None:
    """An unselected staged policy cannot veto or authorize the signed commit."""
    root = prepared_work_lane(tmp_path).worktree
    policy = root / ".ethos/workspace.toml"
    policy.write_text(_POLICY)
    commit_fixture(root, "fix: declare commit policy")
    configure_signer(root, tmp_path)
    note = root / "notes/selected.md"
    note.parent.mkdir()
    note.write_text("Selected authored note.\n")
    policy.write_text(policy.read_text().replace("^fix: .+", "^docs: .+"))
    git(root, "add", ".ethos/workspace.toml", "notes/selected.md")
    head, index = git(root, "rev-parse", "HEAD"), git(root, "write-tree")
    selected = ".ethos/workspace.toml" if select_policy else "notes/selected.md"
    result = git_process(root, "commit", "-S", "-m", "fix: selected policy", "--", selected)
    assert result.returncode == int(select_policy), result.stderr
    assert git(root, "write-tree") == index
    assert "^docs: .+" in git(root, "show", ":.ethos/workspace.toml")
    assert "^fix: .+" in git(root, "show", "HEAD:.ethos/workspace.toml")
    if select_policy:
        assert "commit_subject_invalid" in result.stderr
        assert git(root, "rev-parse", "HEAD") == head
    else:
        assert git(root, "rev-parse", "HEAD") != head
        assert git_process(root, "verify-commit", "HEAD").returncode == 0


@pytest.mark.parametrize(
    "case", ["valid", "anchorless", "unsigned", "forged", "weakened", "removed"]
)
def test_range_requires_real_signature_under_trusted_prestate(tmp_path: Path, case: str) -> None:
    repo, baseline, tree = _repository(tmp_path)
    if case in {"weakened", "removed"}:
        (repo / ".ethos/workspace.toml").write_text(
            "" if case == "removed" else _POLICY.replace("true", "false")
        )
        git(repo, "add", ".ethos/workspace.toml")
        tree = git(repo, "write-tree")
    revision = git(
        repo,
        "commit-tree",
        *(("-S",) if case in {"valid", "anchorless"} else ()),
        tree,
        "-p",
        baseline,
        "-m",
        "fix: candidate",
    )
    if case == "forged":
        raw = run_git(repo, "cat-file", "commit", revision, text=False).stdout
        header, separator, message = raw.partition(b"\n\n")
        forged = (
            header + b"\ngpgsig -----BEGIN SSH SIGNATURE-----\n invalid-base64"
            b"\n -----END SSH SIGNATURE-----" + separator + message
        )
        revision = (
            run_git(repo, "hash-object", "-w", "-t", "commit", "--stdin", stdin=forged, text=False)
            .stdout.decode()
            .strip()
        )
    if case == "anchorless":
        git(repo, "config", "gpg.ssh.allowedSignersFile", str(tmp_path / "missing"))
    report = commit_range_admission_report(
        repo,
        target_ref="refs/heads/proposal/test",
        proposed_head=revision,
        remote_head=baseline,
        remote_name="origin",
    )
    assert report["verdict"] == ("pass" if case == "valid" else "block"), report
    assert report["revisions"] == [revision]
    if case == "anchorless":
        assert report["required_gaps"] == ["commit_trust_anchor_missing"]
    if case in {"valid", "anchorless", "unsigned", "forged"}:
        args = (
            f"hook commit-range --target-ref refs/heads/topic --proposed-head {revision} "
            f"--remote-head {'0' * 40} --remote origin --trusted-baseline {baseline} --json"
        )
        result = run_ethos_raw(*args.split(), cwd=repo)
        payload = json.loads(result.stdout)
        assert result.returncode == (0 if case == "valid" else 1), payload
        assert payload["data"]["target_ref"] == "refs/heads/topic"
        assert payload["data"]["proposed_head"] == revision
        assert payload["data"]["remote_head"] == "0" * 40
        assert payload["data"]["remote_name"] == "origin"
        assert payload["data"]["baseline_commit"] == baseline
        assert payload["data"]["revisions"] == [revision]
        assert payload["data"]["signature_verification"] == "required_native"
        assert payload["required_gaps"] == report["required_gaps"]


@pytest.mark.parametrize("role", ["author", "committer"])
def test_tracked_identity_rejects_prospective_override(tmp_path, monkeypatch, role):
    repo, _baseline, _tree = _repository(tmp_path)
    (repo / ".ethos/workspace.toml").write_text(_POLICY + _IDENTITY)
    git(repo, "add", ".ethos/workspace.toml")
    message = repo / "message"
    message.write_text("fix: prospective\n")
    monkeypatch.setenv(f"GIT_{role.upper()}_NAME", "Wrong Account")
    report = commit_message_report(repo, message)
    assert report["verdict"] == "block"
    assert any(
        f"commit_{role}_identity_mismatch" in gap
        for gap in cast("list[str]", report["required_gaps"])
    )


@pytest.mark.parametrize("role", ["author", "committer"])
@pytest.mark.parametrize("policy_owner", ["candidate", "incumbent"])
def test_tracked_identity_rejects_signed_object(tmp_path, monkeypatch, role, policy_owner):
    repo, baseline, _tree = _repository(tmp_path)
    (repo / ".ethos/workspace.toml").write_text(_POLICY + _IDENTITY)
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    if policy_owner == "incumbent":
        baseline = git(repo, "commit-tree", tree, "-p", baseline, "-m", "fix: identity policy")
        (repo / ".ethos/workspace.toml").write_text(_POLICY)
        git(repo, "add", ".ethos/workspace.toml")
        tree = git(repo, "write-tree")
    monkeypatch.setenv(f"GIT_{role.upper()}_EMAIL", "wrong@example.invalid")
    revision = git(repo, "commit-tree", "-S", tree, "-p", baseline, "-m", "fix: signed")
    report = commit_range_admission_report(
        repo,
        target_ref="refs/heads/proposal/test",
        proposed_head=revision,
        remote_head=baseline,
        remote_name="origin",
    )
    assert report["verdict"] == "block"
    assert any(
        f"commit_{role}_identity_mismatch" in gap
        for gap in cast("list[str]", report["required_gaps"])
    )


def test_identity_constraints_have_one_strict_compiler():
    policy = commit_policy_from_text(_POLICY + _IDENTITY)
    assert policy is not None
    assert policy.projection()["author"] == {"name": "ETHOS Test", "email": "test@example.invalid"}
    with pytest.raises(ValueError, match="commit_policy_invalid:author"):
        commit_policy_from_text(_POLICY + '[commit_policy.author]\nname="Partial"\n')


@pytest.mark.parametrize("case", ["identity", "subject", "policy_removed"])
def test_prospective_candidate_cannot_waive_incumbent_constraints(tmp_path, monkeypatch, case):
    repo, _baseline, _tree = _repository(tmp_path)
    original = _POLICY + _IDENTITY
    (repo / ".ethos/workspace.toml").write_text(original)
    git(repo, "add", ".ethos/workspace.toml")
    git(repo, "commit", "-m", "fix: declared")
    weakened = "" if case == "policy_removed" else _POLICY
    if case == "subject":
        weakened = weakened.replace('"^fix: .+"', '".*"')
    (repo / ".ethos/workspace.toml").write_text(weakened)
    git(repo, "add", ".ethos/workspace.toml")
    if case != "subject":
        monkeypatch.setenv("GIT_AUTHOR_NAME", "Wrong Account")
    message = repo / "message"
    message.write_text("invalid" if case == "subject" else "fix: cannot self-authorize")
    assert commit_message_report(repo, message)["verdict"] == "block"


@pytest.mark.parametrize("case", ["parent", "target", "identity", "subject", "malformed"])
def test_generated_commit_uses_exact_parent_and_target_not_checkout(tmp_path, case):
    repo, baseline, tree = _repository(tmp_path)
    workspace = repo / ".ethos/workspace.toml"
    if case == "identity":
        workspace.write_text(_POLICY + _IDENTITY)
        git(repo, "add", ".ethos/workspace.toml")
        tree = git(repo, "write-tree")
        baseline = git(repo, "commit-tree", tree, "-m", "fix: constrained parent")
    if case in {"parent", "identity"}:
        workspace.write_text("")
    elif case == "malformed":
        workspace.write_text("[commit_policy]\nsubject_pattern = 42\n")
    git(repo, "add", ".ethos/workspace.toml")
    tree = git(repo, "write-tree")
    # The editable checkout is not the tree passed to commit-tree.
    workspace.write_text("")
    if case == "target":
        baseline = git(repo, "rev-parse", "HEAD")

    def create():
        return create_git_commit(
            repo,
            tree=tree,
            parent=baseline,
            message="invalid subject" if case == "subject" else "fix: generated",
            environment={"GIT_AUTHOR_NAME": "Wrong"} if case == "identity" else None,
        )

    if case in {"identity", "subject", "malformed"}:
        with pytest.raises(
            ValueError, match=r"commit_(author_identity_mismatch|subject_invalid|policy_invalid)"
        ):
            create()
    else:
        result = create()
        assert result.returncode == 0, result.stderr
        assert run_git(repo, "verify-commit", result.stdout.strip(), check=False).returncode == 0


@pytest.mark.parametrize("case", ["identity", "unsigned", "valid"])
def test_native_hooks_reject_commit_or_push_without_parallel_policy(tmp_path, monkeypatch, case):
    repo, _baseline, _tree = _repository(tmp_path)
    write_publication_topology(repo)
    (repo / ".ethos/workspace.toml").write_text(_POLICY + _IDENTITY)
    git(repo, "add", ".")
    git(repo, "commit", "-S", "-m", "fix: baseline")
    git(repo, "branch", "topic")
    git(repo, "checkout", "topic")
    baseline = git(repo, "rev-parse", "HEAD")
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare")
    git(repo, "remote", "add", "gitlab", str(remote))
    git(repo, "push", "gitlab", "refs/heads/topic:refs/heads/proposal/test")
    install_fixture_hook_runtime(repo)
    if case == "identity":
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "wrong@example.invalid")
        rejected = git_process(repo, "commit", "--allow-empty", "-S", "-m", "fix: wrong")
        assert rejected.returncode != 0, rejected
        assert "commit_author_identity_mismatch" in rejected.stderr
        assert git(repo, "rev-parse", "HEAD") == baseline
    committed = git_process(
        repo,
        "commit",
        "--no-verify",
        "--allow-empty",
        "--no-gpg-sign" if case == "unsigned" else "-S",
        "-m",
        "fix: exact range",
    )
    assert committed.returncode == 0, committed.stderr
    pushed = git_process(repo, "push", "gitlab", "refs/heads/topic:refs/heads/proposal/test")
    if case == "valid":
        assert pushed.returncode == 0, pushed.stderr
        assert git(remote, "rev-parse", "refs/heads/proposal/test") == git(
            repo, "rev-parse", "HEAD"
        )
    else:
        assert pushed.returncode != 0, pushed
        expected = (
            "commit_signature_missing" if case == "unsigned" else "commit_author_identity_mismatch"
        )
        assert expected in pushed.stderr
        assert git(remote, "rev-parse", "refs/heads/proposal/test") == baseline


def test_replayed_commits_cannot_waive_trusted_baseline_signatures(tmp_path):
    repo, baseline, tree = _repository(tmp_path)
    revision = git(repo, "commit-tree", tree, "-p", baseline, "-m", "fix: unsigned replay")
    assert validate_replayed_commits(
        repo,
        baseline_commit=baseline,
        proposed_commit=revision,
        policy=commit_policy_from_text(""),
    ) == [f"commit_signature_missing:{revision}"]


@pytest.mark.parametrize("selected_valid", [True, False])
@pytest.mark.parametrize("checked_owner", ["projection", "formatter", "secrets"])
def test_signed_pathspec_commit_admits_only_its_selected_index(
    tmp_path: Path, *, selected_valid: bool, checked_owner: str
) -> None:
    """Selected index bytes govern every check without consuming unrelated staged work."""
    root = prepared_work_lane(tmp_path).worktree
    if checked_owner == "projection":
        _declaration, _model, output = architecture_projection_fixture(root, "Before")
        invalid, gap = "wrong staged output\n", "generated_projection_drift:docs/diagram.mmd"
    else:
        output = root / ("unselected.py" if checked_owner == "formatter" else "unselected.txt")
        output.write_text("VALUE = 1\n")
        if checked_owner == "formatter":
            formatter = root / ".config/checks/ruff/ruff.toml"
            formatter.parent.mkdir(parents=True, exist_ok=True)
            formatter.write_text("line-length = 100\n")
            install_fixture_hook_runtime(root, native_executables={"ruff": Path(find_ruff_bin())})
            invalid, gap = "VALUE=1\n", "pre_commit_python_format_failed"
        else:
            secrets = root / ".config/checks/gitleaks/gitleaks.toml"
            secrets.parent.mkdir(parents=True)
            secrets.write_text('[[rules]]\nid = "test-selection"\nregex = "AUTHORIZATION_[0-9]+"\n')
            invalid, gap = "AUTHORIZATION_123456789\n", "staged_secret_scan_failed"
    before = output.read_text()
    commit_fixture(root, "declare exact checks")
    configure_signer(root, tmp_path)
    note = root / ("src/selected.py" if checked_owner == "formatter" else "notes/selected.md")
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("VALUE = 1\n")
    output.write_text(invalid)
    staged_note, staged_output = (path.relative_to(root).as_posix() for path in (note, output))
    git(root, "add", staged_note, staged_output)
    head, index = git(root, "rev-parse", "HEAD"), git(root, "write-tree")

    selected = staged_note if selected_valid else staged_output
    completed = git_process(root, "commit", "-S", "-m", "test: selected index", "--", selected)

    assert completed.returncode == (0 if selected_valid else 1), completed.stderr
    assert git(root, "write-tree") == index
    assert git(root, "show", f":{staged_output}") == invalid.rstrip()
    assert output.read_text() == invalid
    assert git(root, "show", f"HEAD:{staged_output}") == before.rstrip()
    if selected_valid:
        assert git(root, "rev-parse", "HEAD") != head
        assert git_process(root, "verify-commit", "HEAD").returncode == 0
        assert git(root, "diff", "--cached", "--name-only") == staged_output
        assert git(root, "show", f"HEAD:{staged_note}") == note.read_text().rstrip()
    else:
        assert gap in completed.stderr
        assert git(root, "rev-parse", "HEAD") == head


@pytest.mark.parametrize(
    ("checked_owner", "policy_state"),
    [
        (owner, state)
        for owner in ("formatter", "secrets")
        for state in ("root-deleted", "root-replaced", "extension-deleted", "extension-replaced")
    ]
    + [("secrets", "ignore-replaced")],
)
def test_signed_commit_preserves_incumbent_native_policy(
    tmp_path: Path, *, checked_owner: str, policy_state: str
) -> None:
    """Unstaged policy mutations cannot waive an incumbent selected-index obligation."""
    root = prepared_work_lane(tmp_path).worktree
    extension = root / ".config" / "native-policy.toml"
    extension.parent.mkdir(exist_ok=True)
    if checked_owner == "formatter":
        policy = root / ".config/checks/ruff/ruff.toml"
        policy.parent.mkdir(parents=True, exist_ok=True)
        policy.write_text('extend = "../../native-policy.toml"\n')
        extension.write_text("line-length = 100\n")
        weakened = "line-length = 1000\n"
        output = root / "selected.py"
        before = "VALUE = 1\n"
        invalid = "VALUE = [" + ", ".join(str(value) for value in range(40)) + "]\n"
        gap = "pre_commit_python_format_failed"
        install_fixture_hook_runtime(root, native_executables={"ruff": Path(find_ruff_bin())})
    else:
        policy = root / ".config/checks/gitleaks/gitleaks.toml"
        policy.parent.mkdir(parents=True)
        policy.write_text('[extend]\npath = ".config/native-policy.toml"\n')
        extension.write_text('[[rules]]\nid = "test-selection"\nregex = "AUTHORIZATION_[0-9]+"\n')
        weakened = '[[rules]]\nid = "unrelated"\nregex = "UNRELATED_[0-9]+"\n'
        output = root / "selected.txt"
        before, invalid = "safe content\n", "AUTHORIZATION_123456789\n"
        gap = "staged_secret_scan_failed"
    output.write_text(before)
    ignore = root / ".config/checks/gitleaks/gitleaksignore"
    if policy_state == "ignore-replaced":
        ignore.write_text("unrelated.txt:test-selection:1\n")
        weakened = "selected.txt:test-selection:1\n"
    commit_fixture(root, "declare incumbent native configuration")
    configure_signer(root, tmp_path)
    output.write_text(invalid)
    git(root, "add", output.name)
    head, index = git(root, "rev-parse", "HEAD"), git(root, "write-tree")
    mutable = policy if policy_state.startswith("root-") else extension
    if policy_state == "ignore-replaced":
        mutable = ignore
    if policy_state.endswith("deleted"):
        mutable.unlink()
    else:
        mutable.write_text(weakened)

    completed = git_process(
        root, "commit", "-S", "-m", "test: incumbent native policy", "--", output.name
    )

    assert completed.returncode == 1, completed.stderr
    assert gap in completed.stderr
    assert git(root, "rev-parse", "HEAD") == head
    assert git(root, "write-tree") == index
    assert git(root, "show", f":{output.name}") == invalid.rstrip()
    assert output.read_text() == invalid
    assert git(root, "show", f"HEAD:{output.name}") == before.rstrip()
