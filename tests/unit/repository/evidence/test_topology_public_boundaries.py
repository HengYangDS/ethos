from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.evidence.topology import evidence_topology_report

if TYPE_CHECKING:
    from pathlib import Path


def _profile(root: Path, *, durable_evidence: str = "evidence") -> None:
    profile = root / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text(
        f'profile_id = "test"\n[roots]\ndurable_evidence = "{durable_evidence}"\n',
        encoding="utf-8",
    )


def test_evidence_topology_invalid_profile_fails_closed(tmp_path: Path) -> None:
    profile = tmp_path / ".ethos/profile.toml"
    profile.parent.mkdir()
    profile.write_text("profile_id = [\n", encoding="utf-8")

    report = evidence_topology_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["required_gaps"]
    assert report["counts"] == {"historical_artifacts": 0}


def test_evidence_topology_kernel_missing_malformed_and_canonical(tmp_path: Path) -> None:
    _profile(tmp_path)
    assert evidence_topology_report(tmp_path)["required_gaps"] == ["evidence_root_missing"]

    evidence = tmp_path / "evidence"
    (evidence / "attestations").mkdir(parents=True)
    (evidence / "attestations/current.json").write_text("{}\n", encoding="utf-8")
    (evidence / "foreign").mkdir()
    (evidence / "README.md").write_text("# Evidence\n", encoding="utf-8")
    report = evidence_topology_report(tmp_path)
    assert report["required_gaps"] == ["evidence_root_dir_not_allowed:foreign"]

    (evidence / "foreign").rmdir()
    assert evidence_topology_report(tmp_path)["counts"] == {"historical_artifacts": 1}


def test_evidence_topology_curated_missing_malformed_and_canonical(tmp_path: Path) -> None:
    _profile(tmp_path, durable_evidence="docs/evidence")
    missing = evidence_topology_report(tmp_path)
    assert missing["required_gaps"] == ["evidence_root_missing"]
    assert missing["counts"] == {"curated_artifacts": 0}

    evidence = tmp_path / "docs/evidence"
    (evidence / "attestations").mkdir(parents=True)
    (evidence / "attestations/current.json").write_text("{}\n", encoding="utf-8")
    (evidence / "guide.md").write_text("invalid root file\n", encoding="utf-8")
    report = evidence_topology_report(tmp_path)
    assert report["required_gaps"] == ["evidence_root_file_not_allowed:guide.md"]
    assert report["counts"] == {"curated_artifacts": 2}

    (evidence / "guide.md").unlink()
    (evidence / "README.md").write_text("# Curated evidence\n", encoding="utf-8")
    canonical = evidence_topology_report(tmp_path)
    assert canonical["verdict"] == "pass"
    assert canonical["counts"]["curated_artifacts"] == 1
