from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import ethos.adapters.repo.source_budget.carriers as adapter
from ethos.adapters.repo.source_budget.carriers import PresentWorktreePathsLoad
from ethos.adapters.repo.source_budget.carriers import classify_carriers
from ethos.adapters.repo.source_budget.carriers import load_carrier_manifest
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

ROOT = Path(__file__).resolve().parents[5]
_D: dict[str, Any] = json.loads(
    (Path(__file__).parents[4] / "fixtures/source-budget-v2/compression-cases.json").read_text()
)["adapter"]
_TRACKED = b"H 100644 " + (b"a" * 40) + b" 0\tx.py\0"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init(root: Path) -> Path:
    root.mkdir()
    _git(root, "init", "--quiet")
    return root


def _observe(monkeypatch: pytest.MonkeyPatch, output: bytes, code: int = 0) -> None:
    monkeypatch.setattr(
        adapter.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, code, stdout=output),
    )


def _failure(root: Path, gap: str) -> None:
    load = adapter.load_present_worktree_paths(root)
    assert (load.paths, load.required_gaps) == (None, (gap,))


def _output(text: str) -> bytes:
    return text.replace("{a40}", "a" * 40).replace("{g40}", "g" * 40).encode("latin1")


def test_policy_loader_contract(tmp_path: Path) -> None:
    specs = (
        (
            load_carrier_manifest,
            "manifest",
            "source-budget-carriers.toml",
            "source_budget_carrier_manifest",
        ),
        (
            load_metric_contracts,
            "contracts",
            "source-budget-metrics.toml",
            "source_budget_metric_contracts",
        ),
    )

    def check(suffix: str) -> None:
        for loader, field, _name, prefix in specs:
            loaded = loader(tmp_path)
            assert getattr(loaded, field) is None
            assert loaded.required_gaps == (f"{prefix}_{suffix}",)

    check("missing")
    policy = tmp_path / "system/policies"
    policy.mkdir(parents=True)
    for _loader, _field, name, _prefix in specs:
        (policy / name).write_text("[[broken")
    check("invalid_toml")
    paths = tuple(policy / item[2] for item in specs)
    for path in paths:
        path.unlink()
        path.mkdir()
    check("unreadable")
    for path in paths:
        path.rmdir()
    paths[0].write_text(
        'schema = "ethos-source-budget-carriers-v2"\ncontract_version = 2\ncarriers = []\n'
    )
    paths[1].write_text(
        'schema = "ethos-source-budget-metrics-v2"\ncontract_version = 2\nprofiles = []\ncontracts = []\n'
    )
    check("invalid")


def test_manifest_inventory_contract() -> None:
    carrier_load = load_carrier_manifest(ROOT)
    metric_load = load_metric_contracts(ROOT)
    path_load = adapter.load_present_worktree_paths(ROOT)
    assert (carrier_load.required_gaps, metric_load.required_gaps, path_load.required_gaps) == (
        (),
        (),
        (),
    )
    assert carrier_load.manifest is not None
    assert metric_load.contracts is not None
    assert path_load.paths
    forward = classify_carriers(path_load.paths, carrier_load.manifest)
    reverse = classify_carriers(reversed(path_load.paths), carrier_load.manifest)
    assert forward.required_gaps == ()
    assert (forward.manifest_digest, forward.inventory_digest, forward.matches) == (
        reverse.manifest_digest,
        reverse.inventory_digest,
        reverse.matches,
    )
    measured = tuple(
        match.identity
        for match in forward.matches
        if match.state == "classified" and match.identity is not None
    )
    assert measured
    for identity in measured:
        assert resolve_metric_contracts(identity, metric_load.contracts)
    rule = next(
        item
        for item in carrier_load.manifest.carriers
        if item.disposition == "measure" and ".py" in item.extensions
    )
    overlap = rule.model_copy(
        update={"carrier_id": f"{rule.carrier_id}-overlap", "include": ("packages/**",)}
    )
    manifest = carrier_load.manifest.model_copy(
        update={"carriers": (*carrier_load.manifest.carriers, overlap)}
    )
    inventory = classify_carriers(("packages/ethos/src/ethos/__init__.py",), manifest)
    assert inventory.matches[0].state == "ambiguous"
    assert overlap.carrier_id in inventory.matches[0].matched_carrier_ids
    assert inventory.required_gaps


