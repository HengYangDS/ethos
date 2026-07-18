from __future__ import annotations

import pytest

from ethos.domain import prove


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
        lambda _root: {
            "baseline": {
                "global_total": 6,
                "python_product": 1,
                "python_tests": 1,
                "python_tools": 0,
                "toml": 1,
                "json": 1,
                "jinja": 1,
            },
            "terminal": {"global_total": 3, "python_total": 2},
            "debt": {"maximum_total": 0, "records": []},
            "enforcement": "transition",
        },
        raising=False,
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: tuple(files))

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
        prove.git_adapter,
        "git_files",
        lambda _root, *_patterns: (*files, "tools/growth.sh"),
    )

    grown = prove.source_budget_report(tmp_path)

    assert grown["ok"] is False
    assert grown["required_gaps"] == ["source_budget_exceeded:global_total:7>6"]


def test_source_budget_derives_python_total_allowance_from_python_categories(tmp_path, monkeypatch):
    relative = "packages/ethos/src/ethos/domain/current.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: {
            "baseline": {"python_product": 0, "python_total": 0, "global_total": 0},
            "terminal": {"global_total": 0},
            "debt": {
                "maximum_total": 1,
                "records": [
                    {
                        "id": "typed-foundation",
                        "allowance": 1,
                        "allowance_by_category": {"python_product": 1},
                    }
                ],
            },
            "enforcement": "transition",
        },
        raising=False,
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.source_budget_report(tmp_path)

    assert report["ok"] is True


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
        lambda _root: {
            "baseline": {"yaml": 2, "global_total": 2},
            "terminal": {"global_total": 2},
            "debt": {"maximum_total": 0, "records": []},
            "enforcement": "transition",
        },
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: tuple(files))

    metrics = prove.source_budget_report(tmp_path)["metrics"]

    assert metrics["yaml"] == 2
    assert metrics["global_total"] == 2


@pytest.mark.parametrize("debt", ["invalid", {"records": "invalid"}, {"records": [None]}])
def test_source_budget_ignores_malformed_debt_records(debt):
    assert prove._source_budget_allowance({"debt": debt}) == (0, {}, [])  # noqa: RUF100, SLF001 - exact malformed-debt reducer coverage
    if debt == "invalid":
        assert prove._budget_ints(debt) == {}  # noqa: RUF100, SLF001 - exact invalid-input reducer coverage


def test_source_budget_ignores_boolean_allowance_and_blank_record_id():
    assert prove._source_budget_allowance(
        {"debt": {"records": [{"allowance": True, "id": ""}]}}
    ) == (0, {}, [])


def test_source_budget_reports_missing_policy_and_terminal_debt_gaps(tmp_path, monkeypatch):
    monkeypatch.setattr(prove, "source_budget_policy", lambda _root: {})
    assert prove.source_budget_report(tmp_path)["required_gaps"] == ["source_budget_policy_missing"]

    path = tmp_path / "tools" / "current.sh"
    path.parent.mkdir()
    path.write_text("echo current\n", encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "source_budget_policy",
        lambda _root: {
            "baseline": {"unknown": 0},
            "terminal": {"global_total": 0, "shell": 2},
            "debt": {"maximum_total": 0, "records": [{"id": "growth", "allowance": 1}]},
            "enforcement": "terminal",
        },
    )
    monkeypatch.setattr(
        prove.git_adapter, "git_files", lambda _root, *_patterns: ("tools/current.sh",)
    )

    report = prove.source_budget_report(tmp_path)

    assert report["required_gaps"] == [
        "source_budget_debt_exceeded:1>0",
        "source_budget_terminal_exceeded:global_total:1>0",
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
