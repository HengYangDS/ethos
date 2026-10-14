"""Measure source accurately and validate prove-stage payloads."""

from __future__ import annotations

import pytest

import ethos.domain.prove as prove
from ethos.contracts.paradigm.declaration import load_repository_paradigm
from ethos.measure import effective_code_lines_for_source
from tests.support.governed_repository import git
from tests.support.governed_repository import init_git_repo


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
