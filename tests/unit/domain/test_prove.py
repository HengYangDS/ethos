from __future__ import annotations

from ethos.domain import prove


def test_role_for_classifies_tests_surface_and_logic():
    assert prove._role_for("tests/unit/test_sample.py", ()) == "test"
    assert prove._role_for("packages/pkg/tests/test_sample.py", ()) == "test"
    assert (
        prove._role_for("packages/ethos/src/ethos/surface/cli/rules.py", ("**/surface/**",))
        == "surface"
    )
    assert prove._role_for("packages/ethos/src/ethos/domain/plan.py", ("**/surface/**",)) == "logic"


def test_code_size_report_applies_role_limits_global_cap_and_exceptions(tmp_path, monkeypatch):
    files = {
        "packages/ethos/src/ethos/domain/small.py": "a=1\nb=2\n",
        "packages/ethos/src/ethos/surface/cli/big.py": "\n".join(f"x{i}=1" for i in range(4)),
        "tests/unit/test_big.py": "\n".join(f"x{i}=1" for i in range(4)),
        "packages/ethos/src/ethos/domain/excepted.py": "\n".join(f"x{i}=1" for i in range(10)),
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
            "global_hard_effective_max_lines": 4,
            "surface_path_globs": ["**/surface/**"],
            "exception": [
                {
                    "path": "packages/ethos/src/ethos/domain/excepted.py",
                    "effective_max_lines": 10,
                }
            ],
        },
    )
    monkeypatch.setattr(prove._git, "git_files", lambda _root, *_patterns: tuple(files))

    report = prove.code_size_report(tmp_path)
    by_path = {record["path"]: record for record in report["files"]}

    assert report["ok"] is True
    assert by_path["packages/ethos/src/ethos/domain/small.py"]["role"] == "logic"
    assert by_path["packages/ethos/src/ethos/surface/cli/big.py"]["limit"] == 4
    assert by_path["tests/unit/test_big.py"]["category"] == "test"
    assert by_path["packages/ethos/src/ethos/domain/excepted.py"]["exception"] is True


def test_code_size_report_emits_gap_when_effective_lines_exceed_limit(tmp_path, monkeypatch):
    relative = "packages/ethos/src/ethos/domain/too_big.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("a=1\nb=2\nc=3\n", encoding="utf-8")
    monkeypatch.setattr(prove, "code_size_policy", lambda _root: {"default_effective_max_lines": 2})
    monkeypatch.setattr(prove._git, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.code_size_report(tmp_path)

    assert report["ok"] is False
    assert report["required_gaps"] == [
        "code_size_exceeded:packages/ethos/src/ethos/domain/too_big.py:3>2"
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
