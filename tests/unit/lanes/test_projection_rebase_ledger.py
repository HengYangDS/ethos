from __future__ import annotations

from types import SimpleNamespace

import pytest

from ethos.adapters.mutation.lane_lifecycle.projection_rebase import ledger


def _rules(records: list[tuple[object, object]]) -> str:
    blocks = []
    for identifier, allowance in records:
        blocks.append(
            "\n".join(
                (
                    "[[quality.source_budget.debt.records]]",
                    f"id = {identifier!r}",
                    f"allowance = {allowance!r}",
                )
            )
        )
    return "\n\n".join(
        (
            "[quality.source_budget.debt]",
            f"maximum_total = {sum(allowance for _, allowance in records if isinstance(allowance, int) and not isinstance(allowance, bool))}",
            *blocks,
            "[other]\nvalue = true",
            "",
        )
    )


def _git(stages: dict[str, SimpleNamespace], calls: list[tuple[str, ...]]):
    def run(_root, *args: str, check: bool = True):
        calls.append(args)
        if args[:2] == ("diff", "--name-only"):
            return SimpleNamespace(stdout=".ethos/rules.toml\n", returncode=0)
        if args[:2] == ("show", ":1:.ethos/rules.toml"):
            return stages["base"]
        if args[:2] == ("show", ":2:.ethos/rules.toml"):
            return stages["candidate"]
        if args[:2] == ("show", ":3:.ethos/rules.toml"):
            return stages["lane"]
        return SimpleNamespace(stdout="", returncode=0)

    return run


def test_resolver_writes_and_stages_independent_append_only_records(tmp_path) -> None:
    stages = {
        "base": SimpleNamespace(stdout=_rules([("base", 10)]), returncode=0),
        "candidate": SimpleNamespace(
            stdout=_rules([("base", 10), ("candidate", 20)]), returncode=0
        ),
        "lane": SimpleNamespace(stdout=_rules([("base", 10), ("lane", 30)]), returncode=0),
    }
    calls: list[tuple[str, ...]] = []
    root = tmp_path
    (root / ".ethos").mkdir()
    result = ledger.resolve_source_budget_ledger_rebase_conflict(
        root, runtime=SimpleNamespace(run_git=_git(stages, calls))
    )

    assert result["ok"] is True
    assert result["gaps"] == ["semantic_ledger_merged:source_budget_debt"]
    assert ("add", ".ethos/rules.toml") in calls
    merged = (root / ".ethos" / "rules.toml").read_text(encoding="utf-8")
    assert "maximum_total = 60" in merged
    assert all(identifier in merged for identifier in ("base", "candidate", "lane"))
    assert (
        ledger.tomllib.loads(merged)["quality"]["source_budget"]["debt"]["records"][-1]["id"]
        == "lane"
    )


def test_resolver_preserves_record_child_tables(tmp_path) -> None:
    def categorized(identifier: str, allowance: int) -> str:
        return "\n".join(
            (
                ledger.RECORD,
                f'id = "{identifier}"',
                f"allowance = {allowance}",
                "",
                "[quality.source_budget.debt.records.allowance_by_category]",
                f"python_tests = {allowance}",
            )
        )

    def rules(*blocks: str) -> str:
        return "\n\n".join(
            (
                ledger.SECTION,
                f"maximum_total = {sum(int(block.split('allowance = ')[1].splitlines()[0]) for block in blocks)}",
                *blocks,
                "[other]\nvalue = true",
                "",
            )
        )

    stages = {
        "base": SimpleNamespace(stdout=rules(categorized("base", 10)), returncode=0),
        "candidate": SimpleNamespace(
            stdout=rules(categorized("base", 10), categorized("candidate", 20)),
            returncode=0,
        ),
        "lane": SimpleNamespace(
            stdout=rules(categorized("base", 10), categorized("lane", 30)), returncode=0
        ),
    }
    calls: list[tuple[str, ...]] = []
    (tmp_path / ".ethos").mkdir()

    result = ledger.resolve_source_budget_ledger_rebase_conflict(
        tmp_path, runtime=SimpleNamespace(run_git=_git(stages, calls))
    )

    assert result["ok"] is True
    merged = (tmp_path / ledger.RULES_PATH).read_text(encoding="utf-8")
    parsed = ledger.tomllib.loads(merged)["quality"]["source_budget"]["debt"]
    assert parsed["maximum_total"] == 60
    assert [record["id"] for record in parsed["records"]] == [
        "base",
        "candidate",
        "lane",
    ]
    assert parsed["records"][-1]["allowance_by_category"] == {"python_tests": 30}


