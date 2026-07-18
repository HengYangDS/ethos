from __future__ import annotations

from datetime import date

from ethos.domain import prove
from ethos_core.contracts.source_budget.core import SourceBudgetPolicy
from ethos_core.contracts.source_budget.core import SourceBudgetPolicyLoad


def _source_budget_load(policy: dict[str, object]) -> SourceBudgetPolicyLoad:
    return SourceBudgetPolicyLoad(
        policy=SourceBudgetPolicy.model_validate({"baseline_head": "a" * 40, **policy}),
        required_gaps=(),
    )


def test_role_for_classifies_tests_surface_and_logic():
    assert prove._role_for("tests/unit/test_sample.py", ()) == "test"
    assert prove._role_for("packages/pkg/tests/test_sample.py", ()) == "test"
    assert (
        prove._role_for("packages/ethos/src/ethos/surface/cli/rules.py", ("**/surface/**",))
        == "surface"
    )
    assert prove._role_for("packages/ethos/src/ethos/domain/plan.py", ("**/surface/**",)) == "logic"


def test_code_size_report_applies_role_limits_and_global_cap(tmp_path, monkeypatch):
    files = {
        "packages/ethos/src/ethos/domain/small.py": "a=1\nb=2\n",
        "packages/ethos/src/ethos/surface/cli/big.py": "\n".join(f"x{i}=1" for i in range(4)),
        "tests/unit/test_big.py": "\n".join(f"x{i}=1" for i in range(4)),
        # An over-limit logic file is held to its role limit — there is no way to
        # exempt it, so it fails.
        "packages/ethos/src/ethos/domain/oversized.py": "\n".join(f"x{i}=1" for i in range(10)),
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(
        prove,
        "code_size_policy",
        lambda _root: {
            "default_effective_max_lines": 3,
            "surface_effective_max_lines": 5,
            "test_effective_max_lines": 8,
            "surface_path_globs": ["**/surface/**"],
        },
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: tuple(files))

    report = prove.code_size_report(tmp_path)
    by_path = {record["path"]: record for record in report["files"]}

    assert by_path["packages/ethos/src/ethos/domain/small.py"]["role"] == "logic"
    assert by_path["packages/ethos/src/ethos/domain/small.py"]["limit"] == 3
    assert by_path["packages/ethos/src/ethos/surface/cli/big.py"]["limit"] == 5
    assert by_path["tests/unit/test_big.py"]["limit"] == 8
    assert by_path["tests/unit/test_big.py"]["category"] == "test"
    # An oversized logic file is held to its role limit (3) and therefore fails —
    # no per-file escape hatch exists.
    oversized = by_path["packages/ethos/src/ethos/domain/oversized.py"]
    assert oversized["limit"] == 3
    assert oversized["ok"] is False
    assert report["ok"] is False


def test_code_size_report_emits_gap_when_effective_lines_exceed_limit(tmp_path, monkeypatch):
    relative = "packages/ethos/src/ethos/domain/too_big.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("a=1\nb=2\nc=3\n", encoding="utf-8")
    monkeypatch.setattr(prove, "code_size_policy", lambda _root: {"default_effective_max_lines": 2})
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.code_size_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "code_size_exceeded:packages/ethos/src/ethos/domain/too_big.py:3>2"
    ]


def test_code_size_report_skips_deleted_tracked_paths(tmp_path, monkeypatch):
    relative = "packages/ethos/src/ethos/domain/deleted.py"
    monkeypatch.setattr(prove, "code_size_policy", lambda _root: {"default_effective_max_lines": 2})
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.code_size_report(tmp_path)

    assert report["ok"] is True
    assert report["files"] == []
    assert report["required_gaps"] == []


