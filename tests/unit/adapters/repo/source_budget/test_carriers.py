from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import ethos.adapters.repo.source_budget.carriers as carrier_adapter
from ethos.adapters.repo.source_budget.carriers import classify_carriers
from ethos.adapters.repo.source_budget.carriers import load_carrier_manifest
from ethos.adapters.repo.source_budget.carriers import load_metric_contracts
from ethos_core.contracts.source_budget.metrics import resolve_metric_contracts

ROOT = Path(__file__).resolve().parents[5]


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def test_carrier_and_metric_loaders_fail_closed_on_missing_or_invalid_toml(
    tmp_path: Path,
) -> None:
    carrier_load = load_carrier_manifest(tmp_path)
    assert carrier_load.manifest is None
    assert carrier_load.required_gaps == ("source_budget_carrier_manifest_missing",)

    metric_load = load_metric_contracts(tmp_path)
    assert metric_load.contracts is None
    assert metric_load.required_gaps == ("source_budget_metric_contracts_missing",)

    policy_root = tmp_path / "system" / "policies"
    policy_root.mkdir(parents=True)
    (policy_root / "source-budget-carriers.toml").write_text("[[broken", encoding="utf-8")
    (policy_root / "source-budget-metrics.toml").write_text("[[broken", encoding="utf-8")

    carrier_load = load_carrier_manifest(tmp_path)
    assert carrier_load.manifest is None
    assert carrier_load.required_gaps == ("source_budget_carrier_manifest_invalid_toml",)

    metric_load = load_metric_contracts(tmp_path)
    assert metric_load.contracts is None
    assert metric_load.required_gaps == ("source_budget_metric_contracts_invalid_toml",)


def test_current_manifest_classifies_present_inventory_deterministically() -> None:
    carrier_load = load_carrier_manifest(ROOT)
    metric_load = load_metric_contracts(ROOT)

    assert carrier_load.required_gaps == ()
    assert carrier_load.manifest is not None
    assert metric_load.required_gaps == ()
    assert metric_load.contracts is not None

    path_load = carrier_adapter.load_present_worktree_paths(ROOT)
    assert path_load.required_gaps == ()
    assert path_load.paths
    paths = path_load.paths

    forward = classify_carriers(paths, carrier_load.manifest)
    reverse = classify_carriers(reversed(paths), carrier_load.manifest)

    assert forward.required_gaps == ()
    assert forward.manifest_digest == reverse.manifest_digest
    assert forward.inventory_digest == reverse.inventory_digest
    assert forward.matches == reverse.matches

    measured = tuple(
        match.identity
        for match in forward.matches
        if match.state == "classified" and match.identity is not None
    )
    assert measured
    for identity in measured:
        assert resolve_metric_contracts(identity, metric_load.contracts)


def test_inventory_preserves_ambiguous_matches_instead_of_first_match() -> None:
    carrier_load = load_carrier_manifest(ROOT)
    assert carrier_load.manifest is not None

    python_rule = next(
        item
        for item in carrier_load.manifest.carriers
        if item.disposition == "measure" and ".py" in item.extensions
    )
    overlap = python_rule.model_copy(
        update={
            "carrier_id": f"{python_rule.carrier_id}-overlap",
            "include": ("packages/**",),
            "exclude": (),
        }
    )
    manifest = carrier_load.manifest.model_copy(
        update={"carriers": (*carrier_load.manifest.carriers, overlap)}
    )

    inventory = classify_carriers(("packages/ethos/src/ethos/__init__.py",), manifest)

    assert inventory.matches[0].state == "ambiguous"
    assert overlap.carrier_id in inventory.matches[0].matched_carrier_ids
    assert inventory.required_gaps


def test_typed_inventory_loader_fails_closed_on_git_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        carrier_adapter.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 128, stdout=b""),
    )

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert load.required_gaps == ("source_budget_inventory_git_failed",)


def test_typed_inventory_loader_fails_closed_on_git_os_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def fail(*_args, **_kwargs):
        raise OSError

    monkeypatch.setattr(carrier_adapter.subprocess, "run", fail)

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert load.required_gaps == ("source_budget_inventory_git_unavailable",)


def test_typed_inventory_loader_uses_one_tagged_git_observation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    (tmp_path / "tracked.py").write_text("tracked\n", encoding="utf-8")
    (tmp_path / "untracked.py").write_text("untracked\n", encoding="utf-8")
    calls: list[list[str]] = []
    output = b"? untracked.py\0" + b"H 100644 " + (b"a" * 40) + b" 0\ttracked.py\0"

    def observe(args: list[str], **_kwargs) -> subprocess.CompletedProcess[bytes]:
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, stdout=output)

    monkeypatch.setattr(carrier_adapter.subprocess, "run", observe)

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths == ("tracked.py", "untracked.py")
    assert load.required_gaps == ()
    assert calls == [
        [
            "git",
            "ls-files",
            "-z",
            "-t",
            "--stage",
            "--cached",
            "--others",
            "--exclude-standard",
        ]
    ]


