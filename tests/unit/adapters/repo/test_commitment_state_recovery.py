from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest
import tomli_w

import ethos.adapters.repo.commitment as commitment
from tests.support.semantic import commitment_v2

if TYPE_CHECKING:
    from pathlib import Path


def _repository_commitment(root: Path) -> str:
    repository_id = "repository:test"
    path = root / ".ethos/commitment.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        tomli_w.dumps(
            commitment_v2(
                id=repository_id,
                intent="Govern.",
                subjects=(repository_id,),
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )
    return repository_id


def _change(root: Path, change_id: str) -> str:
    relative = f"openspec/changes/{change_id}/commitment.toml"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        tomli_w.dumps(
            commitment_v2(
                id=f"change:{change_id}",
                intent="Change.",
                subjects=(commitment.load_repository_commitment(root).id,),
            ).model_dump(mode="python")
        ),
        encoding="utf-8",
    )
    return relative


def test_profile_selected_commitment_rejects_invalid_profile(tmp_path: Path) -> None:
    _repository_commitment(tmp_path)
    (tmp_path / ".ethos/profile.toml").write_text("profile_id = [\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repository_profile_invalid"):
        commitment.load_commitment(tmp_path)


def test_changed_commitment_rejects_unreadable_diff_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        commitment,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=b"\xff\0"),
    )

    with pytest.raises(ValueError, match="commitment_rebind_target_path_invalid"):
        commitment.changed_commitment_fields(
            tmp_path,
            old_head="a" * 40,
            new_head="b" * 40,
            commitment_id="change:test",
            old_digest="0" * 64,
        )


def test_changed_commitment_skips_noncarriers_and_invalid_candidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        commitment,
        "run_git",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0,
            stdout=b"README.md\0openspec/changes/bad/commitment.toml\0",
        ),
    )
    monkeypatch.setattr(
        commitment,
        "exact_commitment_fields",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )

    with pytest.raises(ValueError, match="commitment_rebind_target_ambiguous"):
        commitment.changed_commitment_fields(
            tmp_path,
            old_head="a" * 40,
            new_head="b" * 40,
            commitment_id="change:test",
            old_digest="0" * 64,
        )


def test_lease_binding_maps_semantic_and_reload_failures(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    expected = {
        "expected_head": "a" * 40,
        "expected_tree": "b" * 40,
        "base_commitment_path": "openspec/changes/test/commitment.toml",
        "base_commitment_bytes_sha256": "c" * 64,
        "base_commitment_digest": "d" * 64,
    }
    monkeypatch.setattr(
        commitment,
        "exact_commitment_fields",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("commitment_missing:test")),
    )
    with pytest.raises(ValueError, match="lease_base_commitment_digest_mismatch"):
        commitment.load_lease_bound_commitment(tmp_path, lease=expected)

    monkeypatch.setattr(commitment, "exact_commitment_fields", lambda *_args, **_kwargs: expected)
    monkeypatch.setattr(
        commitment,
        "load_commitment",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError("invalid")),
    )
    with pytest.raises(ValueError, match="lease_base_commitment_digest_mismatch"):
        commitment.load_lease_bound_commitment(tmp_path, lease=expected)
