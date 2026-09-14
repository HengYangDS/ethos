"""Retirement receipts bind exact repository, reviewed content and request identity."""

from __future__ import annotations

import hashlib
import json
import pathlib
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.mutation.lane_retirement.operation as operation
from ethos.contracts.retirement import RetirementOperation
from tests.support.lane_scenarios import retirement_request

if TYPE_CHECKING:
    from pathlib import Path


def test_empty_review_extension_preserves_historical_receipt_identity(tmp_path, monkeypatch):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    historical = retirement_request(tmp_path).model_dump(mode="json")
    historical.pop("reviewed_content", None)
    payload = json.dumps(historical, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(payload).hexdigest()
    path = operation.operation_store(tmp_path) / f"{digest}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(payload)

    restored = operation.load_operation(tmp_path, str(path), digest)

    assert restored.digest() == digest
    assert restored.model_dump(mode="json") == historical
    assert operation.persist_operation(tmp_path, restored)["path"] == str(path)
    assert path.read_bytes() == payload


def test_reviewed_receipt_uses_the_same_identity_as_its_request(tmp_path, monkeypatch):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    entries = content["entries"]
    entries["\ue000"] = entries["src/module.py"]
    entries["\U00010000"] = entries["src/module.py"]
    request = RetirementOperation.model_validate(payload)

    receipt = operation.persist_operation(tmp_path, request)
    path, digest = receipt["path"], receipt["sha256"]
    assert isinstance(path, str)
    assert isinstance(digest, str)
    raw = pathlib.Path(path).read_bytes()

    assert raw.index('"\U00010000"'.encode()) < raw.index('"\ue000"'.encode())
    assert digest == f"sha256:{request.digest()}"
    assert pathlib.Path(path).stem == request.digest()
    assert operation.load_operation(tmp_path, path, digest) == request


def _reviewed_request(tmp_path: Path) -> dict[str, object]:
    payload = retirement_request(tmp_path).model_dump(mode="json")
    file = {"kind": "file", "identity": ["1"] * 8, "sha256": "a" * 64}
    directory = {"kind": "directory", "identity": ["2"] * 8}
    payload["reviewed_content"] = {
        "root": directory,
        "index_path": str(tmp_path / ".git/worktrees/lane/index"),
        "index": file,
        "entries": {".git": file, "src": directory, "src/module.py": file},
    }
    return json.loads(json.dumps(payload))


@pytest.mark.parametrize(
    "updates",
    [
        {"mode": "landed"},
        {"worktree_initial": "unbound"},
        {"reviewed_content": {}},
        {"lease_state": "valid"},
        {"lease": {"generation": 1}},
        {"git_plan": {"digest": "a" * 64}},
        {"effects": ["remove_worktree", "delete_ref"]},
    ],
)
def test_detached_receipt_rejects_invented_resources(tmp_path, updates):
    payload = _reviewed_request(tmp_path) | {
        "branch": "",
        "lease_state": "missing",
        "lease": {},
        "git_plan": {},
        "effects": ["remove_worktree"],
    }
    with pytest.raises(
        ValueError, match=r"retirement_(?:detached_resources|operation_effects)_invalid"
    ):
        RetirementOperation.model_validate(payload | updates)


@pytest.mark.parametrize(
    ("coordinate", "replacement"),
    [
        (("root", "kind"), "file"),
        (("index", "kind"), "symlink"),
        (("index_path",), "relative/index"),
        (("entries",), {}),
        (("entries", "src"), {"kind": "socket", "identity": ["1"] * 8}),
        (("entries", "src/module.py", "sha256"), "invalid"),
        (("entries", "src/module.py", "identity"), [1] * 8),
        (("entries", "src/module.py", "identity"), ["1"] * 7),
        (("entries", "src/module.py", "identity"), ["01"] * 8),
        (("entries", "src/module.py", "target"), "unexpected"),
    ],
)
def test_receipt_reader_rejects_malformed_reviewed_inventory(
    tmp_path, monkeypatch, coordinate, replacement
):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    for key in coordinate[:-1]:
        content = content[key]
    content[coordinate[-1]] = replacement
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    digest = hashlib.sha256(raw).hexdigest()
    path = operation.operation_store(tmp_path) / f"{digest}.json"
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)

    with pytest.raises(ValueError, match="lane_retirement_receipt_invalid"):
        operation.load_operation(tmp_path, str(path), digest)
    assert path.read_bytes() == raw


@pytest.mark.parametrize(
    "path",
    ["../escape.py", "/absolute.py", "./alias.py", "src//alias.py", "missing/file.py", "src/.git"],
)
def test_reviewed_inventory_requires_exact_relative_tree(tmp_path, path):
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    content["entries"][path] = content["entries"].pop("src/module.py")

    with pytest.raises(ValueError, match="retirement_content_tree_invalid"):
        RetirementOperation.model_validate(payload)


def test_reviewed_inventory_cannot_traverse_a_link(tmp_path):
    payload = _reviewed_request(tmp_path)
    content = payload["reviewed_content"]
    assert isinstance(content, dict)
    content["entries"]["src"] = {"kind": "symlink", "identity": ["3"] * 8, "target": "../external"}

    with pytest.raises(ValueError, match="retirement_content_tree_invalid"):
        RetirementOperation.model_validate(payload)


@pytest.mark.parametrize(
    ("damage", "gap"),
    [
        ("repository", "path_invalid"),
        ("digest", "path_invalid"),
        ("missing", "missing"),
        ("tamper", "sha256_mismatch"),
        ("json", "invalid"),
        ("schema", "invalid"),
    ],
)
def test_operation_receipt_is_repository_scoped_and_tamper_evident(
    tmp_path, monkeypatch, damage, gap
):
    monkeypatch.setattr(operation, "local_state_root", lambda root: root / "state")
    request = retirement_request(tmp_path)
    receipt = operation.persist_operation(tmp_path, request)
    path_value, digest = receipt["path"], receipt["sha256"]
    assert isinstance(path_value, str)
    assert isinstance(digest, str)
    path = pathlib.Path(path_value)
    assert operation.load_operation(tmp_path, str(path), digest) == request
    assert operation.persist_operation(tmp_path, request) == receipt
    if damage == "repository":
        tmp_path = tmp_path / "other"
    elif damage == "digest":
        digest = "invalid"
    elif damage == "missing":
        path.unlink()
    elif damage == "tamper":
        path.write_bytes(b"tampered")
    else:
        content = b"{" if damage == "json" else b"{}"
        digest = hashlib.sha256(content).hexdigest()
        path = path.with_name(f"{digest}.json")
        path.write_bytes(content)
    before = path.read_bytes() if path.exists() else None
    with pytest.raises(ValueError, match=f"lane_retirement_receipt_{gap}"):
        operation.load_operation(tmp_path, str(path), digest)
    assert (path.read_bytes() if path.exists() else None) == before
