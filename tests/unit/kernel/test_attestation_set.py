from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from datetime import datetime
from subprocess import CompletedProcess
from threading import Barrier
from typing import TYPE_CHECKING
from unittest.mock import Mock

import pytest

import ethos.adapters.repo.attestation_set as attestation_set
from ethos.adapters.repo.git import run_git
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


def _attestation(ordinal: int) -> Attestation:
    return Attestation.issue(
        {
            "schema_version": 2,
            "predicate": "observation:repository",
            "verifier": "agent:test:attestation-set",
            "subject": f"input:occurrence:{ordinal}",
            "issued_at": datetime(2026, 8, 14, tzinfo=UTC),
            "valid_from": None,
            "valid_until": None,
            "verdict": "pass",
            "payload": {
                "kind": "input:feedback",
                "body": {"occurrence": {"ordinal": ordinal, "source": "test"}},
            },
            "relations": (),
            "advisories": (),
            "evidence_refs": (f"evidence:test:{ordinal}",),
            "commitment_digest": None,
            "facts_digest": None,
            "plan_digest": None,
            "policy_digest": None,
            "effect_digest": None,
            "mints_authority": False,
        }
    )


def _canonical_root(repo: Path, tree: str) -> str:
    payload = (
        f"tree {tree}\n"
        "author ETHOS Attestation Set <attestations@example.invalid> 0 +0000\n"
        "committer ETHOS Attestation Set <attestations@example.invalid> 0 +0000\n"
        "encoding UTF-8\n\n"
        "ETHOS Attestation Set\n"
    ).encode()
    return (
        run_git(
            repo,
            "hash-object",
            "-t",
            "commit",
            "-w",
            "--stdin",
            stdin=payload,
            text=False,
        )
        .stdout.decode()
        .strip()
    )


def test_attestation_set_union_is_order_independent_idempotent_and_hash_sharded(
    tmp_path: Path,
) -> None:
    first_repo, second_repo = init_git_repo(tmp_path / "first"), init_git_repo(tmp_path / "second")
    one, two = _attestation(1), _attestation(2)

    first = attestation_set.record_attestations(first_repo, (one, two))
    second = attestation_set.record_attestations(second_repo, (two, one))
    repeated = attestation_set.record_attestations(first_repo, (two, one, two))

    assert first["root"] == second["root"] == repeated["root"]
    assert repeated["added"] == ()
    assert attestation_set.read_attestation_set(first_repo) == (
        first["root"],
        tuple(sorted((one, two), key=lambda item: item.id)),
    )
    root = str(first["root"])
    assert git(first_repo, "rev-list", "--parents", "-n", "1", root) == root
    assert git(first_repo, "ls-tree", "-r", "--name-only", root) == "\n".join(
        f"evidence/attestations/{item.id[:2]}/{item.id}.json"
        for item in sorted((one, two), key=lambda item: item.id)
    )


def test_attestation_set_read_uses_constant_git_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    attestations = tuple(_attestation(ordinal) for ordinal in range(24))
    attestation_set.record_attestations(repo, attestations)
    counted_run_git = Mock(wraps=attestation_set.run_git)
    monkeypatch.setattr(attestation_set, "run_git", counted_run_git)

    assert attestation_set.read_attestation_set(repo)[1] == tuple(
        sorted(attestations, key=lambda item: item.id)
    )
    assert counted_run_git.call_count <= 8


