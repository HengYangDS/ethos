"""Real Git boundaries for canonical Attestation set preservation and selection."""

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
import ethos.adapters.repo.git_object as git_object
from ethos.adapters.repo.git import run_git
from ethos.contracts.semantic import Attestation
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.semantic import attestation_fixture

if TYPE_CHECKING:
    from pathlib import Path


def _attestation(ordinal: int, *, payload_bytes: int = 0) -> Attestation:
    occurrence = {"ordinal": ordinal, "source": "test"}
    if payload_bytes:
        occurrence["text"] = "x" * payload_bytes
    return attestation_fixture(
        predicate="observation:repository",
        verifier="agent:test:attestation-set",
        subject=f"input:occurrence:{ordinal}",
        issued_at=datetime(2026, 8, 14, tzinfo=UTC),
        payload_kind="input:feedback",
        payload_body={"occurrence": occurrence},
        evidence_refs=(f"evidence:test:{ordinal}",),
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


@pytest.mark.parametrize("object_format", ["sha1", "sha256"])
def test_attestation_set_read_uses_constant_git_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, object_format: str
) -> None:
    repo = init_git_repo(tmp_path / "repo", object_format=object_format)
    attestations = tuple(_attestation(ordinal) for ordinal in range(24))
    attestation_set.record_attestations(repo, attestations)
    counted_run_git = Mock(wraps=attestation_set.run_git)
    monkeypatch.setattr(attestation_set, "run_git", counted_run_git)
    monkeypatch.setattr(git_object, "run_git", counted_run_git)
    with pytest.raises(ValueError, match="git_object_batch_invalid"):
        git_object.read_objects(repo, ("0" * 40,), kind=())

    assert attestation_set.read_attestation_set(repo)[1] == tuple(
        sorted(attestations, key=lambda item: item.id)
    )
    assert [call.args[1] for call in counted_run_git.call_args_list] == [
        "symbolic-ref",
        "show-ref",
        "ls-tree",
        "cat-file",
        "hash-object",
    ]


