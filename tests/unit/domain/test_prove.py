"""Measure source accurately and enforce public size and proof-policy boundaries."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import cast

import pytest

import ethos.domain.prove as prove
from ethos.measure import effective_code_lines_for_source
from ethos.repository.policy.rules.config import CodeSizePolicy
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


def _public_size_report(root: Path) -> tuple[dict, dict]:
    """Observe the declared size provider through the actual host CLI."""
    result = run_ethos_raw(
        "prove", "--host", "--execute", "--gate", "python-size", "--json", cwd=root
    )
    report = json.loads(result.stdout)
    observed = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]
    assert report["summary"]["proof_attestation_issued"] is False
    return report, observed


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ('"padding"; value = 1\n', 1),
        ('"文档"; 值 = 1\n', 1),
        ('"a\u2028b"; value = 1\n', 1),
        ('"a\u2029b"; value = 1\n', 1),
        ('"documentation"\r\nvalue = 1\r\n', 1),
        ('"documentation"\rvalue = 1\r', 1),
        ('def value(): "documentation"; return 1\n', 1),
        ('(\n "documentation"\n)\nvalue = 1\n', 1),
        ('payload = """first\n# literal data\nlast"""\n', 3),
        ('payload = """first\n\nlast"""\n', 3),
        ('payload = f"""first\n# {1 + 2}\nlast"""\n', 3),
        ('payload = f"""\n;\n{value}\n"""\n', 4),
        ('# comment\n"""documentation\nmore documentation"""\nvalue = 1 # inline\n', 1),
        ('"only a string";\n', 0),
    ],
)
def test_effective_lines_preserve_code_and_literal_data(source: str, expected: int) -> None:
    """Only syntax-classified non-code is excluded, never neighboring code or string data."""
    assert effective_code_lines_for_source(source) == expected


def test_invalid_python_is_not_a_valid_size_measurement() -> None:
    """Unparseable input cannot be certified by a fallback line counter."""
    with pytest.raises(SyntaxError):
        effective_code_lines_for_source("def invalid(\n")


@pytest.mark.parametrize(
    "relative",
    ["src/logic.py", "src/ethos/surface/cli/view.py", "tests/test_case.py"],
)
@pytest.mark.parametrize("tracked", [True, False], ids=["tracked", "new"])
def test_public_size_gate_enforces_uniform_ceiling(
    tmp_path: Path, relative: str, *, tracked: bool
) -> None:
    """Every admitted role, including new source, shares the 512-pass/513-reject boundary."""
    limit = 512
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_bytes((Path(__file__).resolve().parents[3] / ".ethos/rules.toml").read_bytes())
    source = root / relative
    source.parent.mkdir(parents=True)
    for lines in (limit, limit + 1):
        source.write_text("value = 1\n" * lines, encoding="utf-8")
        if tracked:
            git(root, "add", relative)
        report, observed = _public_size_report(root)
        assert report["verdict"] == ("pass" if lines == limit else "block"), report
        assert observed["default_effective_max_lines"] == limit
        assert {record["limit"] for record in observed["files"]} == {limit}
        assert not {"surface_effective_max_lines", "test_effective_max_lines"}.intersection(
            observed
        )
        assert observed["required_gaps"] == (
            [] if lines == limit else [f"code_size_exceeded:{relative}:{lines}>{limit}"]
        )