def test_resolver_merges_disjoint_updates_to_existing_records(tmp_path) -> None:
    def categorized(retirement: int, status_tests: int, *, include_candidate: bool) -> str:
        records = [
            "\n".join(
                (
                    ledger.RECORD,
                    'id = "retirement"',
                    f"allowance = {retirement}",
                )
            ),
            "\n".join(
                (
                    ledger.RECORD,
                    'id = "status"',
                    "allowance = 100",
                    "",
                    "[quality.source_budget.debt.records.allowance_by_category]",
                    f"python_tests = {status_tests}",
                )
            ),
        ]
        if include_candidate:
            records.append(f'{ledger.RECORD}\nid = "candidate"\nallowance = 102')
        return "\n\n".join(
            (
                ledger.SECTION,
                f"maximum_total = {retirement + 100 + (102 if include_candidate else 0)}",
                *records,
                "[other]\nvalue = true",
                "",
            )
        )

    stages = {
        "base": SimpleNamespace(stdout=categorized(100, 80, include_candidate=False), returncode=0),
        "candidate": SimpleNamespace(
            stdout=categorized(100, 80, include_candidate=True), returncode=0
        ),
        "lane": SimpleNamespace(
            stdout=categorized(120, 100, include_candidate=False), returncode=0
        ),
    }
    calls: list[tuple[str, ...]] = []
    (tmp_path / ".ethos").mkdir()

    result = ledger.resolve_source_budget_ledger_rebase_conflict(
        tmp_path, runtime=SimpleNamespace(run_git=_git(stages, calls))
    )

    assert result["ok"] is True
    debt = ledger.tomllib.loads((tmp_path / ledger.RULES_PATH).read_text(encoding="utf-8"))[
        "quality"
    ]["source_budget"]["debt"]
    assert debt["maximum_total"] == 322
    assert {record["id"] for record in debt["records"]} == {
        "retirement",
        "status",
        "candidate",
    }
    status = next(record for record in debt["records"] if record["id"] == "status")
    assert status["allowance_by_category"] == {"python_tests": 100}


def test_resolver_refuses_to_claim_success_when_staging_fails(tmp_path) -> None:
    stages = {
        "base": SimpleNamespace(stdout=_rules([("base", 10)]), returncode=0),
        "candidate": SimpleNamespace(
            stdout=_rules([("base", 10), ("candidate", 20)]), returncode=0
        ),
        "lane": SimpleNamespace(stdout=_rules([("base", 10), ("lane", 30)]), returncode=0),
    }
    calls: list[tuple[str, ...]] = []
    git = _git(stages, calls)

    def stage_failure(root, *args: str, check: bool = True):
        result = git(root, *args, check=check)
        return (
            SimpleNamespace(stdout="", returncode=1)
            if args == ("add", ".ethos/rules.toml")
            else result
        )

    root = tmp_path
    (root / ".ethos").mkdir()
    result = ledger.resolve_source_budget_ledger_rebase_conflict(
        root, runtime=SimpleNamespace(run_git=stage_failure)
    )

    assert result["ok"] is False
    assert ("add", ".ethos/rules.toml") in calls


@pytest.mark.parametrize(
    "stages",
    [
        {"base": SimpleNamespace(stdout="invalid", returncode=0)},
        {"base": SimpleNamespace(stdout=_rules([("base", 10)]), returncode=1)},
        {
            "base": SimpleNamespace(stdout=_rules([("base", 10)]), returncode=0),
            "candidate": SimpleNamespace(stdout=_rules([("candidate", 20)]), returncode=0),
            "lane": SimpleNamespace(stdout=_rules([("base", 10), ("lane", 30)]), returncode=0),
        },
        {
            "base": SimpleNamespace(stdout=_rules([("base", 10)]), returncode=0),
            "candidate": SimpleNamespace(
                stdout=_rules([("base", 10), ("shared", 20)]), returncode=0
            ),
            "lane": SimpleNamespace(stdout=_rules([("base", 10), ("shared", 30)]), returncode=0),
        },
        {
            "base": SimpleNamespace(stdout=_rules([(None, 10)]), returncode=0),
            "candidate": SimpleNamespace(stdout=_rules([(None, 10)]), returncode=0),
            "lane": SimpleNamespace(stdout=_rules([(None, 10)]), returncode=0),
        },
    ],
)
def test_resolver_refuses_invalid_or_non_additive_ledgers(tmp_path, stages) -> None:
    defaults = {
        "base": SimpleNamespace(stdout=_rules([("base", 10)]), returncode=0),
        "candidate": SimpleNamespace(
            stdout=_rules([("base", 10), ("candidate", 20)]), returncode=0
        ),
        "lane": SimpleNamespace(stdout=_rules([("base", 10), ("lane", 30)]), returncode=0),
    }
    defaults.update(stages)
    calls: list[tuple[str, ...]] = []

    result = ledger.resolve_source_budget_ledger_rebase_conflict(
        tmp_path, runtime=SimpleNamespace(run_git=_git(defaults, calls))
    )

    assert result == {
        "ok": False,
        "paths": [".ethos/rules.toml"],
        "gaps": [],
        "next_actions": [],
    }
    assert ("add", ".ethos/rules.toml") not in calls


