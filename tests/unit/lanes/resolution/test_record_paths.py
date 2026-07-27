from __future__ import annotations

from pathlib import Path

from ethos.adapters.mutation.resolution.records.roots import record_path_is_safe


def test_record_path_is_safe_rejects_escape_and_symlinked_owner_components(
    tmp_path: Path, monkeypatch
) -> None:
    record_root = tmp_path / "records"
    record_root.mkdir()
    normal = record_root / "decisions" / "record.json"

    assert record_path_is_safe(record_root, normal)
    assert not record_path_is_safe(record_root, tmp_path / "outside" / "record.json")
    assert not record_path_is_safe(record_root, record_root / "decisions" / ".." / "escape.json")

    linked_root = tmp_path / "linked-records"
    linked_root.symlink_to(record_root, target_is_directory=True)
    assert not record_path_is_safe(linked_root, linked_root / "record.json")

    nested_target = tmp_path / "nested-target"
    nested_target.mkdir()
    nested_link = record_root / "decisions"
    nested_link.symlink_to(nested_target, target_is_directory=True)
    assert not record_path_is_safe(record_root, nested_link / "record.json")

    candidate = record_root / "unresolvable.json"
    resolve = Path.resolve

    def raise_for_candidate(path: Path, **_kwargs: object) -> Path:
        if path == candidate.absolute():
            message = "resolution unavailable"
            raise OSError(message)
        return resolve(path)

    monkeypatch.setattr(Path, "resolve", raise_for_candidate)
    assert not record_path_is_safe(record_root, candidate)
