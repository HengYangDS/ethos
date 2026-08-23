from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ethos.adapters.repo.commitment import changed_commitment_fields
from ethos.adapters.repo.commitment import exact_commitment_fields
from ethos.adapters.repo.commitment import load_commitment
from ethos.adapters.repo.commitment import load_lease_bound_commitment
from ethos.adapters.repo.commitment import load_repository_commitment
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_change_commitment
from tests.support.governed_repository import write_repository_commitment

if TYPE_CHECKING:
    from pathlib import Path


def _commit(repo: Path, message: str) -> str:
    git(repo, "add", ".")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "carrier",
    ["", "/absolute", "./relative", "../escape", "path\\windows", "path\x00nul"],
)
def test_commitment_carrier_malformed_paths_fail_closed(tmp_path: Path, carrier: str) -> None:
    write_repository_commitment(tmp_path)
    with pytest.raises(ValueError, match="commitment_carrier_invalid"):
        load_commitment(tmp_path, carrier=carrier)


def test_commitment_missing_malformed_and_canonical_public_boundaries(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match=r"repository_commitment_missing:\.ethos/commitment\.toml"):
        load_repository_commitment(tmp_path)

    write_repository_commitment(tmp_path)
    carrier = tmp_path / ".ethos/commitment.toml"
    carrier.write_bytes(b"\xff")
    with pytest.raises(
        ValueError, match=r"repository_commitment_unreadable:\.ethos/commitment\.toml"
    ):
        load_repository_commitment(tmp_path)

    carrier.write_text('id = "repository:obsolete"\n', encoding="utf-8")
    with pytest.raises(
        ValueError, match=r"repository_commitment_schema_unsupported:\.ethos/commitment\.toml"
    ):
        load_repository_commitment(tmp_path)

    carrier.write_text(
        carrier.read_text(encoding="utf-8").replace(
            'id = "repository:obsolete"', 'schema_version = 2\nid = "repository:obsolete"'
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match=r"repository_commitment_invalid:\.ethos/commitment\.toml"):
        load_repository_commitment(tmp_path)

    repository_id = write_repository_commitment(tmp_path)
    assert load_repository_commitment(tmp_path).id == repository_id


def test_commitment_exact_fields_and_digest_boundary(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_repository_commitment(repo)
    carrier = write_change_commitment(repo, "canonical", scope=("src/**",))
    head = _commit(repo, "canonical")

    fields = exact_commitment_fields(repo, head=head, carrier=carrier, change_id="canonical")
    assert fields["expected_head"] == head
    assert fields["expected_tree"] == git(repo, "rev-parse", "HEAD^{tree}")
    assert (
        load_commitment(
            repo,
            carrier=carrier,
            tree_ref=head,
            expected_digest=fields["base_commitment_digest"],
        ).id
        == "change:canonical"
    )
    with pytest.raises(ValueError, match="commitment_digest_mismatch"):
        load_commitment(repo, carrier=carrier, tree_ref=head, expected_digest="0" * 64)
    with pytest.raises(ValueError, match="commitment_carrier_path_invalid"):
        exact_commitment_fields(repo, head=head, carrier="../escape")
    with pytest.raises(ValueError, match="commitment_head_unreadable"):
        exact_commitment_fields(repo, head="0" * 40, carrier=carrier)


def test_commitment_changed_carrier_is_unique_and_readable(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_repository_commitment(repo)
    carrier = write_change_commitment(repo, "refine", scope=("src/**",))
    old_head = _commit(repo, "old")
    old_digest = load_commitment(repo, carrier=carrier, tree_ref=old_head).digest()

    write_change_commitment(repo, "refine", intent="Refined.", scope=("src/**",))
    new_head = _commit(repo, "new")
    fields = changed_commitment_fields(
        repo,
        old_head=old_head,
        new_head=new_head,
        commitment_id="change:refine",
        old_digest=old_digest,
    )
    assert fields["base_commitment_path"] == carrier

    with pytest.raises(ValueError, match="commitment_rebind_target_ambiguous"):
        changed_commitment_fields(
            repo,
            old_head=new_head,
            new_head=new_head,
            commitment_id="change:refine",
            old_digest=old_digest,
        )
    with pytest.raises(ValueError, match="commitment_rebind_target_unreadable"):
        changed_commitment_fields(
            repo,
            old_head="0" * 40,
            new_head=new_head,
            commitment_id="change:refine",
            old_digest=old_digest,
        )


def test_commitment_changed_carrier_accepts_byte_only_canonicalization(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_repository_commitment(repo)
    carrier = write_change_commitment(repo, "canonicalize", scope=("src/**",))
    old_head = _commit(repo, "old")
    old = load_commitment(repo, carrier=carrier, tree_ref=old_head)
    old_fields = exact_commitment_fields(repo, head=old_head, carrier=carrier)

    path = repo / carrier
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    new_head = _commit(repo, "canonicalize bytes")

    fields = changed_commitment_fields(
        repo,
        old_head=old_head,
        new_head=new_head,
        commitment_id=old.id,
        old_digest=old.digest(),
    )

    assert fields["base_commitment_path"] == carrier
    assert fields["base_commitment_digest"] == old.digest()
    assert fields["base_commitment_bytes_sha256"] != old_fields["base_commitment_bytes_sha256"]


def test_lease_bound_commitment_missing_and_canonical_coordinates(tmp_path: Path) -> None:
    repo = init_git_repo(tmp_path / "repo")
    write_repository_commitment(repo)
    carrier = write_change_commitment(repo, "lease", scope=("src/**",))
    head = _commit(repo, "lease")
    fields = exact_commitment_fields(repo, head=head, carrier=carrier, change_id="lease")

    with pytest.raises(ValueError, match="lease_expected_head_missing"):
        load_lease_bound_commitment(repo, lease={})
    assert load_lease_bound_commitment(repo, lease=fields, change_id="lease").id == "change:lease"
    with pytest.raises(ValueError, match="lease_base_commitment_bytes_mismatch"):
        load_lease_bound_commitment(
            repo,
            lease=fields | {"base_commitment_bytes_sha256": "0" * 64},
            change_id="lease",
        )