@pytest.mark.parametrize(
    "output",
    [
        b"? tracked.py",
        b"? tracked.py\0\0",
    ],
)
def test_typed_inventory_loader_rejects_invalid_nul_framing(
    tmp_path: Path,
    monkeypatch,
    output: bytes,
) -> None:
    (tmp_path / "tracked.py").write_text("tracked\n", encoding="utf-8")
    monkeypatch.setattr(
        carrier_adapter.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, stdout=output),
    )

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert load.required_gaps == ("source_budget_inventory_git_output_invalid",)


@pytest.mark.parametrize(
    ("tag", "stage", "expected_gap"),
    [
        (b"M", b"0", "source_budget_inventory_git_output_invalid"),
        (b"H", b"1", "source_budget_inventory_git_output_invalid"),
        (b"S", b"2", "source_budget_inventory_git_output_invalid"),
        (b"X", b"0", "source_budget_inventory_git_output_invalid"),
        (b"H", b"4", "source_budget_inventory_git_output_invalid"),
        (b"M", b"1", "source_budget_inventory_index_unmerged:x.py"),
    ],
)
def test_typed_inventory_loader_validates_tag_stage_pairs(
    tmp_path: Path,
    monkeypatch,
    tag: bytes,
    stage: bytes,
    expected_gap: str,
) -> None:
    (tmp_path / "x.py").write_text("tracked\n", encoding="utf-8")
    output = tag + b" 100644 " + (b"a" * 40) + b" " + stage + b"\tx.py\0"
    monkeypatch.setattr(
        carrier_adapter.subprocess,
        "run",
        lambda args, **_kwargs: subprocess.CompletedProcess(args, 0, stdout=output),
    )

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert load.required_gaps == (expected_gap,)


def test_typed_inventory_envelope_rejects_empty_clean_paths() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        carrier_adapter.PresentWorktreePathsLoad((), ())


def test_typed_inventory_loader_rejects_tracked_symlinks(tmp_path: Path) -> None:
    _git(tmp_path, "init", "--quiet")
    (tmp_path / "target.py").write_text("print('target')\n", encoding="utf-8")
    (tmp_path / "link.py").symlink_to("target.py")
    _git(tmp_path, "add", "target.py", "link.py")

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert load.required_gaps == ("source_budget_inventory_object_unsupported:symlink:link.py",)


def test_typed_inventory_loader_rejects_symlinked_ancestors(tmp_path: Path) -> None:
    _git(tmp_path, "init", "--quiet")
    (tmp_path / ".gitignore").write_text("dir\n", encoding="utf-8")
    tracked_dir = tmp_path / "dir"
    tracked_dir.mkdir()
    tracked = tracked_dir / "file.py"
    tracked.write_text("print('tracked')\n", encoding="utf-8")
    _git(tmp_path, "add", ".gitignore")
    _git(tmp_path, "add", "-f", "dir/file.py")

    outside = tmp_path.parent / f"{tmp_path.name}-outside"
    outside.mkdir()
    (outside / "file.py").write_text("print('outside')\n", encoding="utf-8")
    tracked.unlink()
    tracked_dir.rmdir()
    tracked_dir.symlink_to(outside, target_is_directory=True)

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert any("symlink_ancestor:dir/file.py" in gap for gap in load.required_gaps)


def test_typed_inventory_loader_omits_unstaged_deleted_regular_paths(
    tmp_path: Path,
) -> None:
    _git(tmp_path, "init", "--quiet")
    (tmp_path / "present.py").write_text("present\n", encoding="utf-8")
    deleted = tmp_path / "deleted.py"
    deleted.write_text("deleted\n", encoding="utf-8")
    _git(tmp_path, "add", "present.py", "deleted.py")
    deleted.unlink()

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths == ("present.py",)
    assert load.required_gaps == ()


def test_typed_inventory_loader_rejects_tracked_gitlinks(tmp_path: Path) -> None:
    _git(tmp_path, "init", "--quiet")
    _git(
        tmp_path,
        "-c",
        "user.name=ETHOS Test",
        "-c",
        "user.email=ethos-test@example.invalid",
        "commit",
        "--allow-empty",
        "--message=fixture",
    )
    head = _git(tmp_path, "rev-parse", "HEAD").stdout.decode("ascii").strip()
    _git(tmp_path, "update-index", "--add", "--cacheinfo", f"160000,{head},vendor/sub")

    load = carrier_adapter.load_present_worktree_paths(tmp_path)

    assert load.paths is None
    assert load.required_gaps == ("source_budget_inventory_object_unsupported:gitlink:vendor/sub",)