@pytest.mark.parametrize(
    "declaration",
    [
        "[quality.code_size",
        "quality = false\n",
        "[quality]\ncode_size = []\n",
        "[quality.code_size]\n",
        *(
            f"[quality.code_size]\ndefault_effective_max_lines = {value}\n"
            for value in ('"512"', "true", "512.0", "0", "-100", "550.5", "500", "513")
        ),
        '[quality.code_size]\ndefault_effective_max_lines = 512\nsurface_path_globs = "src/**"\n',
        '[quality.code_size]\ndefault_effective_max_lines = 512\nsurface_path_globs = [""]\n',
        "[quality.code_size]\ndefault_effective_max_lines = 512\nsurface_path_globs = [false]\n",
        "[quality.code_size]\ndefault_effective_max_lines = 512\ntest_effective_max_lines = 800\n",
        (
            "[quality.code_size]\ndefault_effective_max_lines = 512\n"
            "surface_effective_max_lines = 600\n"
        ),
        (
            "[quality.code_size]\ndefault_effective_max_lines = 512\n"
            'exemptions = ["src/oversized.py"]\n'
        ),
    ],
)
def test_public_size_gate_rejects_malformed_policy(tmp_path: Path, declaration: str) -> None:
    """Malformed or coercible limits cannot silently select defaults or weaken admission."""
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_text(declaration, encoding="utf-8")
    report, observed = _public_size_report(root)
    assert report["verdict"] == observed["verdict"] == "block", report
    assert observed["required_gaps"] == ["code_size_policy_invalid"]
    assert observed["errors"]
    assert "lane prewrite .ethos/rules.toml" in observed["next_action"]


def test_selected_size_gate_requires_its_declaration_without_inventing_limit(
    tmp_path: Path,
) -> None:
    """Selecting the gate requires its policy; generic compilation still invents no ceiling."""
    root = init_git_repo(tmp_path / "repo")
    (root / "large.py").write_text("value = 1\n" * 1_200, encoding="utf-8")
    git(root, "add", "large.py")
    report, observed = _public_size_report(root)
    assert prove.code_size_policy({}) is None
    assert report["verdict"] == observed["verdict"] == "block", report
    assert observed["state"] == "policy_missing"
    assert observed["files"] == []
    assert observed["required_gaps"] == ["code_size_policy_missing"]
    assert "default_effective_max_lines" not in observed
    assert "lane prewrite .ethos/rules.toml" in observed["next_action"]


