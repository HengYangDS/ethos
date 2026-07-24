from __future__ import annotations

import hashlib
import json
import os
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import ethos.adapters.repo.source_budget.artifacts as artifacts
import tools.ci.source_budget_replay as replay
from ethos.adapters.config import source_budget_taxonomy_from_bytes
from ethos.adapters.repo.source_budget.snapshots import read_snapshot_blobs
from ethos.adapters.repo.source_budget.snapshots import tree_snapshot
from ethos.domain.source_budget.core import source_budget_metrics_from_bytes
from ethos.domain.source_budget.core import source_budget_taxonomy_digest
from ethos_core.contracts.source_budget.measurements import MeasurementSnapshotLoad

ROOT = Path(__file__).resolve().parents[4]
BASELINE = "2dab77f169eceb2d45f917358c2a7487e7ac8db6"
TAXONOMY_PATH = ".config/checks/format/selection.toml"
ARTIFACT_ROOT = "build/evidence/quality/source-budget-v2/replay"


def _artifact_payload(label: str) -> dict[str, object]:
    payload: dict[str, object] = {"schema": "test", "entries": [{"entry_id": label}]}
    payload["digest"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return payload


def _taxonomy(commit: str):
    snapshot = tree_snapshot(ROOT, commit).snapshot
    assert snapshot is not None
    load = read_snapshot_blobs(ROOT, snapshot, (TAXONOMY_PATH,))
    assert load.snapshot is not None
    return source_budget_taxonomy_from_bytes(load.snapshot.contents[0][1])


def test_exact_baseline_replay_binds_historical_and_live_observer_profiles() -> None:
    subject = tree_snapshot(ROOT, BASELINE).snapshot
    assert subject is not None
    blobs = read_snapshot_blobs(
        ROOT, subject, tuple(entry.relative_path for entry in subject.entries)
    ).snapshot
    assert blobs is not None

    historical = _taxonomy("604934c7afe244caf5b671423f108823a7753a98")
    live = _taxonomy("fe94c0268d060742e808770d4d65d554709af0dd")
    historical_metrics, historical_inventory = source_budget_metrics_from_bytes(
        blobs.contents, historical
    )
    live_metrics, live_inventory = source_budget_metrics_from_bytes(blobs.contents, live)

    assert source_budget_taxonomy_digest(historical) == (
        "76ebd7491393d9083b60763a7a72c3f4e2904bfe2b9b935bdc181e0e0cc08e8a"
    )
    assert historical_inventory["file_count"] == 933
    assert historical_inventory["digest"] == (
        "f8e85ace7648b60592fbe6e678f78169afa98c6289b0e8bb7d7fbc3961fa1c8d"
    )
    assert historical_metrics["global_total"] == 105060
    assert historical_metrics["jinja"] == 671

    assert source_budget_taxonomy_digest(live) == (
        "5fbc0ff6e25f625463b7020728bbed4e1f30e21e1f081b7af897f7d234037356"
    )
    assert live_inventory["file_count"] == 888
    assert live_inventory["digest"] == (
        "d48fca7255274216d029c600b98972f00bd367b91979441b4d6512a857fb7a5c"
    )
    assert live_metrics["global_total"] == 104389
    assert "jinja" not in live_metrics


def test_history_config_binds_subject_observer_and_declaration_independently() -> None:
    history = replay.load_history_config(ROOT)
    historical = history.entries["v1-continuation-20260719"]
    live = history.entries["v1-live-at-task4-start"]

    assert history.declaration.commit_sha == "540e06d5a67b31bc3f34f535bf8543f735031dd2"
    assert historical.subject_commit == BASELINE
    assert historical.observer_commit == "604934c7afe244caf5b671423f108823a7753a98"
    assert historical.taxonomy_blob == "51a3931b43aa9030e166309289d6d85a80831526"
    assert (
        historical.taxonomy_content_sha256
        == "b5dfc532586b0e1f3c3f614ce34e70cd9e817b84adfeabfbda266adf19d07a3d"
    )
    assert live.subject_commit == BASELINE
    assert live.observer_commit == "fe94c0268d060742e808770d4d65d554709af0dd"
    assert live.taxonomy_blob == "280f4ff640b0d6088c6fc819bebca2c6a7de5fea"
    assert (
        live.taxonomy_content_sha256
        == "3180f9739fc254c29fa6ca6924818a2c3eb5d1ccedd0fe1916e88a05e1b41983"
    )
    assert historical.expected_absent_categories == ()
    assert historical.expected_required_gaps == ()
    assert history.entries["c1-static-hybrid-accepted"].expected_required_gaps == (
        "source_budget_native_parse_failed:yaml:.config/ci/templates/hosted/gitlab-ci.yml",
    )


def test_history_config_is_strict_and_rejects_unknown_fields_and_traversal() -> None:
    source = tomllib.loads(
        (ROOT / ".config/checks/source-budget/history.toml").read_text(encoding="utf-8")
    )
    source["entries"]["v1-continuation-20260719"]["expected_file_count"] = True
    with pytest.raises(ValidationError):
        replay.HistoryConfig.model_validate(source)

    source = tomllib.loads(
        (ROOT / ".config/checks/source-budget/history.toml").read_text(encoding="utf-8")
    )
    source["entries"]["v1-continuation-20260719"]["unexpected"] = "field"
    with pytest.raises(ValidationError):
        replay.HistoryConfig.model_validate(source)

    source = tomllib.loads(
        (ROOT / ".config/checks/source-budget/history.toml").read_text(encoding="utf-8")
    )
    source["entries"]["v1-continuation-20260719"]["taxonomy_path"] = "../selection.toml"
    with pytest.raises(ValidationError):
        replay.HistoryConfig.model_validate(source)


def test_replay_cli_writes_ignored_artifact_and_has_explicit_clean_mode() -> None:
    output = ROOT / "build/evidence/quality/source-budget-v2/replay/test-task4.json"
    output.unlink(missing_ok=True)
    assert (
        replay.main(
            ["--root", str(ROOT), "--entry", "v1-continuation-20260719", "--output", str(output)]
        )
        == 0
    )
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["entries"][0]["comparison_state"] == "reviewed_observation"
    assert payload["entries"][0]["v1"]["replay_total"] == 105060
    assert payload["entries"][0]["v1"]["metrics"]["jinja"] == 671
    assert payload["entries"][0]["v1"]["category_deltas"] == {
        "diagram": -1,
        "js": 1,
        "yaml": -282,
    }
    live_output = output.with_name("test-task4-live.json")
    live_output.unlink(missing_ok=True)
    assert (
        replay.main(
            [
                "--root",
                str(ROOT),
                "--entry",
                "v1-live-at-task4-start",
                "--output",
                str(live_output),
            ]
        )
        == 0
    )
    payload = json.loads(live_output.read_text(encoding="utf-8"))
    live = payload["entries"][0]
    assert live["comparison_state"] == "unresolved"
    assert live["required_gaps"] == ["source_budget_taxonomy_profile_unresolved"]
    assert "jinja" not in live["v1"]["metrics"]
    assert live["v1"]["category_deltas"]["jinja"] == -671
    assert (
        replay.main(
            [
                "--root",
                str(ROOT),
                "--entry",
                "v1-live-at-task4-start",
                "--require-clean",
                "--output",
                str(live_output),
            ]
        )
        == 1
    )


def test_c1_replay_admits_exact_expected_blocker_without_partial_v2_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_gap = (
        "source_budget_native_parse_failed:yaml:.config/ci/templates/hosted/gitlab-ci.yml"
    )

    def blocked_measurement(*_args: object):
        return MeasurementSnapshotLoad(None, (expected_gap,))

    monkeypatch.setattr(replay, "measure_snapshot_bytes", blocked_measurement)
    output = ROOT / "build/evidence/quality/source-budget-v2/replay/test-task4-c1.json"
    output.unlink(missing_ok=True)
    args = [
        "--root",
        str(ROOT),
        "--entry",
        "c1-static-hybrid-accepted",
        "--output",
        str(output),
    ]

    assert replay.main(args) == 0
    entry = json.loads(output.read_text(encoding="utf-8"))["entries"][0]
    assert entry["transport_valid"] is True
    assert entry["comparison_state"] == "blocked"
    assert entry["required_gaps"] == [expected_gap]
    assert entry["v2"]["coordinates"] is None
    assert entry["v2"]["vector_digest"] is None
    assert entry["v2"]["snapshot_digest"] is None
    assert replay.main([*args, "--require-clean"]) == 1


def test_c1_replay_rejects_forged_measurement_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = ROOT / "build/evidence/quality/source-budget-v2/replay/test-task4-c1-forged.json"
    output.unlink(missing_ok=True)
    monkeypatch.setattr(
        replay,
        "measure_snapshot_bytes",
        lambda *_args: SimpleNamespace(
            snapshot=None,
            required_gaps=(
                "source_budget_native_parse_failed:yaml:.config/ci/templates/hosted/gitlab-ci.yml",
            ),
        ),
    )

    assert (
        replay.main(
            [
                "--root",
                str(ROOT),
                "--entry",
                "c1-static-hybrid-accepted",
                "--output",
                str(output),
            ]
        )
        == 1
    )
    entry = json.loads(output.read_text(encoding="utf-8"))["entries"][0]
    assert entry["transport_valid"] is False
    assert entry["required_gaps"] == ["source_budget_replay_v2_measurement_invalid"]


def test_replay_rejects_outside_output_without_creating_parent(tmp_path: Path) -> None:
    output = tmp_path / "outside" / "replay.json"

    assert (
        replay.main(
            [
                "--root",
                str(ROOT),
                "--entry",
                "v1-continuation-20260719",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    assert not output.parent.exists()


def test_replay_atomic_write_failure_removes_temporary_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = ROOT / "build/evidence/quality/source-budget-v2/replay/test-task4-atomic.json"
    output.unlink(missing_ok=True)
    for temporary in output.parent.glob(f".{output.name}.*"):
        temporary.unlink()

    def fail_link(*_args: object, **_kwargs: object) -> None:
        message = "injected link failure"
        raise OSError(message)

    monkeypatch.setattr(artifacts.os, "link", fail_link)
    assert (
        replay.main(
            [
                "--root",
                str(ROOT),
                "--entry",
                "v1-continuation-20260719",
                "--output",
                str(output),
            ]
        )
        == 2
    )
    assert not output.exists()
    assert list(output.parent.glob(f".{output.name}.*")) == []


def test_artifact_publication_rejects_symlink_parent_and_is_handle_bound_on_swap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "build").symlink_to(outside, target_is_directory=True)
    with pytest.raises(OSError, match=r"Not a directory|Too many levels"):
        artifacts.write_replay_artifact(root, ARTIFACT_ROOT, None, _artifact_payload("symlink"))
    assert list(outside.rglob("*.json")) == []

    (root / "build").unlink()
    parent = root / ARTIFACT_ROOT
    parent.mkdir(parents=True)
    moved = outside / "moved-replay"
    payload = _artifact_payload("swap")
    real_link = os.link

    def swap_then_link(*args: object, **kwargs: object) -> None:
        parent.rename(moved)
        parent.symlink_to(outside, target_is_directory=True)
        real_link(*args, **kwargs)

    monkeypatch.setattr(artifacts.os, "link", swap_then_link)
    with pytest.raises(OSError, match="artifact directory changed"):
        artifacts.write_replay_artifact(root, ARTIFACT_ROOT, None, payload)
    assert not list(outside.rglob("*.json"))


def test_artifact_publication_reuses_identical_rejects_conflict_and_separates_concurrency(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    output = root / ARTIFACT_ROOT / "named.json"
    first = _artifact_payload("first")
    assert artifacts.write_replay_artifact(root, ARTIFACT_ROOT, output, first) == output
    before = output.read_bytes()
    assert artifacts.write_replay_artifact(root, ARTIFACT_ROOT, output, first) == output
    assert output.read_bytes() == before
    with pytest.raises(ValueError, match="conflicting replay artifact"):
        artifacts.write_replay_artifact(root, ARTIFACT_ROOT, output, _artifact_payload("conflict"))
    assert output.read_bytes() == before

    payloads = (_artifact_payload("left"), _artifact_payload("right"))
    with ThreadPoolExecutor(max_workers=2) as pool:
        paths = tuple(
            pool.map(
                lambda item: artifacts.write_replay_artifact(root, ARTIFACT_ROOT, None, item),
                payloads,
            )
        )
    assert paths == tuple(root / ARTIFACT_ROOT / f"{item['digest']}.json" for item in payloads)
    assert len(set(paths)) == 2


def test_replay_redacts_memory_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_load(_root: Path):
        raise MemoryError

    monkeypatch.setattr(replay, "load_history_config", fail_load)
    assert replay.main(["--root", str(ROOT)]) == 2


def test_replay_wrapper_and_tool_registry_use_one_owner_script() -> None:
    wrapper = ROOT / "tools/ci/scripts/run-source-budget-replay.sh"
    assert wrapper.is_file()
    assert "source_budget_replay.py" in wrapper.read_text(encoding="utf-8")
    catalog = tomllib.loads((ROOT / "system/tools.toml").read_text(encoding="utf-8"))
    entry = next(item for item in catalog["tool"] if item["concern"] == "source_budget_replay")
    assert entry["config"] == ".config/checks/source-budget/history.toml"
    assert entry["gate"] == "tools/ci/scripts/run-source-budget-replay.sh"
    assert entry["artifacts"] == "build/evidence/quality/source-budget-v2/replay/"


def test_v1_bytes_replay_rejects_duplicate_and_disordered_paths() -> None:
    taxonomy = _taxonomy("fe94c0268d060742e808770d4d65d554709af0dd")
    with pytest.raises(ValueError, match="unique and ordered"):
        source_budget_metrics_from_bytes((("b.py", b"b = 1\n"), ("a.py", b"a = 1\n")), taxonomy)
    with pytest.raises(ValueError, match="unique and ordered"):
        source_budget_metrics_from_bytes((("a.py", b"a = 1\n"), ("a.py", b"a = 1\n")), taxonomy)
