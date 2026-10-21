"""Verify committed received archives without extracting or relabelling their entries."""

from __future__ import annotations

import hashlib
import importlib
import io
import stat
import warnings
import zipfile
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ethos.repository.policy.quality.sources import source_contract_paths
from ethos.repository.profile import SourceContract
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.governed_repository import write_test_profile

if TYPE_CHECKING:
    from pathlib import Path

CONTENT = b"export const value = 42;\n"
MEMBER = "archify/bin/archify.mjs"


@pytest.mark.parametrize(
    "defect",
    [
        "none",
        "archive-bytes",
        "artifact-bytes",
        "missing",
        "duplicate",
        "link",
        "encrypted",
        "bzip2",
        "corrupt",
        "oversized",
    ],
)
def test_received_archive_entries_match_their_pinned_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, defect: str
) -> None:
    """A pinned committed archive and each declared entry decide byte identity, not a label."""
    repo = init_git_repo(tmp_path / "repository")
    original = _archive(defect)
    reference = f"supply/archify.zip#sha256:{hashlib.sha256(original).hexdigest()}"
    (repo / "supply").mkdir()
    (repo / "supply/archify.zip").write_bytes(
        original + b"changed" if defect == "archive-bytes" else original
    )
    (repo / "supply/archify.mjs").write_bytes(
        CONTENT + b"// drift\n" if defect == "artifact-bytes" else CONTENT
    )
    member = "archify/bin/absent.mjs" if defect == "missing" else MEMBER
    write_test_profile(
        repo,
        profile_id="example",
        proof={
            "gate_registry": "system/gates.toml",
            "source_contracts": [
                {
                    "kind": "upstream",
                    "input_refs": [reference],
                    "members": {"supply/archify.mjs": [reference, member]},
                    "integrity_gate": "integrity",
                }
            ],
        },
    )
    commit_fixture(repo, "declare a committed received archive")
    observer = importlib.import_module("ethos.adapters.gates.provenance.observation")
    if defect == "oversized":
        limits = vars(observer)["_ARCHIVE_LIMITS"]
        monkeypatch.setattr(observer, "_ARCHIVE_LIMITS", {**limits, "expanded_bytes": 1})
    report = observer.integrity_report(repo)
    if defect == "none":
        assert report["verdict"] == "pass", report
        integrity = report["source_integrity"]
        assert isinstance(integrity, dict)
        assert integrity["members"] == {
            "supply/archify.mjs": {"kind": "upstream", "input_ref": reference, "member": MEMBER}
        }
    else:
        assert report["verdict"] == "unknown", report
        assert report["required_gaps"] == ["source_integrity_unproven:supply/archify.mjs"]


@pytest.mark.parametrize(
    ("reference", "member", "valid"),
    [
        ("supply/archify.zip#sha256:" + "a" * 64, MEMBER, True),
        ("supply/archify.zip#sha256:" + "A" * 64, MEMBER, False),
        ("supply/archify.tar#sha256:" + "a" * 64, MEMBER, False),
        ("supply/archify.zip#sha512:" + "a" * 64, MEMBER, False),
        ("../archify.zip#sha256:" + "a" * 64, MEMBER, False),
        ("supply/archify.zip#sha256:" + "a" * 64, "archify/bin/", False),
    ],
)
def test_received_archive_reference_names_a_committed_zip_and_its_digest(
    reference: str, member: str, *, valid: bool
) -> None:
    """Only an exact repository ZIP with a lowercase SHA-256 and exact entry names is native."""
    declaration = {
        "kind": "upstream",
        "input_refs": [reference],
        "members": {"supply/archify.mjs": [reference, member]},
        "integrity_gate": "integrity",
    }
    if not valid:
        with pytest.raises(ValidationError):
            SourceContract.model_validate(declaration)
        return
    contract = SourceContract.model_validate(declaration)
    assert source_contract_paths((contract,), {}) == ("supply/archify.mjs", "supply/archify.zip")


def _archive(defect: str) -> bytes:
    if defect == "corrupt":
        return b"PK\x03\x04 not an archive"
    buffer = io.BytesIO()
    method = zipfile.ZIP_BZIP2 if defect == "bzip2" else zipfile.ZIP_DEFLATED
    with warnings.catch_warnings(), zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        warnings.simplefilter("ignore")
        archive.writestr("archify/README.md", b"# unselected entry\n")
        entry = zipfile.ZipInfo(MEMBER)
        if defect == "link":
            entry.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(entry, CONTENT, method)
        if defect == "duplicate":
            archive.writestr(MEMBER, CONTENT)
    data = bytearray(buffer.getvalue())
    if defect == "encrypted":
        # Set the general-purpose encryption bit in the entry's local and central headers.
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            local = archive.getinfo(MEMBER).header_offset
        data[local + 6] |= 1
        data[data.rfind(b"PK\x01\x02") + 8] |= 1
    return bytes(data)