def test_size_inventory_failure_is_unknown_with_original_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed native inventory cannot certify an empty successful source set."""
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_text("[quality.code_size]\ndefault_effective_max_lines = 512\n")

    def failed_inventory(_root: Path, *_arguments: str, **_options: object) -> object:
        raise subprocess.CalledProcessError(128, ("git", "ls-files"), "", "inventory failure\n")

    monkeypatch.setattr(prove.git_adapter, "run_git", failed_inventory)
    report = prove.code_size_report(root)
    assert report["verdict"] == "unknown", report
    assert report["state"] == "inventory_unavailable"
    assert report["files"] == []
    assert report["required_gaps"] == ["code_size_inventory_unavailable"]
    assert report["errors"][0]["stderr"] == "inventory failure\n"


@pytest.mark.parametrize("limit", [128, 256, 512])
def test_code_size_policy_declares_one_positive_native_unit_limit(limit: int) -> None:
    """The native schema owns one strict threshold in positive 128-line units."""
    declaration = {"default_effective_max_lines": limit}
    policy = CodeSizePolicy.model_validate(declaration)
    assert policy.model_dump(exclude_defaults=True) == declaration
    schema = CodeSizePolicy.model_json_schema()
    threshold = schema["properties"]["default_effective_max_lines"]
    if "$ref" in threshold:
        threshold = schema["$defs"][threshold["$ref"].rsplit("/", 1)[1]]
    assert threshold["type"] == "integer"
    assert (threshold["exclusiveMinimum"], threshold["multipleOf"]) == (0, 128)
    assert not {"surface_effective_max_lines", "test_effective_max_lines"}.intersection(
        schema["properties"]
    )


@pytest.mark.parametrize("content", [b"def invalid(\n", b"name = '\xff'\n"])
def test_public_size_gate_reports_invalid_source(tmp_path: Path, content: bytes) -> None:
    """Invalid syntax or encoding is a path-bound failure, never zero measured lines."""
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_text("[quality.code_size]\ndefault_effective_max_lines = 512\n")
    (root / "broken.py").write_bytes(content)
    git(root, "add", "broken.py")
    report, observed = _public_size_report(root)
    assert report["verdict"] == observed["verdict"] == "block", report
    assert observed["required_gaps"] == ["code_size_source_invalid:broken.py"]
    assert observed["errors"][0]["path"] == "broken.py"
    assert observed["files"] == []
    assert "lane prewrite broken.py" in observed["next_action"]


@pytest.mark.parametrize("boundary", ["policy", "source"])
def test_size_report_keeps_unavailable_observation_unknown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    """Inaccessible input cannot be reported as absent, invalid, or measured zero."""
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_text("[quality.code_size]\ndefault_effective_max_lines = 512\n")
    (root / "source.py").write_text("value = 1\n")
    git(root, "add", "source.py")

    def unavailable(_path: Path) -> int:
        message = "unreadable fixture"
        raise PermissionError(message)

    monkeypatch.setattr(
        prove, "load_rules_config" if boundary == "policy" else "effective_code_lines", unavailable
    )
    report = prove.code_size_report(root)
    assert report["verdict"] == "unknown", report
    assert report["required_gaps"] == [
        "code_size_policy_unavailable"
        if boundary == "policy"
        else "code_size_source_unavailable:source.py"
    ]
    assert report["files"] == []
    assert report["errors"]


def test_code_size_report_applies_declared_uniform_limit(tmp_path, monkeypatch):
    files = {
        "src/ethos/domain/small.py": "a=1\nb=2\n",
        "src/ethos/surface/cli/big.py": "value = 1\n" * 400,
        "tests/unit/test_big.py": "value = 1\n" * 600,
        "src/ethos/domain/oversized.py": "value = 1\n" * 385,
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
                    "default_effective_max_lines": 384,
                    "surface_path_globs": ["**/surface/**"],
                }
            }
        },
    )
    monkeypatch.setattr(
        prove.git_adapter, "git_files", lambda _root, *_patterns, **_options: tuple(files)
    )

    report = prove.code_size_report(tmp_path)
    records = cast("list[dict[str, object]]", report["files"])
    by_path = {record["path"]: record for record in records}

    assert by_path["src/ethos/domain/small.py"]["role"] == "logic"
    assert {record["limit"] for record in records} == {384}
    assert by_path["src/ethos/surface/cli/big.py"]["within_limit"] is False
    assert by_path["tests/unit/test_big.py"]["within_limit"] is False
    assert by_path["tests/unit/test_big.py"]["category"] == "test"
    oversized = by_path["src/ethos/domain/oversized.py"]
    assert oversized["limit"] == 384
    assert oversized["within_limit"] is False
    assert report["verdict"] == "block"
    assert report["required_gaps"] == [
        "code_size_exceeded:src/ethos/surface/cli/big.py:400>384",
        "code_size_exceeded:tests/unit/test_big.py:600>384",
        "code_size_exceeded:src/ethos/domain/oversized.py:385>384",
    ]
    assert "ok" not in report


def test_code_size_report_emits_gap_when_effective_lines_exceed_limit(tmp_path, monkeypatch):
    relative = "src/ethos/domain/too_big.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n" * 257, encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {"quality": {"code_size": {"default_effective_max_lines": 256}}},
    )
    monkeypatch.setattr(
        prove.git_adapter, "git_files", lambda _root, *_patterns, **_options: (relative,)
    )

    report = prove.code_size_report(tmp_path)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["code_size_exceeded:src/ethos/domain/too_big.py:257>256"]


def test_code_size_report_skips_deleted_tracked_paths(tmp_path, monkeypatch):
    relative = "src/ethos/domain/deleted.py"
    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {"quality": {"code_size": {"default_effective_max_lines": 256}}},
    )
    monkeypatch.setattr(
        prove.git_adapter, "git_files", lambda _root, *_patterns, **_options: (relative,)
    )

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