def test_attestation_set_ignores_workspace_history_and_needs_no_directory(tmp_path: Path) -> None:
    """A worktree file never selects or overrides a current Git-set member."""
    repo = init_git_repo(tmp_path / "repo")
    one, two = _attestation(41), _attestation(42)
    index = (repo / ".git/index").read_bytes()
    before = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    current = attestation_set.record_attestations(repo, (one,))
    assert not (repo / "evidence").exists()
    historical = repo / f"evidence/attestations/{two.id}.json"
    historical.parent.mkdir(parents=True)
    historical.write_text("not a canonical Attestation\n")
    assert attestation_set.read_attestation_set(repo) == (current["root"], (one,))
    historical.unlink()
    historical.parent.rmdir()
    (repo / "evidence").rmdir()
    attestation_set.record_attestations(repo, (two,))
    assert attestation_set.read_attestation_set(repo)[1] == tuple(
        sorted((one, two), key=lambda item: item.id)
    )
    assert not (repo / "evidence").exists()
    assert (repo / ".git/index").read_bytes() == index
    assert git(repo, "status", "--porcelain=v1", "--untracked-files=all") == before


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
    with pytest.raises(ValueError, match="attestation_set_repository_invalid"):
        attestation_set.read_attestation_set(tmp_path)
    repo = init_git_repo(tmp_path / "repo")
    assert attestation_set.read_attestation_set(repo) == ("", ())

    original = attestation_set.run_git
    existing = str(attestation_set.record_attestations(repo, (_attestation(15),))["root"])
    cases = (
        (("symbolic-ref", "--quiet"), 2, "attestation_set_ref_invalid"),
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


@pytest.mark.parametrize("warm", [False, True])
@pytest.mark.parametrize(
    "fault",
    [
        "tree-malformed",
        "batch-malformed",
        "tree-failed",
        "batch-failed",
        "root-kind",
        "root-metadata",
        "root-digest",
        "member-kind",
    ],
)
def test_attestation_set_rejects_failed_or_corrupt_current_reads(
    tmp_path, monkeypatch, fault, warm
):
    """Warm pure validation never hides failed reads or corrupt typed object frames."""
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(9)
    selected = attestation_set.record_attestations(repo, (record,))["root"]
    if warm:
        assert attestation_set.read_attestation_set(repo) == (selected, (record,))
    original = attestation_set.run_git
    command = "ls-tree" if fault.startswith("tree-") else "cat-file"

    def observe(root, *args, **kwargs):
        result = original(root, *args, **kwargs)
        if args[0] != command:
            return result
        if fault.endswith("failed"):
            return CompletedProcess(args, 1, stdout=b"", stderr=b"failed")
        output = result.stdout
        if fault.endswith("malformed"):
            output = b"not-a-native-record"
        elif fault == "root-kind":
            output = output.replace(b" commit ", b" blob ", 1)
        elif fault == "member-kind":
            output = output.replace(b" blob ", b" commit ", 1)
        elif fault == "root-metadata":
            output = output.replace(b"author ETHOS", b"author Other", 1)
        else:
            tree = git(repo, "rev-parse", f"{selected}^{{tree}}").encode()
            output = output.replace(b"tree " + tree, b"tree " + b"0" * len(tree), 1)
        return CompletedProcess(args, 0, stdout=output, stderr=b"")

    monkeypatch.setattr(
        git_object if command == "cat-file" else attestation_set, "run_git", observe
    )
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
        if (
            args[:3] == ("update-ref", "--no-deref", attestation_set.ATTESTATION_SET_REF)
            and synchronized < 2
        ):
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

    assert synchronized == 2
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
        if (
            args[:3] == ("update-ref", "--no-deref", attestation_set.ATTESTATION_SET_REF)
            and synchronized < 2
        ):
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

    assert synchronized == 2
    assert selected[0] == selected[1]
    assert attestation_set.read_attestation_set(repo)[1] == (selected[0],)


@pytest.mark.parametrize(
    ("size", "expected_root"),
    [
        (1, "c4caabe7fef61ba9abf6c900b5e2ac4db1474032"),
        (24, "36b278d7d0470a72e9e4bc94189fbca727c3c685"),
    ],
)
def test_attestation_set_write_has_constant_native_process_cost(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int, expected_root: str
) -> None:
    """Adding members preserves pinned roots without one Git process per member."""
    repo = init_git_repo(tmp_path / 'quoted "workspace" 雪')
    records = tuple(_attestation(ordinal) for ordinal in range(size))
    before_index = (repo / ".git/index").read_bytes()
    counted = Mock(wraps=attestation_set.run_git)
    monkeypatch.setattr(attestation_set, "run_git", counted)

    result = attestation_set.record_attestations(repo, records)

    assert result["root"] == expected_root
    writes = [
        call
        for call in counted.call_args_list
        if call.args[1] in {"hash-object", "update-index", "write-tree"}
    ]
    assert len(writes) <= 4
    assert (repo / ".git/index").read_bytes() == before_index
    assert not tuple((repo / ".git").glob("attestation-set-*"))
    assert attestation_set.read_attestation_set(repo)[1] == tuple(
        sorted(records, key=lambda item: item.id)
    )


@pytest.mark.parametrize("payload_bytes", [0, 131_072])
def test_attestation_set_reuses_validation_but_not_selected_membership(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload_bytes: int
) -> None:
    """Identical bytes decode once while changed and missing refs stay observable."""
    repo = init_git_repo(tmp_path / "repo")
    one, two = _attestation(3_001, payload_bytes=payload_bytes), _attestation(3_002 + payload_bytes)
    first = attestation_set.record_attestations(repo, (one,))
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    for _ in range(3):
        assert attestation_set.read_attestation_set(repo) == (first["root"], (one,))
    assert validate.call_count == 1

    second = attestation_set.record_attestations(repo, (two,))
    assert attestation_set.read_attestation_set(repo) == (
        second["root"],
        tuple(sorted((one, two), key=lambda item: item.id)),
    )
    assert validate.call_count == 2
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, str(first["root"]))
    assert attestation_set.read_attestation_set(repo) == (first["root"], (one,))
    git(repo, "update-ref", "-d", attestation_set.ATTESTATION_SET_REF)
    assert attestation_set.read_attestation_set(repo) == ("", ())


