from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

import ethos.domain.prove as prove
from ethos.measure import effective_code_lines_for_source
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
        report, observed = _public_size_report(root)
        assert report["verdict"] == ("pass" if lines == limit else "block"), report
        assert observed["default_effective_max_lines"] == 500
        assert observed["surface_effective_max_lines"] == 500
        assert observed["test_effective_max_lines"] == 800
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
            for value in ('"500"', "true", "500.0", "0", "-100", "550")
        ),
        '[quality.code_size]\ndefault_effective_max_lines = 500\nsurface_path_globs = "src/**"\n',
        '[quality.code_size]\ndefault_effective_max_lines = 500\nsurface_path_globs = [""]\n',
        "[quality.code_size]\ndefault_effective_max_lines = 500\nsurface_path_globs = [false]\n",
        "[quality.code_size]\ndefault_effective_max_lines = 500\ntest_effective_max_lines = true\n",
        (
            "[quality.code_size]\ndefault_effective_max_lines = 500\n"
            "surface_effective_max_lines = 550\n"
        ),
        (
            "[quality.code_size]\ndefault_effective_max_lines = 500\n"
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


def test_public_size_gate_does_not_invent_an_undeclared_limit(tmp_path: Path) -> None:
    """A generic repository without the optional declaration acquires no hidden ceiling."""
    root = init_git_repo(tmp_path / "repo")
    (root / "large.py").write_text("value = 1\n" * 1_200, encoding="utf-8")
    git(root, "add", "large.py")
    report, observed = _public_size_report(root)
    assert report["verdict"] == "pass", report
    assert observed["state"] == "not_configured"
    assert observed["files"] == []
    assert observed["required_gaps"] == []


@pytest.mark.parametrize("content", [b"def invalid(\n", b"name = '\xff'\n"])
def test_public_size_gate_reports_invalid_source(tmp_path: Path, content: bytes) -> None:
    """Invalid syntax or encoding is a path-bound failure, never zero measured lines."""
    root = init_git_repo(tmp_path / "repo")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir()
    rules.write_text("[quality.code_size]\ndefault_effective_max_lines = 500\n")
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
    rules.write_text("[quality.code_size]\ndefault_effective_max_lines = 500\n")
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


def test_code_size_report_applies_declared_role_limits(tmp_path, monkeypatch):
    files = {
        "src/ethos/domain/small.py": "a=1\nb=2\n",
        "src/ethos/surface/cli/big.py": "value = 1\n" * 400,
        "tests/unit/test_big.py": "value = 1\n" * 600,
        # An over-limit logic file is held to its role limit — there is no way to
        # exempt it, so it fails.
        "src/ethos/domain/oversized.py": "value = 1\n" * 301,
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
                    "default_effective_max_lines": 300,
                    "surface_effective_max_lines": 500,
                    "test_effective_max_lines": 800,
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
    assert by_path["src/ethos/domain/small.py"]["limit"] == 300
    assert by_path["src/ethos/surface/cli/big.py"]["limit"] == 500
    assert by_path["tests/unit/test_big.py"]["limit"] == 800
    assert by_path["tests/unit/test_big.py"]["category"] == "test"
    # An oversized logic file is held to its role limit (300) and therefore fails —
    # no per-file escape hatch exists.
    oversized = by_path["src/ethos/domain/oversized.py"]
    assert oversized["limit"] == 300
    assert oversized["within_limit"] is False
    assert report["verdict"] == "block"
    assert "ok" not in report


def test_code_size_report_emits_gap_when_effective_lines_exceed_limit(tmp_path, monkeypatch):
    relative = "src/ethos/domain/too_big.py"
    path = tmp_path / relative
    path.parent.mkdir(parents=True)
    path.write_text("value = 1\n" * 201, encoding="utf-8")
    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {"quality": {"code_size": {"default_effective_max_lines": 200}}},
    )
    monkeypatch.setattr(prove.git_adapter, "git_files", lambda _root, *_patterns: (relative,))

    report = prove.code_size_report(tmp_path)

    assert report["verdict"] == "block"
    assert "ok" not in report
    assert report["required_gaps"] == ["code_size_exceeded:src/ethos/domain/too_big.py:201>200"]


def test_code_size_report_skips_deleted_tracked_paths(tmp_path, monkeypatch):
    relative = "src/ethos/domain/deleted.py"
    monkeypatch.setattr(
        prove,
        "load_rules_config",
        lambda _root: {"quality": {"code_size": {"default_effective_max_lines": 200}}},
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
