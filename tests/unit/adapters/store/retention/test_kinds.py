"""The record retirement preview classifies only its writers' exact records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.adapters.gates.input_key import record_results
from ethos.adapters.store.retention.kinds import classify_store
from ethos.adapters.store.retention.kinds import owned_directories
from tests.support.retention_store import gate_result
from tests.support.retention_store import javascript_attempt
from tests.support.retention_store import lane_unit
from tests.support.retention_store import manifest
from tests.support.retention_store import merge_preimage
from tests.support.retention_store import native_attempt
from tests.support.retention_store import proof_check
from tests.support.retention_store import proof_plan
from tests.support.retention_store import put

if TYPE_CHECKING:
    from pathlib import Path


def test_each_writer_record_and_lane_unit_has_its_kind(tmp_path: Path) -> None:
    """Artifacts take their writer's kind; units are terminal, receipt-only or manifest-only."""
    store = tmp_path / "store"
    proof = put(store, "artifacts", proof_check(), ".json", age_days=30)
    merge = put(store, "artifacts", merge_preimage(), ".json", age_days=30)
    native = put(store, "artifacts", native_attempt(), ".zip", age_days=30)
    script = put(store, "artifacts", javascript_attempt(), ".zip", age_days=30)
    foreign = put(store, "artifacts", b'{"producer": "other"}', ".json", age_days=30)
    plan = put(store, "artifacts", proof_plan(), ".json", age_days=30)
    # One key more than the plan's writer dumps: another producer's record, so it stays.
    near = put(store, "artifacts", proof_plan()[:-1] + b',"zz":1}', ".json", age_days=30)
    terminal, terminal_digest = lane_unit(store, "work/terminal", age_days=30)
    orphan, orphan_digest = lane_unit(store, "work/orphan", age_days=30, request=False)
    pending, _pending_digest = lane_unit(store, "work/pending", age_days=30, receipt=False)
    snapshot = store / "operations/lane-retirement" / terminal_digest / f"{'c' * 64}.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_bytes(b"{}")
    unbound = manifest(store, age_days=30)

    items, unowned = classify_store(store)

    found = {(item.kind, item.state, item.paths) for item in items}
    assert found == {
        ("proof-check", "artifact", (proof,)),
        ("proof-plan", "artifact", (plan,)),
        ("merge-preimage", "artifact", (merge,)),
        ("native-attempt", "artifact", (native,)),
        ("javascript-attempt", "artifact", (script,)),
        (
            "lane-retirement",
            "terminal",
            tuple(sorted((terminal["receipt"], terminal["request"], snapshot))),
        ),
        ("lane-retirement", "receipt-only", (orphan["receipt"],)),
        ("lane-retirement", "manifest-only", (unbound,)),
    }
    assert unowned == tuple(sorted((foreign, near)))
    named = {item.state: item.tokens for item in items if item.kind == "lane-retirement"}
    assert terminal_digest in named["terminal"]
    assert orphan_digest in named["receipt-only"]
    assert pending["request"] not in {path for item in items for path in item.paths}


def test_records_another_producer_wrote_are_kept_as_unowned(tmp_path: Path) -> None:
    """A misnamed request, a malformed receipt or a damaged archive is no writer's record."""
    store = tmp_path / "store"
    misnamed = store / "requests/lane-retirement" / f"{'d' * 64}.json"
    misnamed.parent.mkdir(parents=True)
    misnamed.write_bytes(b"{}")
    not_json = put(store, "receipts/lane-retirement", b"not json", ".json", age_days=30)
    listed = put(
        store,
        "receipts/lane-retirement",
        b'{"kind": "lane-retirement-receipt", "request": []}',
        ".json",
        age_days=30,
    )
    damaged = put(store, "artifacts", b"PK\x03\x04 broken", ".zip", age_days=30)
    a_list = put(store, "artifacts", b"[]", ".json", age_days=30)

    items, unowned = classify_store(store)

    assert items == ()
    assert unowned == tuple(sorted((misnamed, not_json, listed, damaged, a_list)))


def test_a_run_record_of_gate_results_is_owned_and_another_form_beside_it_is_not(
    tmp_path: Path,
) -> None:
    """The record retires as a record, under the record floor; any other file there stays."""
    store = tmp_path / "store"
    record = record_results(store, {"schema": 1, "head": "h", "tree": "t", "results": []})
    assert record.read_bytes() == gate_result()
    others = [
        put(store, "gate-results", payload, suffix, age_days=30)
        for payload, suffix in (
            (b'{"schema": 2, "head": "h", "tree": "t", "results": []}', ".json"),
            (b'{"schema": true, "head": "h", "tree": "t", "results": []}', ".json"),
            (b'{"schema": 1, "results": []}', ".json"),
            (b'{"schema": 1, "head": "h", "tree": "t", "results": null}', ".json"),
            (b"[]", ".json"),
            (gate_result("another suffix"), ".txt"),
            (gate_result("no suffix"), ""),
        )
    ]
    misnamed = store / "gate-results" / f"{'d' * 64}.json"
    misnamed.write_bytes(gate_result("misnamed"))

    items, unowned = classify_store(store)

    assert [(item.kind, item.state, item.paths) for item in items] == [
        ("gate-result", "record", (record,))
    ]
    assert unowned == tuple(sorted((*others, misnamed)))
    assert record.parent in owned_directories(store)