def test_mocked_inventory_contract(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for failure, gap in _D["git_failures"]:
        if failure == "returncode":
            _observe(monkeypatch, b"", 128)
        else:
            monkeypatch.setattr(
                adapter.subprocess,
                "run",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()),
            )
        _failure(tmp_path, gap)
    for name in ("tracked.py", "untracked.py"):
        (tmp_path / name).write_text(name)
    calls: list[list[str]] = []
    tagged = b"? untracked.py\0" + b"H 100644 " + (b"a" * 40) + b" 0\ttracked.py\0"

    def observe(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=tagged)

    monkeypatch.setattr(adapter.subprocess, "run", observe)
    load = adapter.load_present_worktree_paths(tmp_path)
    assert (load.paths, load.required_gaps) == (("tracked.py", "untracked.py"), ())
    assert calls == [
        ["git", "ls-files", "-z", "-t", "--stage", "--cached", "--others", "--exclude-standard"]
    ]
    (tmp_path / "x.py").write_text("tracked")
    for text, gap in _D["git_outputs"]:
        _observe(monkeypatch, _output(text))
        _failure(tmp_path, gap)
    for path_kind, paths, gap_kind, gaps, message in _D["envelopes"]:
        path_value = (
            None if path_kind == "none" else list(paths) if path_kind == "list" else tuple(paths)
        )
        gap_value = list(gaps) if gap_kind == "list" else tuple(gaps)
        with pytest.raises(ValueError, match=message):
            PresentWorktreePathsLoad(path_value, gap_value)
    _observe(monkeypatch, b"")
    _failure(tmp_path, "source_budget_inventory_empty")
    original_kind = adapter._worktree_object_kind
    for record, kind, gap in _D["object_kinds"]:
        _observe(monkeypatch, b"? x.py\0" if record == "untracked" else _TRACKED)
        monkeypatch.setattr(adapter, "_worktree_object_kind", lambda *_args, kind=kind: kind)
        _failure(tmp_path, gap)
    monkeypatch.setattr(adapter, "_worktree_object_kind", original_kind)
    _observe(monkeypatch, b"? missing/x.py\0")
    _failure(tmp_path, "source_budget_inventory_empty")
    (tmp_path / "parent").write_text("not a directory")
    _observe(monkeypatch, b"? parent/x.py\0")
    _failure(
        tmp_path,
        "source_budget_inventory_object_unsupported:untracked_non_directory_ancestor:parent/x.py",
    )
    original_lstat = Path.lstat
    for mode, gap in _D["object_modes"]:
        _observe(monkeypatch, b"? x.py\0")
        monkeypatch.setattr(
            Path, "lstat", lambda _path, mode=mode: SimpleNamespace(st_mode=getattr(stat, mode))
        )
        _failure(tmp_path, gap)
    monkeypatch.setattr(Path, "lstat", lambda _path: (_ for _ in ()).throw(OSError()))
    _failure(tmp_path, "source_budget_inventory_object_unreadable:x.py")
    monkeypatch.setattr(Path, "lstat", original_lstat)


def test_real_inventory_contract(tmp_path: Path) -> None:
    symlink = _init(tmp_path / "symlink")
    (symlink / "target.py").write_text("target")
    (symlink / "link.py").symlink_to("target.py")
    _git(symlink, "add", "target.py", "link.py")
    _failure(symlink, "source_budget_inventory_object_unsupported:symlink:link.py")

    ancestor = _init(tmp_path / "ancestor")
    (ancestor / ".gitignore").write_text("dir\n")
    directory = ancestor / "dir"
    directory.mkdir()
    tracked = directory / "file.py"
    tracked.write_text("tracked")
    _git(ancestor, "add", ".gitignore")
    _git(ancestor, "add", "-f", "dir/file.py")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "file.py").write_text("outside")
    tracked.unlink()
    directory.rmdir()
    directory.symlink_to(outside, target_is_directory=True)
    load = adapter.load_present_worktree_paths(ancestor)
    assert load.paths is None
    assert any("symlink_ancestor:dir/file.py" in gap for gap in load.required_gaps)

    deleted = _init(tmp_path / "deleted")
    (deleted / "present.py").write_text("present")
    removed = deleted / "deleted.py"
    removed.write_text("deleted")
    _git(deleted, "add", "present.py", "deleted.py")
    removed.unlink()
    load = adapter.load_present_worktree_paths(deleted)
    assert (load.paths, load.required_gaps) == (("present.py",), ())

    gitlink = _init(tmp_path / "gitlink")
    _git(
        gitlink,
        "-c",
        "user.name=ETHOS Test",
        "-c",
        "user.email=ethos-test@example.invalid",
        "commit",
        "--allow-empty",
        "--message=fixture",
    )
    head = _git(gitlink, "rev-parse", "HEAD").stdout.decode().strip()
    _git(gitlink, "update-index", "--add", "--cacheinfo", f"160000,{head},vendor/sub")
    _failure(gitlink, "source_budget_inventory_object_unsupported:gitlink:vendor/sub")