def test_source_budget_reports_all_executable_carriers_and_blocks_unfunded_growth(
    tmp_path, monkeypatch
):
    files = {
        "packages/ethos/src/ethos/domain/current.py": "value = 1\n",
        "tests/unit/test_current.py": "assert True\n",
        "tools/check.sh": "echo ok\n",
        "system/current.toml": "value = 1\n",
        "schemas/current.json": '{"type": "object"}\n',
        "templates/current.j2": "{# generated comment #}\n{{ value }}\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: _source_budget_load(
            {
                "baseline": {
                    "global_total": 6,
                    "python_total": 2,
                    "python_product": 1,
                    "python_tests": 1,
                    "python_tools": 0,
                    "toml": 1,
                    "json": 1,
                    "jinja": 1,
                },
                "terminal": {"global_total": 3, "python_total": 2},
                "debt": {"maximum_total": 0, "waves": [], "records": []},
                "enforcement": "transition",
            }
        ),
        raising=False,
    )
    monkeypatch.setattr(prove.git_adapter, "git_stdout", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        prove.source_budget_adapter,
        "present_worktree_paths",
        lambda _root: tuple(files),
    )

    report = prove.source_budget_report(tmp_path)

    assert report["metrics"] == {
        "python_product": 1,
        "python_tests": 1,
        "python_tools": 0,
        "python_other": 0,
        "shell": 1,
        "js": 0,
        "toml": 1,
        "yaml": 0,
        "json": 1,
        "jinja": 1,
        "ini": 0,
        "diagram": 0,
        "python_total": 2,
        "global_total": 6,
    }
    assert report["terminal_target_met"] is False
    assert report["ok"] is True

    (tmp_path / "tools" / "growth.sh").write_text("echo growth\n", encoding="utf-8")
    monkeypatch.setattr(
        prove.source_budget_adapter,
        "present_worktree_paths",
        lambda _root, *_patterns: (*files, "tools/growth.sh"),
    )

    grown = prove.source_budget_report(tmp_path)

    assert grown["ok"] is False
    assert grown["required_gaps"] == ["source_budget_exceeded:global_total:7>6"]


def test_source_budget_classifies_non_product_python_and_non_code_carriers(tmp_path) -> None:
    archived = "openspec/changes/archive/2026-07-18-closed/.openspec.yaml"
    files = {
        "scripts/tool.py": "value = 1\n",
        "notes.txt": "ignored\n",
        "config/current.ini": "; comment\nvalue = 1\n",
        "diagram/current.mmd": "%% comment\nflowchart TD\n",
        archived: "schema: spec-driven\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    assert prove.source_budget_carrier_report(tmp_path / "scripts/tool.py", "scripts/tool.py") == {
        "category": "python_other",
        "effective_lines": 1,
    }
    assert prove.source_budget_carrier_report(tmp_path / "notes.txt", "notes.txt") == {
        "category": None,
        "effective_lines": 0,
    }
    assert prove.source_budget_carrier_report(tmp_path / archived, archived) == {
        "category": None,
        "effective_lines": 0,
    }
    assert prove.source_budget_carrier_report(
        tmp_path / "config/current.ini", "config/current.ini"
    ) == {
        "category": "ini",
        "effective_lines": 1,
    }
    assert prove.source_budget_carrier_report(
        tmp_path / "diagram/current.mmd", "diagram/current.mmd"
    ) == {"category": "diagram", "effective_lines": 1}


def test_source_budget_derives_python_total_allowance_from_python_categories(tmp_path, monkeypatch):
    relative = "packages/ethos/src/ethos/domain/current.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: _source_budget_load(
            {
                "baseline": {"python_product": 0, "python_total": 0, "global_total": 0},
                "terminal": {"python_total": 0, "global_total": 0},
                "debt": {
                    "maximum_total": 1,
                    "waves": [{"id": "wave", "due_on": "2026-12-01", "state": "active"}],
                    "records": [
                        {
                            "id": "typed-foundation",
                            "owner": "owner",
                            "replacement": "replacement",
                            "deletion_wave": "wave",
                            "expiry": "2026-12-01",
                            "allowance": 1,
                            "expected_net_deletion": 1,
                            "allowance_by_category": {"python_product": 1},
                        }
                    ],
                },
                "enforcement": "transition",
            }
        ),
        raising=False,
    )
    monkeypatch.setattr(prove.git_adapter, "git_stdout", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        prove.source_budget_adapter, "present_worktree_paths", lambda _root: (relative,)
    )

    report = prove.source_budget_report(tmp_path)

    assert report["ok"] is True