def test_parser_helpers_reject_malformed_records_and_split_tables(monkeypatch) -> None:
    assert ledger.parse(_rules([])) is None
    assert ledger.parse(_rules([("", 1)])) is None
    assert ledger.parse(_rules([("item", True)])) is None
    assert ledger.parse(_rules([("item", -1)])) is None
    assert (
        ledger.next_section("x\n[[quality.source_budget.debt.records]]\na=1\n[next]\nx=1\n", 2)
        == 44
    )
    assert ledger.split("prefix[[quality.source_budget.debt.records]]\na=1") == [
        "[[quality.source_budget.debt.records]]\na=1"
    ]
    parsed = {"quality": {"source_budget": {"debt": {"records": []}}}}
    monkeypatch.setattr(ledger.tomllib, "loads", lambda _text: parsed)
    assert ledger.parse(_rules([("item", 1)])) is None
    parsed["quality"]["source_budget"]["debt"]["records"] = [{"id": "one", "allowance": 1}]
    assert ledger.parse(_rules([("one", 1), ("two", 2)])) is None
    parsed["quality"]["source_budget"]["debt"]["records"] = ["not-a-record"]
    assert ledger.parse(_rules([("one", 1)])) is None


def test_semantic_ledger_helpers_cover_merge_and_render_edges(tmp_path) -> None:
    base = ledger.LedgerRecord("base", "base", 10, {"id": "base", "allowance": 10})
    changed = ledger.LedgerRecord("base", "changed", 20, {"id": "base", "allowance": 20})

    assert (
        ledger.unresolved_paths(
            tmp_path,
            runtime=SimpleNamespace(
                run_git=lambda *_args, **_kwargs: SimpleNamespace(stdout="", returncode=1)
            ),
        )
        == []
    )
    assert ledger.merge_records([base], [base], [changed]) == [changed]
    assert ledger.merge_records([base], [changed], [base]) == [changed]
    assert ledger.merge_records([base], [changed], [changed]) == [changed]
    conflicting = ledger.LedgerRecord("base", "conflicting", 30, {"id": "base", "allowance": 30})
    assert ledger.merge_records([base], [changed], [conflicting]) is None
    nested_base = ledger.LedgerRecord(
        "nested",
        "nested-base",
        1,
        {"id": "nested", "allowance": 1, "allowance_by_category": {"left": 1, "right": 1}},
    )
    nested_candidate = ledger.LedgerRecord(
        "nested",
        "nested-candidate",
        1,
        {"id": "nested", "allowance": 1, "allowance_by_category": {"left": 2, "right": 1}},
    )
    nested_lane = ledger.LedgerRecord(
        "nested",
        "nested-lane",
        1,
        {"id": "nested", "allowance": 1, "allowance_by_category": {"left": 1, "right": 2}},
    )
    merged_nested = ledger.merge_records([nested_base], [nested_candidate], [nested_lane])
    assert merged_nested is not None
    assert merged_nested[0].data["allowance_by_category"] == {"left": 2, "right": 2}
    assert ledger.merge_records([], [base], [base]) is None

    disjoint_base = {"left": 1, "right": 1}
    assert ledger.merge_values(disjoint_base, {"left": 2, "right": 1}, {"left": 1, "right": 2}) == {
        "left": 2,
        "right": 2,
    }
    assert ledger.merge_values(1, 1, 2) == 2
    assert ledger.merge_values(1, 2, 1) == 2
    assert ledger.merge_values(1, 2, 2) == 2
    assert ledger.merge_values(1, 2, 3) is None
    assert ledger.merge_values({"one": 1}, {"one": 2}, {"two": 3}) is None
    assert ledger.merge_values({"one": 1}, {"one": 2}, {"one": 3}) is None

    with pytest.raises(TypeError, match="must be a table"):
        ledger.record_from_data("bad")
    with pytest.raises(TypeError, match="identity contract"):
        ledger.record_from_data({"id": "bad", "allowance": True})
    rendered = ledger.record_from_data(
        {
            "id": "valid",
            "allowance": 3,
            "enabled": True,
            "label": "quoted",
            "allowance_by_category": {"python_tests": 3},
        }
    )
    assert rendered.identifier == "valid"
    assert "enabled = true" in rendered.block
    assert 'label = "quoted"' in rendered.block
    assert "[quality.source_budget.debt.records.allowance_by_category]" in rendered.block
    with pytest.raises(ValueError, match="unsupported"):
        ledger.toml_value([])

    nested = (
        f'{ledger.RECORD}\nid = "one"\nallowance = 1\n\n'
        "[quality.source_budget.debt.records.allowance_by_category]\npython_tests = 1\n"
        f'\n{ledger.RECORD}\nid = "two"\nallowance = 2\n[next]\nvalue = 1\n'
    )
    assert ledger.next_section(nested, 0) == nested.index("\n[next]")
    assert ledger.next_section(ledger.RECORD, 0) == len(ledger.RECORD)
    assert len(ledger.split(nested[: nested.index("\n[next]")])) == 2

    with pytest.raises(ValueError, match="maximum_total"):
        ledger.replace(f'{ledger.SECTION}\n{ledger.RECORD}\nid = "one"\nallowance = 1\n', [base])
