"""A reviewed retirement keeps its nodes in one content-addressed manifest its request binds."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

import ethos.adapters.mutation.lane_retirement.manifest as manifest_module
import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.adapters.mutation.lane_retirement.continuation import content_review_command
from ethos.adapters.mutation.lane_retirement.continuation import lane_status_command
from ethos.adapters.mutation.lane_retirement.manifest import manifest_store
from ethos.contracts.retirement import ReviewedManifest
from ethos.contracts.semantic import canonical_json_bytes
from tests.support.governed_repository import git
from tests.support.lane_scenarios import apply_retirement_receipt
from tests.support.lane_scenarios import derive_abandonment

_FILE = {"kind": "file", "identity": ["1", "2", "3", "4", "11", "6", "7", "1"], "sha256": "a" * 64}
_DIRECTORY = {"kind": "directory", "identity": ["2"] * 8}


def _request(receipt: Any) -> dict[str, Any]:
    return json.loads(Path(receipt["path"]).read_bytes())


def _reviewed(repo: Path, lane: Path) -> tuple[dict[str, Any], dict[str, Any], Path]:
    (lane / "scratch.txt").write_text("nontracked\n", encoding="utf-8")
    derived: dict[str, Any] = derive_abandonment(repo, review_content=True)
    assert derived["verdict"] == "pass", derived
    reference = _request(derived["receipt"])["reviewed_content"]["manifest"]
    return derived, reference, manifest_store(repo) / f"{reference['sha256']}.json"


def test_a_reviewed_request_binds_its_manifest_by_digest(divergent_lane):
    """The request keeps the manifest's digest, size and per-root totals; the file keeps nodes."""
    repo, lane = divergent_lane
    derived, reference, manifest = _reviewed(repo, lane)
    payload = manifest.read_bytes()
    entries = json.loads(payload)["entries"]

    assert "entries" not in _request(derived["receipt"])["reviewed_content"]
    assert hashlib.sha256(payload).hexdigest() == reference["sha256"]
    assert reference["size_bytes"] == len(payload)
    assert {".git", "abandoned.txt", "scratch.txt"} <= set(entries)
    assert reference["totals"]["scratch.txt"] == {
        "directories": 0,
        "files": 1,
        "symlinks": 0,
        "file_bytes": len("nontracked\n"),
    }
    assert reference["totals"][".git"]["files"] == 1
    assert derived["review_summary"] == {
        "entry_count": len(entries),
        "full_manifest": manifest.as_posix(),
    }


def test_a_terminal_retirement_releases_its_manifest(divergent_lane):
    """The receipt keeps the reference only, and the manifest goes once the lane is retired."""
    repo, lane = divergent_lane
    derived, reference, manifest = _reviewed(repo, lane)

    applied: dict[str, Any] = apply_retirement_receipt(repo, derived["receipt"])

    assert applied["state"] == "retired", applied
    assert not lane.exists()
    assert not manifest.exists()
    assert applied["manifest_release"] == {"path": manifest.as_posix(), "state": "deleted"}
    terminal = json.loads(Path(applied["terminal_receipt"]["path"]).read_bytes())
    assert terminal["request"]["reviewed_content"]["manifest"] == reference


def test_a_manifest_that_an_unreceipted_request_binds_survives_its_peer(divergent_lane):
    """Two reviews of one unchanged tree share a manifest; the first terminal keeps it."""
    repo, lane = divergent_lane
    first, reference, manifest = _reviewed(repo, lane)
    second: dict[str, Any] = derive_abandonment(
        repo, review_content=True, reason="discard the same experiment"
    )
    assert second["receipt"]["path"] != first["receipt"]["path"]
    assert _request(second["receipt"])["reviewed_content"]["manifest"] == reference

    applied: dict[str, Any] = apply_retirement_receipt(repo, first["receipt"])

    assert applied["state"] == "retired", applied
    assert applied["manifest_release"] == {"path": manifest.as_posix(), "state": "kept"}
    assert manifest.exists()


@pytest.mark.parametrize("damage", ["missing", "mismatch"])
def test_a_lost_manifest_refuses_removal_and_selects_a_fresh_review(divergent_lane, damage):
    """Nothing is removed on a guess; the continuation is the review that content drift selects."""
    repo, lane = divergent_lane
    derived, _reference, manifest = _reviewed(repo, lane)
    if damage == "missing":
        manifest.unlink()
    else:
        manifest.write_bytes(manifest.read_bytes().replace(b"scratch.txt", b"scratch.tx_"))

    applied: dict[str, Any] = apply_retirement_receipt(repo, derived["receipt"])

    assert applied["required_gaps"] == [f"lane_retirement_manifest_{damage}"], applied
    assert (lane / "scratch.txt").read_text(encoding="utf-8") == "nontracked\n"
    assert applied["next_action"] == content_review_command(
        Path(_request(derived["receipt"])["control_root"]), "work/abandon"
    )