def test_source_budget_report_skips_absent_declared_metric_category(tmp_path, monkeypatch):
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: _source_budget_load(
            {
                "baseline": {"global_total": 0, "python_total": 0, "shell": 0},
                "terminal": {"global_total": 0, "python_total": 0, "shell": 0},
                "debt": {"maximum_total": 0, "waves": [], "records": []},
                "enforcement": "transition",
            }
        ),
    )
    monkeypatch.setattr(
        prove,
        "_source_budget_metrics",
        lambda _root: ({"global_total": 0, "python_total": 0}, {"file_count": 0}),
    )
    monkeypatch.setattr(prove.git_adapter, "git_stdout", lambda *_args: "a" * 40)

    assert prove.source_budget_report(tmp_path)["ok"] is True


def test_source_budget_excludes_archived_openspec_metadata_only(tmp_path, monkeypatch):
    files = {
        "openspec/changes/archive/2026-07-12-closed/.openspec.yaml": (
            "schema: spec-driven\ncreated: 2026-07-12\nstatus: archived\n"
        ),
        "openspec/changes/current/.openspec.yaml": "schema: spec-driven\n",
        "config/current.yaml": "value: true\n",
    }
    for relative, content in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: _source_budget_load(
            {
                "baseline": {"yaml": 2, "python_total": 0, "global_total": 2},
                "terminal": {"python_total": 0, "global_total": 2},
                "debt": {"maximum_total": 0, "waves": [], "records": []},
                "enforcement": "transition",
            }
        ),
    )
    monkeypatch.setattr(prove.git_adapter, "git_stdout", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        prove.source_budget_adapter,
        "present_worktree_paths",
        lambda _root: tuple(files),
    )

    metrics = prove.source_budget_report(tmp_path)["metrics"]

    assert metrics["yaml"] == 2
    assert metrics["global_total"] == 2


def test_source_budget_reports_missing_policy_and_terminal_debt_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: SourceBudgetPolicyLoad(None, ("source_budget_policy_missing",)),
    )
    assert prove.source_budget_report(tmp_path)["required_gaps"] == ["source_budget_policy_missing"]

    path = tmp_path / "tools" / "current.sh"
    path.parent.mkdir()
    path.write_text("echo current\n", encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: _source_budget_load(
            {
                "baseline": {"python_total": 0, "global_total": 0},
                "terminal": {"python_total": 0, "global_total": 0, "shell": 2},
                "debt": {
                    "maximum_total": 0,
                    "waves": [{"id": "wave", "due_on": "2026-12-01", "state": "active"}],
                    "records": [
                        {
                            "id": "growth",
                            "owner": "owner",
                            "replacement": "replacement",
                            "deletion_wave": "wave",
                            "expiry": "2026-12-01",
                            "allowance": 1,
                            "expected_net_deletion": 1,
                            "allowance_by_category": {"global_total": 1},
                        }
                    ],
                },
                "enforcement": "terminal",
            }
        ),
    )
    monkeypatch.setattr(prove.git_adapter, "git_stdout", lambda *_args: "a" * 40)
    monkeypatch.setattr(
        prove.source_budget_adapter,
        "present_worktree_paths",
        lambda _root: ("tools/current.sh",),
    )

    report = prove.source_budget_report(tmp_path)

    assert report["required_gaps"] == [
        "source_budget_debt_exceeded:1>0",
        "source_budget_terminal_exceeded:global_total:1>0",
    ]


