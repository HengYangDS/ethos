from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import ethos.domain.prove as prove
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize(
    ("relative", "limit"),
    [("src/logic.py", 500), ("src/ethos/surface/cli/view.py", 500), ("tests/test_case.py", 800)],
)
def test_public_size_gate_enforces_current_role_boundaries(
    tmp_path: Path, relative: str, limit: int
) -> None:
    """The native CLI accepts each exact ceiling and rejects one additional source line."""
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_bytes((Path(__file__).resolve().parents[3] / ".ethos/rules.toml").read_bytes())
    source = root / relative
    source.parent.mkdir(parents=True)
    for lines in (limit, limit + 1):
        source.write_text("value = 1\n" * lines, encoding="utf-8")
        git(root, "add", relative)
        result = run_ethos_raw(
            "prove", "--host", "--execute", "--gate", "python-size", "--json", cwd=root
        )
        report = json.loads(result.stdout)
        assert report["verdict"] == ("pass" if lines == limit else "block"), report
        observed = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]
        assert observed["default_effective_max_lines"] == 500
        assert observed["surface_effective_max_lines"] == 500
        assert observed["test_effective_max_lines"] == 800
        assert observed["required_gaps"] == (
            [] if lines == limit else [f"code_size_exceeded:{relative}:{lines}>{limit}"]
        )
        assert report["summary"]["proof_attestation_issued"] is False


def test_code_size_report_applies_role_limits_and_global_cap(tmp_path, monkeypatch):
    files = {
        "src/ethos/domain/small.py": "a=1\nb=2\n",
        "src/ethos/surface/cli/big.py": "\n".join(f"x{i}=1" for i in range(4)),
        "tests/unit/test_big.py": "\n".join(f"x{i}=1" for i in range(4)),
        # An over-limit logic file is held to its role limit — there is no way to
        # exempt it, so it fails.
        "src/ethos/domain/oversized.py": "\n".join(f"x{i}=1" for i in range(10)),
    }
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {
            "quality": {
                "code_size": {
                    "default_effective_max_lines": 3,
                    "surface_effective_max_lines": 5,
                    "test_effective_max_lines": 8,
                    "surface_path_globs": ["**/surface/**"],
                }
            }
        },
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: tuple(files))

    report = prove.code_size_report(tmp_path)
    records = cast("list[dict[str, object]]", report["files"])
    by_path = {record["path"]: record for record in records}

    assert by_path["src/ethos/domain/small.py"]["role"] == "logic"
    assert by_path["src/ethos/domain/small.py"]["limit"] == 3
    assert by_path["src/ethos/surface/cli/big.py"]["limit"] == 5
    assert by_path["tests/unit/test_big.py"]["limit"] == 8
    assert by_path["tests/unit/test_big.py"]["category"] == "test"
    # An oversized logic file is held to its role limit (3) and therefore fails —
    # no per-file escape hatch exists.
    oversized = by_path["src/ethos/domain/oversized.py"]
    assert oversized["limit"] == 3
    assert oversized["within_limit"] is False
    assert report["verdict"] == "block"
    assert "ok" not in report


def test_code_size_report_emits_gap_when_effective_lines_exceed_limit(tmp_path, monkeypatch):
    relative = "src/ethos/domain/too_big.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("a=1\nb=2\nc=3\n", encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {"quality": {"code_size": {"default_effective_max_lines": 2}}},
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.code_size_report(tmp_path)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["code_size_exceeded:src/ethos/domain/too_big.py:3>2"]


def test_code_size_report_skips_deleted_tracked_paths(tmp_path, monkeypatch):
    relative = "src/ethos/domain/deleted.py"
    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {"quality": {"code_size": {"default_effective_max_lines": 2}}},
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.code_size_report(tmp_path)

    assert report["verdict"] == "pass"
    assert "ok" not in report
    assert report["files"] == []
    assert report["required_gaps"] == []


def test_workspace_status_validation_prefixes_schema_gaps(monkeypatch, tmp_path):
    def fake_validate(schema_name, _payload, **_kwargs):
        return {
            "verdict": "block",
            "required_gaps": [f"{schema_name}:missing:branch"],
        }

    monkeypatch.setattr(prove, "validate_schema_instance", fake_validate)

    validation = prove.workspace_status_validation(tmp_path, {"branch": "dev"})

    assert validation["schema"] == "workspace-status.schema.json"
    assert validation["verdict"] == "block"
    assert "ok" not in validation
    assert prove.workspace_status_validation_gaps(validation) == (
        "workspace_status_schema:workspace-status.schema.json:missing:branch",
    )