def test_attestation_set_rejects_identity_collision(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(4)
    collision = record.model_copy(update={"verdict": "block"})

    with pytest.raises(ValueError, match=f"attestation_set_identity_collision:{record.id}"):
        attestation_set.record_attestations(repo, (record, collision))


def test_attestation_set_rejects_malformed_carriers_and_honors_object_format(
    tmp_path: Path,
) -> None:
    malformed = init_git_repo(tmp_path / "malformed")
    record = _attestation(8)
    blob = run_git(
        malformed,
        "hash-object",
        "-w",
        "--stdin",
        stdin=record.canonical_json(),
    ).stdout.strip()
    index = tmp_path / "malformed.index"
    environment = {"GIT_INDEX_FILE": index.as_posix()}
    run_git(malformed, "read-tree", "--empty", env=environment)
    run_git(
        malformed,
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{blob},unexpected/{record.id}.json",
        env=environment,
    )
    tree = run_git(malformed, "write-tree", env=environment).stdout.strip()
    git(
        malformed,
        "update-ref",
        attestation_set.ATTESTATION_SET_REF,
        _canonical_root(malformed, tree),
    )
    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(malformed)

    symbolic = init_git_repo(tmp_path / "symbolic")
    victim = git(symbolic, "rev-parse", "HEAD")
    git(symbolic, "symbolic-ref", attestation_set.ATTESTATION_SET_REF, "refs/heads/dev")
    with pytest.raises(ValueError, match="attestation_set_ref_symbolic"):
        attestation_set.record_attestations(symbolic, (record,))
    assert git(symbolic, "rev-parse", "refs/heads/dev") == victim

    non_commit = init_git_repo(tmp_path / "non-commit")
    root = run_git(non_commit, "hash-object", "-w", "--stdin", stdin="not-a-root").stdout.strip()
    run_git(non_commit, "update-ref", attestation_set.ATTESTATION_SET_REF, root)
    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(non_commit)

    sha256 = init_git_repo(tmp_path / "sha256", object_format="sha256")
    root = str(attestation_set.record_attestations(sha256, (record,))["root"])
    assert len(root) == 64
    assert attestation_set.read_attestation_set(sha256)[0] == root


def test_attestation_set_empty_and_invalid_ref_observations_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    assert attestation_set.read_attestation_set(repo) == ("", ())

    original = attestation_set.run_git
    existing = str(attestation_set.record_attestations(repo, (_attestation(15),))["root"])
    cases = (
        (("rev-parse", "--git-dir"), 1, "attestation_set_repository_invalid"),
        (("symbolic-ref", "--quiet"), 2, "attestation_set_ref_invalid"),
        (("show-ref", "--exists"), 1, "attestation_set_ref_invalid"),
        (("show-ref", "--verify"), 1, "attestation_set_ref_invalid"),
    )
    for prefix, returncode, gap in cases:

        def observed(
            root: Path,
            *args: str,
            _prefix: tuple[str, ...] = prefix,
            _returncode: int = returncode,
            **kwargs,
        ):
            if args[: len(_prefix)] == _prefix:
                return CompletedProcess(args, _returncode, stdout="", stderr="")
            return original(root, *args, **kwargs)

        monkeypatch.setattr(attestation_set, "run_git", observed)
        with pytest.raises(ValueError, match=gap):
            attestation_set.read_attestation_set(repo)
        monkeypatch.setattr(attestation_set, "run_git", original)
    assert git(repo, "rev-parse", attestation_set.ATTESTATION_SET_REF) == existing


@pytest.mark.parametrize(
    ("command", "stdout"),
    [
        ("ls-tree", b"not-a-tree-record\0"),
        ("cat-file", b"not-a-batch-header\n"),
    ],
)
def test_attestation_set_rejects_malformed_git_protocol_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    stdout: bytes,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(9)
    attestation_set.record_attestations(repo, (record,))
    original = attestation_set.run_git

    def malformed(root: Path, *args: str, **kwargs):
        if args and args[0] == command:
            return CompletedProcess(args, 0, stdout=stdout, stderr=b"")
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", malformed)
    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


@pytest.mark.parametrize("command", ["ls-tree", "cat-file"])
def test_attestation_set_rejects_failed_git_protocol_reads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    attestation_set.record_attestations(repo, (_attestation(10),))
    original = attestation_set.run_git

    def failed(root: Path, *args: str, **kwargs):
        if args and args[0] == command:
            stdout = b"" if kwargs.get("text") is False else ""
            stderr = b"failed" if kwargs.get("text") is False else "failed"
            return CompletedProcess(args, 1, stdout=stdout, stderr=stderr)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", failed)
    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


def test_attestation_set_rejects_noncanonical_root_and_invalid_member(
    tmp_path: Path,
) -> None:
    record = _attestation(11)
    noncanonical = init_git_repo(tmp_path / "noncanonical")
    tree = git(noncanonical, "rev-parse", "HEAD^{tree}")
    root = git(noncanonical, "commit-tree", tree, "-m", "not canonical")
    git(noncanonical, "update-ref", attestation_set.ATTESTATION_SET_REF, root)
    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(noncanonical)

    invalid = init_git_repo(tmp_path / "invalid-member")
    blob = run_git(invalid, "hash-object", "-w", "--stdin", stdin="not-json").stdout.strip()
    index = tmp_path / "invalid-member.index"
    environment = {"GIT_INDEX_FILE": index.as_posix()}
    run_git(invalid, "read-tree", "--empty", env=environment)
    run_git(
        invalid,
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{blob},evidence/attestations/{record.id[:2]}/{record.id}.json",
        env=environment,
    )
    tree = run_git(invalid, "write-tree", env=environment).stdout.strip()
    git(invalid, "update-ref", attestation_set.ATTESTATION_SET_REF, _canonical_root(invalid, tree))
    with pytest.raises(ValueError, match="attestation_set_member_invalid"):
        attestation_set.read_attestation_set(invalid)


def test_attestation_set_rejects_semantic_collision_and_exhausted_cas(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    first = _attestation(12)
    payload = first.model_dump(mode="python", exclude={"id"})
    payload["issued_at"] = datetime(2026, 8, 14, 0, 0, 1, tzinfo=UTC)
    second = Attestation.issue(payload)
    attestation_set.record_attestations(repo, (first, second))
    with pytest.raises(ValueError, match="attestation_set_semantic_collision"):
        attestation_set.record_attestation_once(repo, _attestation(12))

    fresh = init_git_repo(tmp_path / "fresh")
    monkeypatch.setattr(attestation_set, "_MAX_CAS_ATTEMPTS", 1)
    monkeypatch.setattr(attestation_set, "_compare_and_swap_root", lambda *_args, **_kwargs: False)
    with pytest.raises(ValueError, match="attestation_set_cas_retry_exhausted"):
        attestation_set.record_attestations(fresh, (_attestation(13),))
    with pytest.raises(ValueError, match="attestation_set_cas_retry_exhausted"):
        attestation_set.record_attestation_once(fresh, _attestation(14))


def test_attestation_set_concurrent_writers_recompute_union_after_stale_cas(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    one, two = _attestation(5), _attestation(6)
    barrier, original, synchronized = Barrier(2), attestation_set.run_git, 0

    def synchronized_update(root: Path, *args: str, **kwargs):
        nonlocal synchronized
        if args[:2] == ("update-ref", attestation_set.ATTESTATION_SET_REF) and synchronized < 2:
            synchronized += 1
            barrier.wait(timeout=10)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", synchronized_update)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = tuple(
            executor.submit(attestation_set.record_attestations, repo, (record,))
            for record in (one, two)
        )
        results = tuple(future.result(timeout=20) for future in futures)

    root, members = attestation_set.read_attestation_set(repo)
    assert root in {str(result["root"]) for result in results}
    assert members == tuple(sorted((one, two), key=lambda item: item.id))


def test_attestation_set_concurrent_single_winner_selects_one_semantic_witness(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    first = _attestation(7)
    payload = first.model_dump(mode="python", exclude={"id"})
    payload["issued_at"] = datetime(2026, 8, 14, 0, 0, 1, tzinfo=UTC)
    second = Attestation.issue(payload)
    barrier, original, synchronized = Barrier(2), attestation_set.run_git, 0

    def synchronized_update(root: Path, *args: str, **kwargs):
        nonlocal synchronized
        if args[:2] == ("update-ref", attestation_set.ATTESTATION_SET_REF) and synchronized < 2:
            synchronized += 1
            barrier.wait(timeout=10)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", synchronized_update)
    with ThreadPoolExecutor(max_workers=2) as executor:
        selected = tuple(
            future.result(timeout=20)
            for future in (
                executor.submit(attestation_set.record_attestation_once, repo, first),
                executor.submit(attestation_set.record_attestation_once, repo, second),
            )
        )

    assert selected[0] == selected[1]
    assert attestation_set.read_attestation_set(repo)[1] == (selected[0],)
