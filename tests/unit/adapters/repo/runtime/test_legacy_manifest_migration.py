"""Legacy runtime migration remains observation-only and exact."""

from __future__ import annotations

import hashlib
import json
import platform
from typing import TYPE_CHECKING

import pytest

import ethos.adapters.repo.hook.binding as hook_binding
from ethos.adapters.repo.runtime.selection import legacy_runtime_migration_source

if TYPE_CHECKING:
    from pathlib import Path


def _legacy_manifest(
    common: Path,
    *,
    source: tuple[str, str] = ("a" * 40, "b" * 40),
) -> Path:
    digest = "a" * 64
    runtime = common / "ethos/runtime" / digest
    contents = {
        "venv/bin/python": b"incumbent-python",
        "venv/bin/ethos": b"incumbent-entrypoint",
    }
    for relative, content in contents.items():
        target = runtime / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    payload = {
        "schema_version": 2,
        "runtime_digest": digest,
        "wheel_sha256": "c" * 64,
        "python_abi": "cpython-test",
        "platform": platform.system().lower(),
        "source_commit": source[0],
        "source_tree": source[1],
        "runtime_files": {
            relative: hashlib.sha256(content).hexdigest() for relative, content in contents.items()
        },
    }
    manifest = runtime / "manifest.json"
    manifest.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (runtime.parent / "CURRENT").write_text(f"{digest}\n", encoding="ascii")
    return manifest


def test_binding_uses_exact_legacy_source_only_as_migration_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An exact legacy manifest remains read-only migration evidence."""
    repo = tmp_path / "repo"
    repo.mkdir()
    common = tmp_path / "common"
    source = ("a" * 40, "b" * 40)
    _legacy_manifest(common, source=source)
    generation = common / "ethos/hooks" / ("b" * 64)
    generation.mkdir(parents=True)
    expected = [source]
    monkeypatch.setattr(hook_binding, "git_common_dir", lambda _repo: common.as_posix())
    monkeypatch.setattr(hook_binding, "_configured_hooks_path", lambda _repo: generation)
    monkeypatch.setattr(hook_binding, "_launcher_gap", lambda *_args: "")
    monkeypatch.setattr(hook_binding, "accepted_version_migration_pending", lambda _repo: True)
    monkeypatch.setattr(
        hook_binding,
        "expected_runtime_build",
        lambda _repo: (_ for _ in ()).throw(ValueError("accepted VERSION unavailable")),
    )
    monkeypatch.setattr(hook_binding, "expected_runtime_source", lambda _repo: expected[0])

    observed = hook_binding.hook_runtime_binding(repo)

    assert observed["required_gaps"] == [
        "write_admission_not_armed:runtime_schema_migration_required"
    ]
    assert observed["expected_source_commit"] == source[0]
    assert observed["state"] == "stale"
    assert observed["target_current"] is False

    expected[0] = ("c" * 40, "d" * 40)
    stale = hook_binding.hook_runtime_binding(repo)

    assert stale["required_gaps"] == ["write_admission_not_armed:runtime_build_stale"]
    assert stale["expected_source_commit"] == "c" * 40


@pytest.mark.parametrize(
    ("field", "value"),
    [("schema_version", 999), ("unexpected", "field")],
)
def test_legacy_migration_rejects_non_exact_schema(
    tmp_path: Path, field: str, value: object
) -> None:
    common = tmp_path / "common"
    manifest = _legacy_manifest(common)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload[field] = value
    manifest.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    assert legacy_runtime_migration_source(common) is None
