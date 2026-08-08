from pathlib import Path

from ethos.adapters.openspec.archive_projection import normalize_projected_specs


def test_normalize_projected_specs_changes_only_terminal_newlines(tmp_path: Path) -> None:
    root = tmp_path
    projected = root / "openspec/specs/contracts/spec.md"
    projected.parent.mkdir(parents=True)
    original = b"## Purpose\n\nKeep interior spacing.  \n\n## Requirements\n\nBody.\n\n\n"
    projected.write_bytes(original)
    archived = root / "openspec/changes/archive/2026-08-08-change/spec.md"
    archived.parent.mkdir(parents=True)
    archived.write_bytes(b"archived carrier\n\n")
    binary = root / "openspec/specs/contracts/fixture.bin"
    binary.write_bytes(b"\xff\x00\n\n")

    normalized = normalize_projected_specs(
        root,
        paths=(
            "openspec/specs/contracts/spec.md",
            "openspec/changes/archive/2026-08-08-change/spec.md",
            "openspec/specs/contracts/fixture.bin",
        ),
    )

    assert normalized == ("openspec/specs/contracts/spec.md",)
    assert projected.read_bytes() == original.rstrip(b"\n") + b"\n"
    assert archived.read_bytes() == b"archived carrier\n\n"
    assert binary.read_bytes() == b"\xff\x00\n\n"
