"""Measure source accurately and validate prove-stage payloads."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import ethos.domain.prove as prove
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.measure import effective_code_lines_for_source
from tests.support.ethos_cli_runner import run_ethos_raw
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo

if TYPE_CHECKING:
    from pathlib import Path


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


@pytest.mark.parametrize("extra", [0, 1])
def test_size_gate_projects_the_paradigm_python_ceiling(tmp_path, extra: int) -> None:
    """The retained size gate reports exactly the paradigm's Python size gaps."""
    root = init_git_repo(tmp_path / "repo")
    ceiling = load_repository_paradigm().size.python_effective_lines
    module = root / "src/sample/module.py"
    module.parent.mkdir(parents=True)
    module.write_text("".join(f"value_{index} = {index}\n" for index in range(ceiling + extra)))
    git(root, "add", "src/sample/module.py")

    report = prove.code_size_report(root)

    expected = ["repository_paradigm_python_size:src/sample/module.py"] if extra else []
    assert report["required_gaps"] == expected
    assert report["verdict"] == ("block" if extra else "pass")


@pytest.mark.parametrize(
    "relative", ["src/logic.py", "src/product/surface/view.py", "tests/test_case.py"]
)
@pytest.mark.parametrize("tracked", [True, False], ids=["tracked", "new"])
def test_public_size_gate_enforces_uniform_ceiling(
    tmp_path: Path, relative: str, *, tracked: bool
) -> None:
    """The public gate uses the paradigm ceiling for every authored Python role."""
    root = init_git_repo(tmp_path / "repo")
    source = root / relative
    source.parent.mkdir(parents=True)
    limit = load_repository_paradigm().size.python_effective_lines
    for lines in (limit, limit + 1):
        source.write_text("value = 1\n" * lines, encoding="utf-8")
        if tracked:
            git(root, "add", relative)
        result = run_ethos_raw(
            "prove", "--host", "--execute", "--gate", "python-size", "--json", cwd=root
        )
        report = json.loads(result.stdout)
        observed = json.loads(report["data"]["checks"][0]["stdout"])["providers"][0]["report"]
        assert report["verdict"] == ("pass" if lines == limit else "block"), report
        assert observed["required_gaps"] == (
            [] if lines == limit else [f"repository_paradigm_python_size:{relative}"]
        )
        assert report["summary"]["proof_attestation_issued"] is False


def test_size_gate_does_not_certify_unavailable_inventory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failed native source inventory remains unknown rather than an empty pass."""

    def unavailable(*_args, **_options):
        message = "native inventory unavailable"
        raise OSError(message)

    monkeypatch.setattr(prove, "git_files", unavailable)
    report = prove.code_size_report(tmp_path)
    assert report["verdict"] == "unknown"
    assert report["required_gaps"] == ["code_size_inventory_unavailable"]


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