def test_attestation_set_growth_materializes_only_new_member_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exact selected tree is reused instead of rewriting preserved members."""
    repo = init_git_repo(tmp_path / "repo")
    attestation_set.record_attestations(repo, tuple(_attestation(n) for n in range(24)))
    new = _attestation(3_006)
    original, materialized_bytes = attestation_set.run_git, 0

    def observed(root: Path, *args: str, **kwargs):
        nonlocal materialized_bytes
        if args[0] == "hash-object" and "-w" in args and "-t" not in args:
            if "--stdin-paths" in args:
                materialized_bytes += sum(
                    len((root / name).read_bytes()) for name in kwargs["stdin"].splitlines()
                )
            else:
                materialized_bytes += len(kwargs["stdin"])
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", observed)
    attestation_set.record_attestations(repo, (new,))
    assert materialized_bytes == len(new.canonical_json().encode())
    assert len(attestation_set.read_attestation_set(repo)[1]) == 25


@pytest.mark.parametrize("command", ["read-tree", "hash-object", "update-index", "write-tree"])
def test_attestation_set_failed_batch_preserves_ref_index_and_cleans_staging(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: str
) -> None:
    """Failure in any native batch phase leaves no selected effect or owned scratch."""
    repo = init_git_repo(tmp_path / "repo")
    one, two = _attestation(3_004), _attestation(3_005)
    before = attestation_set.record_attestations(repo, (one,))
    before_index = (repo / ".git/index").read_bytes()
    original = attestation_set.run_git

    def failed(root: Path, *args: str, **kwargs):
        if args[0] == command and not kwargs.get("observation"):
            message = "native_batch_interrupted"
            raise OSError(message)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", failed)
    with pytest.raises(OSError, match="native_batch_interrupted"):
        attestation_set.record_attestations(repo, (two,))
    assert git(repo, "rev-parse", attestation_set.ATTESTATION_SET_REF) == before["root"]
    assert (repo / ".git/index").read_bytes() == before_index
    assert not tuple((repo / ".git").glob("attestation-set-*"))


def test_attestation_set_oversized_member_does_not_consume_reuse_capacity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A large valid member stays admissible without retaining its bytes or value."""
    repo = init_git_repo(tmp_path / "repo")
    large = _attestation(3_007, payload_bytes=64 * 1024 * 1024)
    attestation_set.record_attestations(repo, (large,))
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    assert attestation_set.read_attestation_set(repo)[1] == (large,)
    assert attestation_set.read_attestation_set(repo)[1] == (large,)
    assert validate.call_count == 2


def test_attestation_set_eviction_changes_work_not_membership_or_meaning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reading more than the reuse capacity evicts old bytes without losing evidence."""
    repo = init_git_repo(tmp_path / "repo")
    records = tuple(
        sorted(
            (_attestation(n, payload_bytes=33 * 1024 * 1024) for n in (4_000, 4_001)),
            key=lambda x: x.id,
        )
    )
    first = records[0]
    first_root = attestation_set.record_attestations(repo, (first,))["root"]
    assert attestation_set.read_attestation_set(repo)[1] == (first,)
    attestation_set.record_attestations(repo, records[1:])
    assert len(attestation_set.read_attestation_set(repo)[1]) == len(records)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, str(first_root))
    validate = Mock(wraps=Attestation.model_validate_json)
    monkeypatch.setattr(Attestation, "model_validate_json", validate)

    assert attestation_set.read_attestation_set(repo) == (first_root, (first,))
    assert validate.call_count == 1


def test_attestation_set_new_bytes_cannot_inherit_a_cached_member_identity(
    tmp_path: Path,
) -> None:
    """A selected blob with changed bytes is validated even under the old member path."""
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(3_009)
    valid = attestation_set.record_attestations(repo, (record,))["root"]
    assert attestation_set.read_attestation_set(repo)[1] == (record,)
    changed = record.canonical_json().replace('"source":"test"', '"source":"changed"')
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin=changed).stdout.strip()
    environment = {"GIT_INDEX_FILE": (tmp_path / "changed.index").as_posix()}
    run_git(repo, "read-tree", str(valid), env=environment)
    run_git(
        repo,
        "update-index",
        "--cacheinfo",
        f"100644,{blob},evidence/attestations/{record.id[:2]}/{record.id}.json",
        env=environment,
    )
    tree = run_git(repo, "write-tree", env=environment).stdout.strip()
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, _canonical_root(repo, tree))
    with pytest.raises(ValueError, match="attestation_set_member_invalid"):
        attestation_set.read_attestation_set(repo)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, str(valid))
    assert attestation_set.read_attestation_set(repo)[1] == (record,)
