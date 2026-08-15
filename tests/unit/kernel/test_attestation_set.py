from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC
from datetime import datetime
from threading import Barrier
from typing import TYPE_CHECKING

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


def _write_tree(
    repo: Path,
    index: Path,
    *,
    entries: tuple[tuple[str, str, str], ...],
) -> str:
    environment = {"GIT_INDEX_FILE": index.as_posix()}
    run_git(repo, "read-tree", "--empty", env=environment)
    for mode, blob, path in entries:
        run_git(
            repo,
            "update-index",
            "--add",
            "--cacheinfo",
            f"{mode},{blob},{path}",
            env=environment,
        )
    return run_git(repo, "write-tree", env=environment).stdout.strip()


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


def _member_path(identity: str) -> str:
    return f"evidence/attestations/{identity[:2]}/{identity}.json"


def test_attestation_set_union_is_order_independent_and_idempotent(tmp_path: Path) -> None:
    first_repo = init_git_repo(tmp_path / "first")
    second_repo = init_git_repo(tmp_path / "second")
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


def test_attestation_set_root_is_parentless_and_hash_sharded(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(3)

    result = attestation_set.record_attestations(repo, (record,))

    root = str(result["root"])
    assert git(repo, "rev-list", "--parents", "-n", "1", root) == root
    assert git(repo, "ls-tree", "-r", "--name-only", root) == (
        f"evidence/attestations/{record.id[:2]}/{record.id}.json"
    )
    assert git(repo, "show", f"{root}:evidence/attestations/{record.id[:2]}/{record.id}.json") == (
        record.canonical_json()
    )


def test_attestation_set_rejects_different_bytes_for_one_identity(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(4)
    attestation_set.record_attestations(repo, (record,))
    path = _member_path(record.id)
    corrupted = record.canonical_json().replace('"verdict":"pass"', '"verdict":"block"')
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin=corrupted).stdout.strip()
    index = tmp_path / "corrupt-index"
    environment = {"GIT_INDEX_FILE": index.as_posix()}
    run_git(repo, "read-tree", "--empty", env=environment)
    run_git(repo, "update-index", "--add", "--cacheinfo", f"100644,{blob},{path}", env=environment)
    tree = run_git(repo, "write-tree", env=environment).stdout.strip()
    root = _canonical_root(repo, tree)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, root)

    with pytest.raises(ValueError, match=f"attestation_set_member_invalid:{path}"):
        attestation_set.record_attestations(repo, (record,))


def test_attestation_set_rejects_noncanonical_tree_paths(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(7)
    raw = record.canonical_json()
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin=raw).stdout.strip()
    index = tmp_path / "extra-index"
    environment = {"GIT_INDEX_FILE": index.as_posix()}
    run_git(repo, "read-tree", "--empty", env=environment)
    run_git(
        repo,
        "update-index",
        "--add",
        "--cacheinfo",
        f"100644,{blob},unexpected/{record.id}.json",
        env=environment,
    )
    tree = run_git(repo, "write-tree", env=environment).stdout.strip()
    root = git(repo, "commit-tree", tree, "-m", "noncanonical")
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, root)

    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


def test_attestation_set_normalizes_non_utf8_tree_path_to_typed_gap(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin="invalid path").stdout.strip()
    tree = (
        run_git(
            repo,
            "mktree",
            "-z",
            stdin=f"100644 blob {blob}\t".encode() + b"\xff\0",
            text=False,
        )
        .stdout.decode()
        .strip()
    )
    root = _canonical_root(repo, tree)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, root)

    with pytest.raises(ValueError, match=r"^attestation_set_root_invalid$"):
        attestation_set.read_attestation_set(repo)


@pytest.mark.parametrize(
    ("case", "entries"),
    [
        (
            "executable-member",
            lambda record, blob: (
                ("100755", blob, _member_path(record.id)),
            ),
        ),
        (
            "symlink-member",
            lambda record, blob: (
                ("120000", blob, _member_path(record.id)),
            ),
        ),
        (
            "nested-subtree-member",
            lambda record, blob: (
                (
                    "100644",
                    blob,
                    f"evidence/attestations/{record.id[:2]}/nested/{record.id}.json",
                ),
            ),
        ),
        (
            "extra-entry",
            lambda record, blob: (
                ("100644", blob, _member_path(record.id)),
                ("100644", blob, f"unexpected/{record.id}.json"),
            ),
        ),
    ],
)
def test_attestation_set_reader_rejects_noncanonical_tree_entries(
    tmp_path: Path, case: str, entries
) -> None:
    repo = init_git_repo(tmp_path / case)
    record = _attestation(70)
    blob = run_git(
        repo, "hash-object", "-w", "--stdin", stdin=record.canonical_json()
    ).stdout.strip()
    tree = _write_tree(repo, tmp_path / f"{case}.index", entries=entries(record, blob))
    root = _canonical_root(repo, tree)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, root)

    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


