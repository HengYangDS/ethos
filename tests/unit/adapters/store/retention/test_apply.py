"""The record retirement apply deletes only what its plan and a fresh scan both select."""

from __future__ import annotations

import json
import os
from contextlib import nullcontext
from pathlib import Path
from typing import Any

import pytest
from filelock import FileLock

import ethos.adapters.store.retention.apply as apply
import ethos.adapters.store.retention.closure as closure
import ethos.application.retention as retention
from ethos.adapters.repo.git import git_common_dir
from ethos.adapters.store.custody import custody_lock
from ethos.adapters.store.retention.plan import write_plan
from ethos.adapters.store.retention.tombstones import retire
from ethos.adapters.store.retention.tombstones import tombstone_of
from ethos.adapters.store.state.schema import local_state_root
from tests.support.governed_repository import adopt_and_commit
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import init_git_repo
from tests.support.retention_store import lane_unit
from tests.support.retention_store import merge_preimage
from tests.support.retention_store import native_attempt
from tests.support.retention_store import proof_check
from tests.support.retention_store import put

_REAL_RUNTIME_SELECTED = retention.runtime_selected
_DEFERRED = "record_retirement_batch_deferred:proof-check"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Provide a governed repository whose preview and apply run as the selected runtime."""
    repo = init_git_repo(tmp_path / "repo")
    adopt_and_commit(repo)
    monkeypatch.setattr(retention, "runtime_selected", lambda _root: True)
    return repo


def _planned(repo: Path) -> str:
    result = retention.preview_record_retirement(repo)
    assert result.verdict == "pass", result
    return result.data["plan"]["sha256"]


def _apply(repo: Path, plan: str, *, authorize: bool = True) -> Any:
    return retention.apply_record_retirement(repo, expect_plan=plan, authorize=authorize)


def test_an_apply_deletes_its_plan_once_and_receipts_the_run(repo: Path) -> None:
    """Each planned kind goes, a lane unit with its emptied operations; a rerun deletes nothing."""
    store = local_state_root(repo)
    unit, digest = lane_unit(store, "work/old", age_days=30)
    operation = put(store, f"operations/lane-retirement/{digest}", b"{}", ".json", age_days=30)
    planned = [
        put(store, "artifacts", proof_check(), ".json", age_days=30),
        put(store, "artifacts", native_attempt(), ".zip", age_days=30),
        put(store, "artifacts", merge_preimage(), ".json", age_days=30),
        *unit.values(),
        operation,
    ]
    young = put(store, "artifacts", proof_check("c" * 40), ".json", age_days=1)
    plan = _planned(repo)

    result = _apply(repo, plan)

    assert (result.verdict, result.state) == ("pass", "applied"), result
    assert not any(path.exists() for path in planned)
    assert not operation.parent.exists()
    assert young.exists()
    kinds = result.data["kinds"]
    assert {kind: tally["deleted"] for kind, tally in kinds.items()} == dict.fromkeys(
        ("proof-check", "native-attempt", "merge-preimage", "lane-retirement"), 1
    )
    assert kinds["proof-check"]["deleted_bytes"] == len(proof_check())
    receipt = json.loads(Path(result.data["receipt"]["path"]).read_bytes())
    assert (receipt["plan"], receipt["kinds"], receipt["live_members_clear"]) == (plan, kinds, True)
    again = _apply(repo, plan)
    assert (again.verdict, again.state) == ("pass", "already_applied"), again


@pytest.mark.parametrize("change", ["touched", "named", "member", "absent", "floor"])
def test_an_item_that_changed_or_is_named_since_its_plan_stays(
    repo: Path, monkeypatch: pytest.MonkeyPatch, change: str
) -> None:
    """A changed, newly named or now young item stays; an absent one counts as done."""
    store = local_state_root(repo)
    target = put(store, "artifacts", proof_check(), ".json", age_days=30)
    other = put(store, "artifacts", merge_preimage(), ".json", age_days=30)
    plan = _planned(repo)
    if change == "touched":
        os.utime(target)
    elif change == "named":
        put(store, "custody", target.stem.encode(), ".bin", age_days=0)
    elif change == "member":
        monkeypatch.setattr(closure, "live_member_bytes", lambda _root: [target.stem.encode()])
    elif change == "absent":
        target.unlink()
    else:
        rules = "[paradigm.retention]\ngrace_seconds = 3456000\n"
        (repo / ".ethos/rules.toml").write_text(rules, encoding="utf-8")
        commit_fixture(repo, "raise the artifact floor")

    result = _apply(repo, plan)

    assert (result.verdict, result.state) == ("pass", "applied"), result
    tally = result.data["kinds"]["proof-check"]
    if change == "absent":
        assert (tally["absent"], tally["kept"]) == (1, {})
    else:
        reason = {"touched": "changed", "named": "named", "member": "named", "floor": "young"}
        assert (tally["deleted"], tally["kept"]) == (0, {reason[change]: 1})
        assert target.exists()
    assert other.exists() is (change == "floor")


def test_an_interrupted_apply_is_restored_first_and_then_continued(repo: Path) -> None:
    """The next preview restores tombstones and keeps a clash; a rerun ends the half-gone unit."""
    store = local_state_root(repo)
    check = put(store, "artifacts", proof_check(), ".json", age_days=30)
    unit, _digest = lane_unit(store, "work/old", age_days=30)
    plan = _planned(repo)
    stone = retire(check)
    unit["request"].unlink()
    clash = put(store, "artifacts", proof_check("d" * 40), ".json", age_days=1)
    tombstone_of(clash).write_bytes(b"other bytes")

    preview = retention.preview_record_retirement(repo)

    assert preview.verdict == "pass", preview
    assert check.exists()
    assert stone is not None
    assert not stone.exists()
    assert preview.data["conflicts"] == (tombstone_of(clash).relative_to(store).as_posix(),)
    result = _apply(repo, plan)
    assert (result.verdict, result.state) == ("pass", "applied"), result
    assert not check.exists()
    assert not unit["receipt"].exists()
    assert clash.exists()
    assert tombstone_of(clash).exists()
    assert result.data["kinds"]["lane-retirement"]["deleted"] == 1


@pytest.mark.parametrize("listing", ["generation", "unknown", "elsewhere"])
def test_another_interpreter_of_the_repository_defers_the_batch(
    repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, listing: str
) -> None:
    """Another runtime generation or an unreadable listing defers; another repository does not."""
    store = local_state_root(repo)
    check = put(store, "artifacts", proof_check(), ".json", age_days=30)
    plan = _planned(repo)
    generation = Path("ethos/runtime") / ("e" * 64) / "bin/python3"
    interpreters = {
        "generation": Path(git_common_dir(repo)) / generation,
        "elsewhere": tmp_path / "other/.git" / generation,
    }
    for path in interpreters.values():
        path.parent.mkdir(parents=True)
        path.write_bytes(b"")

    def commands(*_args: object, **_kwargs: object) -> str:
        if listing == "unknown":
            message = "hook_runtime_consumers_unknown"
            raise ValueError(message)
        return f"{interpreters[listing]} -m ethos prove --json\n"

    monkeypatch.setattr(apply, "process_commands", commands)
    result = _apply(repo, plan)

    deferred = listing != "elsewhere"
    assert check.exists() is deferred
    assert not tombstone_of(check).exists()
    assert result.required_gaps == ((f"{_DEFERRED}:writer",) if deferred else ())


@pytest.mark.parametrize("event", ["accepted", "member", "held"])
def test_a_move_during_the_compare_keeps_what_it_names(
    repo: Path, monkeypatch: pytest.MonkeyPatch, event: str
) -> None:
    """An accepted advance or a set swap before the unlink restores; a held lock defers."""
    store = local_state_root(repo)
    check = put(store, "artifacts", proof_check(), ".json", age_days=30)
    plan = _planned(repo)
    holds: list[Path] = []

    def lock(root: Path) -> FileLock:
        holds.append(root)
        if len(holds) == 1 and event == "accepted":
            (repo / "notes.md").write_text(f"evidence {check.stem}\n", encoding="utf-8")
            commit_fixture(repo, "name a tombstoned record")
        elif len(holds) == 1 and event == "member":
            monkeypatch.setattr(closure, "live_member_bytes", lambda _root: [check.stem.encode()])
            monkeypatch.setattr(closure, "set_root", lambda _root: "f" * 40)
        return custody_lock(root)

    monkeypatch.setattr(apply, "custody_lock", lock)
    with custody_lock(repo) if event == "held" else nullcontext():
        result = _apply(repo, plan)

    assert check.exists()
    assert not tombstone_of(check).exists()
    if event == "held":
        assert (result.required_gaps, len(holds)) == ((f"{_DEFERRED}:custody",), 3)
    else:
        assert result.data["kinds"]["proof-check"]["kept"] == {"named": 1}


@pytest.mark.parametrize(
    ("refusal", "gap"),
    [
        ("authorize", "authorization_required"),
        ("required", "record_retirement_plan_required"),
        ("missing", "record_retirement_plan_missing"),
        ("altered", "record_retirement_plan_mismatch"),
        ("schema", "record_retirement_plan_mismatch"),
        ("progress", "record_retirement_in_progress"),
        ("runtime", "record_retirement_runtime_unselected"),
    ],
)
def test_an_apply_refuses_and_deletes_nothing(
    repo: Path, monkeypatch: pytest.MonkeyPatch, refusal: str, gap: str
) -> None:
    """No authorization, a missing, altered or older plan, a held run or another runtime refuse."""
    store = local_state_root(repo)
    check = put(store, "artifacts", proof_check(), ".json", age_days=30)
    plan = _planned(repo)
    path = store / "requests/record-retirement" / f"{plan}.json"
    if refusal == "required":
        plan = ""
    elif refusal == "missing":
        plan = "f" * 64
    elif refusal == "altered":
        path.write_bytes(path.read_bytes() + b" ")
    elif refusal == "schema":
        plan = write_plan(store, {**json.loads(path.read_bytes()), "schema_version": 1})["sha256"]
    elif refusal == "runtime":
        monkeypatch.setattr(retention, "runtime_selected", _REAL_RUNTIME_SELECTED)
    held = FileLock(str(store / "retention.lock")) if refusal == "progress" else nullcontext()
    with held:
        result = _apply(repo, str(plan), authorize=refusal != "authorize")

    assert (result.verdict, result.required_gaps) == ("block", (gap,)), result
    assert check.exists()
    assert not (store / "receipts/record-retirement").exists()


class _Stuck(type(Path())):
    """A tombstone whose unlink another process holds open."""

    def unlink(self, *_args: object, **_kwargs: object) -> None:
        raise PermissionError(self)


@pytest.mark.parametrize(
    "event",
    ["slot", "lane-lock", "in_use", "vanished", "altered", "adopted", "unlink", "runtime", "holds"],
)
def test_a_batch_keeps_or_defers_what_it_cannot_delete_cleanly(
    repo: Path, monkeypatch: pytest.MonkeyPatch, event: str
) -> None:
    """A held lock, a record in use, gone, changed or adopted, a stuck unlink or another runtime."""
    store = local_state_root(repo)
    check = put(store, "artifacts", proof_check(), ".json", age_days=30)
    second = put(store, "artifacts", proof_check("b" * 40), ".json", age_days=30)
    unit, _digest = lane_unit(store, "work/old", age_days=30)
    plan = _planned(repo)
    real_retire, real_lock = apply.retire, apply.custody_lock
    (store / "operations").mkdir(exist_ok=True)
    locks = {"slot": "proof-slot.lock", "lane-lock": "operations/lane-retirement.lock"}
    held = FileLock(str(store / locks[event])) if event in locks else nullcontext()

    def retire(path: Path) -> Path | None:
        if event == "vanished":
            raise FileNotFoundError(path)
        stone = real_retire(path)
        if event == "altered" and stone is not None:
            os.utime(stone, ns=(1, 1))
        return _Stuck(stone) if event == "unlink" and path == check and stone else stone

    def adopting(root: Path) -> FileLock:
        check.write_bytes(proof_check())
        return real_lock(root)

    answers = iter([True])
    patches = {
        "vanished": (apply, "retire", retire),
        "altered": (apply, "retire", retire),
        "unlink": (apply, "retire", retire),
        "in_use": (apply, "retire", lambda _path: None),
        "adopted": (apply, "custody_lock", adopting),
        "runtime": (retention, "runtime_selected", lambda _root: next(answers, False)),
        "holds": (apply, "_PER_HOLD", 1),
    }
    if event in patches:
        monkeypatch.setattr(*patches[event])
    with held:
        result = _apply(repo, plan)

    kept = {path for path in (check, second, *unit.values()) if path.exists()}
    expected = {
        "slot": ({check, second}, ("record_retirement_batch_deferred:proof-check:slot",)),
        "lane-lock": (
            set(unit.values()),
            ("record_retirement_batch_deferred:lane-retirement:lane-lock",),
        ),
        "in_use": ({check, second, *unit.values()}, ()),
        "vanished": ({check, second, *unit.values()}, ()),
        "altered": ({check, second, *unit.values()}, ()),
        "adopted": ({check}, ()),
        "unlink": (set(), ("record_retirement_batch_deferred:proof-check:unlink",)),
        "runtime": ({check, second, *unit.values()}, ("record_retirement_runtime_unselected",)),
        "holds": (set(), ()),
    }[event]
    assert (kept, result.required_gaps) == expected, result
    if event == "unlink":
        assert tombstone_of(check).exists()
        monkeypatch.setattr(apply, "retire", real_retire)
        assert _apply(repo, plan).verdict == "pass"
        assert not tombstone_of(check).exists()
        assert not check.exists()