def test_source_budget_reports_config_validation_gap(tmp_path, monkeypatch):
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: SourceBudgetPolicyLoad(
            policy=None,
            required_gaps=("source_budget_policy_invalid:debt.records.0.expiry",),
        ),
    )

    report = prove.source_budget_report(tmp_path)

    assert report["ok"] is False
    assert report["state"] == "blocked"
    assert report["metrics"]["global_total"] == 0
    assert report["inventory"]["file_count"] == 0
    assert report["required_gaps"] == ["source_budget_policy_invalid:debt.records.0.expiry"]


def test_source_budget_reports_lifecycle_and_present_inventory(tmp_path, monkeypatch):
    relative = "packages/ethos/src/ethos/domain/current.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: _source_budget_load(
            {
                "baseline": {"python_product": 1, "python_total": 1, "global_total": 1},
                "terminal": {"python_total": 1, "global_total": 1},
                "debt": {
                    "maximum_total": 0,
                    "waves": [
                        {"id": "active", "due_on": "2026-12-01", "state": "active"},
                        {"id": "settled", "due_on": "2026-07-01", "state": "settled"},
                    ],
                    "records": [
                        {
                            "id": "expired",
                            "owner": "owner",
                            "replacement": "replacement",
                            "deletion_wave": "active",
                            "expiry": "2026-07-16",
                            "allowance": 0,
                            "expected_net_deletion": 1,
                            "allowance_by_category": {},
                        },
                        {
                            "id": "stale",
                            "owner": "owner",
                            "replacement": "replacement",
                            "deletion_wave": "settled",
                            "expiry": "2026-12-01",
                            "allowance": 0,
                            "expected_net_deletion": 1,
                            "allowance_by_category": {},
                        },
                    ],
                },
                "enforcement": "transition",
            }
        ),
    )
    monkeypatch.setattr(prove.git_adapter, "git_stdout", lambda *_args: "")
    monkeypatch.setattr(
        prove.source_budget_adapter, "present_worktree_paths", lambda _root: (relative,)
    )
    monkeypatch.setattr(prove, "_source_budget_today", lambda: date(2026, 7, 17))

    report = prove.source_budget_report(tmp_path)

    assert report["required_gaps"] == [
        "source_budget_baseline_head_unresolved:" + "a" * 40,
        "source_budget_debt_expired:expired",
        "source_budget_debt_stale:stale",
    ]
    assert report["baseline_head"] == {"value": "a" * 40, "resolved": False}
    assert report["inventory"]["file_count"] == 1
    assert report["inventory"]["category_counts"] == {"python_product": 1}
    assert len(report["inventory"]["digest"]) == 64
    assert report["debt_lifecycle"] == [
        {
            "id": "expired",
            "wave": "active",
            "wave_due_on": "2026-12-01",
            "wave_state": "active",
            "owner": "owner",
            "replacement": "replacement",
            "expiry": "2026-07-16",
            "allowance": 0,
            "expected_net_deletion": 1,
            "status": "expired",
            "required_gaps": ["source_budget_debt_expired:expired"],
        },
        {
            "id": "stale",
            "wave": "settled",
            "wave_due_on": "2026-07-01",
            "wave_state": "settled",
            "owner": "owner",
            "replacement": "replacement",
            "expiry": "2026-12-01",
            "allowance": 0,
            "expected_net_deletion": 1,
            "status": "stale",
            "required_gaps": ["source_budget_debt_stale:stale"],
        },
    ]


def test_workspace_status_validation_prefixes_schema_gaps(monkeypatch, tmp_path):
    def fake_validate(schema_name, payload, root):
        return {
            "ok": False,
            "required_gaps": [f"{schema_name}:missing:branch"],
        }

    monkeypatch.setattr(prove, "validate_schema_instance", fake_validate)

    validation = prove.workspace_status_validation(tmp_path, {"branch": "dev"})

    assert validation["schema"] == "workspace-status.schema.json"
    assert validation["ok"] is False
    assert prove.workspace_status_validation_gaps(validation) == (
        "workspace_status_schema:workspace-status.schema.json:missing:branch",
    )