def test_attestation_set_reader_rejects_extra_empty_subtree(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(71)
    canonical = attestation_set.record_attestations(repo, (record,))
    evidence_tree = git(repo, "rev-parse", f"{canonical['root']}^{{tree}}:evidence")
    empty_tree = run_git(repo, "mktree", stdin="").stdout.strip()
    tree = (
        run_git(
            repo,
            "mktree",
            stdin=(
                f"040000 tree {evidence_tree}\tevidence\n"
                f"040000 tree {empty_tree}\textra-empty\n"
            ),
        )
        .stdout.strip()
    )
    root = _canonical_root(repo, tree)
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, root)

    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


def test_attestation_set_rejects_noncanonical_commit_metadata(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    record = _attestation(8)
    canonical = attestation_set.record_attestations(repo, (record,))
    tree = git(repo, "rev-parse", f"{canonical['root']}^{{tree}}")
    parented = git(repo, "commit-tree", tree, "-p", "HEAD", "-m", "not canonical")
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, parented)

    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


@pytest.mark.parametrize(
    ("case", "build_root"),
    [
        (
            "parented-root",
            lambda repo, tree: git(
                repo, "commit-tree", tree, "-p", "HEAD", "-m", "ETHOS Attestation Set"
            ),
        ),
        (
            "nonfixed-metadata-root",
            lambda repo, tree: git(repo, "commit-tree", tree, "-m", "ETHOS Attestation Set"),
        ),
    ],
)
def test_attestation_set_record_rejects_invalid_selected_root_before_idempotent_return(
    tmp_path: Path, case: str, build_root
) -> None:
    repo = init_git_repo(tmp_path / case)
    record = _attestation(80)
    canonical = attestation_set.record_attestations(repo, (record,))
    tree = git(repo, "rev-parse", f"{canonical['root']}^{{tree}}")
    git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, build_root(repo, tree))

    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.record_attestations(repo, (record,))


def test_attestation_set_uses_the_repository_object_format(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo", object_format="sha256")

    root = str(attestation_set.record_attestations(repo, (_attestation(9),))["root"])

    assert len(root) == 64
    assert attestation_set.read_attestation_set(repo)[0] == root


def test_attestation_set_rejects_symbolic_carrier_without_moving_target(
    tmp_path: Path,
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    victim = git(repo, "rev-parse", "HEAD")
    git(repo, "symbolic-ref", attestation_set.ATTESTATION_SET_REF, "refs/heads/dev")

    with pytest.raises(ValueError, match="attestation_set_ref_symbolic"):
        attestation_set.record_attestations(repo, (_attestation(10),))

    assert git(repo, "rev-parse", "refs/heads/dev") == victim


def test_attestation_set_rejects_dangling_selected_ref(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    ref_path = repo / git(
        repo, "rev-parse", "--git-path", attestation_set.ATTESTATION_SET_REF
    )
    ref_path.parent.mkdir(parents=True, exist_ok=True)
    ref_path.write_text(f"{'1' * 40}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="attestation_set_ref_invalid"):
        attestation_set.read_attestation_set(repo)


def test_attestation_set_rejects_non_commit_selected_root(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    blob = run_git(repo, "hash-object", "-w", "--stdin", stdin="not-a-root").stdout.strip()
    run_git(repo, "update-ref", attestation_set.ATTESTATION_SET_REF, blob)

    with pytest.raises(ValueError, match="attestation_set_root_invalid"):
        attestation_set.read_attestation_set(repo)


def test_concurrent_attestation_set_writers_recompute_union_after_stale_cas(
    tmp_path: Path, monkeypatch
) -> None:
    repo = init_git_repo(tmp_path / "repo")
    one, two = _attestation(5), _attestation(6)
    barrier = Barrier(2)
    original = attestation_set.run_git

    synchronized = 0

    def synchronized_update(root: Path, *args: str, **kwargs):
        nonlocal synchronized
        if args[:2] == ("update-ref", attestation_set.ATTESTATION_SET_REF) and synchronized < 2:
            synchronized += 1
            barrier.wait(timeout=10)
        return original(root, *args, **kwargs)

    monkeypatch.setattr(attestation_set, "run_git", synchronized_update)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = (
            executor.submit(attestation_set.record_attestations, repo, (one,)),
            executor.submit(attestation_set.record_attestations, repo, (two,)),
        )
        results = tuple(future.result(timeout=20) for future in futures)

    root, members = attestation_set.read_attestation_set(repo)
    assert root in {str(result["root"]) for result in results}
    assert members == tuple(sorted((one, two), key=lambda item: item.id))