def _inline(
    repo: Path, derived: dict[str, Any], manifest: Path
) -> tuple[dict[str, Any], Path, str]:
    """Write the request as one written before compaction, with its nodes inline."""
    request: dict[str, Any] = _request(derived["receipt"])
    request["reviewed_content"].pop("manifest")
    request["reviewed_content"]["entries"] = json.loads(manifest.read_bytes())["entries"]
    payload = canonical_json_bytes(request)
    digest = hashlib.sha256(payload).hexdigest()
    path = operation.operation_store(repo) / f"{digest}.json"
    path.write_bytes(payload)
    return request, path, digest


def _recover(repo: Path, path: Path, digest: str, *, authorized: bool = True) -> dict[str, Any]:
    return operation.execute_retirement_operation(
        root=repo,
        receipt_path=path.as_posix(),
        receipt_sha256=f"sha256:{digest}",
        apply=True,
        authorized=authorized,
    )


def test_an_inline_request_continues_through_a_fresh_review(divergent_lane):
    """A request written before compaction no longer applies, and recovery names a new review."""
    repo, lane = divergent_lane
    derived, reference, manifest = _reviewed(repo, lane)
    request, path, digest = _inline(repo, derived, manifest)

    recovered = _recover(repo, path, digest)

    assert recovered["required_gaps"] == ["lane_retirement_receipt_invalid"], recovered
    assert recovered["next_action"] == content_review_command(
        Path(request["control_root"]), "work/abandon"
    )
    assert (lane / "scratch.txt").exists()
    assert reference["sha256"] == manifest.stem


@pytest.mark.parametrize(
    ("path", "node"),
    [
        ("../escape.py", _FILE),
        ("/absolute.py", _FILE),
        ("./alias.py", _FILE),
        ("src//alias.py", _FILE),
        ("missing/file.py", _FILE),
        ("src/.git", _FILE),
        ("src", {"kind": "symlink", "identity": ["3"] * 8, "target": "../external"}),
    ],
)
def test_a_manifest_holds_one_exact_relative_tree(path, node):
    """Escaping, aliased, orphaned, nested-marker and linked parents are not a reviewed tree."""
    entries = {".git": _FILE, "src": _DIRECTORY, "src/module.py": _FILE}
    if path == "src":
        entries["src"] = node
    else:
        entries[path] = entries.pop("src/module.py")

    with pytest.raises(ValueError, match="retirement_content_tree_invalid"):
        ReviewedManifest.model_validate({"entries": entries})


def test_manifest_totals_count_each_top_level_name():
    """Totals count directories, files and symlinks and sum file sizes under each first name."""
    link = {"kind": "symlink", "identity": ["4"] * 8, "target": "module.py"}
    manifest = ReviewedManifest.model_validate(
        {"entries": {".git": _FILE, "src": _DIRECTORY, "src/module.py": _FILE, "src/link": link}}
    )

    assert manifest.totals() == {
        ".git": {"directories": 0, "files": 1, "symlinks": 0, "file_bytes": 11},
        "src": {"directories": 1, "files": 1, "symlinks": 1, "file_bytes": 11},
    }


def test_an_inline_request_on_a_moved_branch_continues_through_status(divergent_lane):
    """When the request's carriers drifted, the continuation is the lane status read."""
    repo, lane = divergent_lane
    derived, _reference, manifest = _reviewed(repo, lane)
    request, path, digest = _inline(repo, derived, manifest)
    git(lane, "commit", "--allow-empty", "-m", "move the lane after its review")

    recovered = _recover(repo, path, digest)

    assert recovered["next_action"] == lane_status_command(Path(request["control_root"]))


def test_a_request_that_is_not_inline_has_no_inline_continuation(divergent_lane, tmp_path):
    """An unreadable receipt, or a current request refused for its authority, names nothing."""
    repo, lane = divergent_lane
    derived, _reference, _manifest = _reviewed(repo, lane)
    receipt = derived["receipt"]
    current = operation.execute_retirement_operation(
        root=repo,
        receipt_path=receipt["path"],
        receipt_sha256=receipt["sha256"],
        apply=True,
        authorized=False,
    )
    missing = _recover(repo, tmp_path / f"{'e' * 64}.json", "e" * 64)

    assert current["required_gaps"] == ["authorization_required"], current
    assert current["next_action"] == ""
    assert missing["next_action"] == ""
    assert (lane / "scratch.txt").exists()


def test_a_failed_manifest_release_is_reported_not_raised(divergent_lane, monkeypatch):
    """The retirement is already terminal, so a release failure reports and keeps the result."""
    repo, lane = divergent_lane
    derived, _reference, manifest = _reviewed(repo, lane)

    def refuse(*_args: object) -> bool:
        message = "release scan refused"
        raise OSError(message)

    monkeypatch.setattr(manifest_module, "_bound_elsewhere", refuse)
    applied: dict[str, Any] = apply_retirement_receipt(repo, derived["receipt"])

    assert applied["state"] == "retired", applied
    assert applied["manifest_release"] == {
        "path": manifest.as_posix(),
        "state": "failed",
        "reason": "release scan refused",
    }
    assert manifest.exists()
