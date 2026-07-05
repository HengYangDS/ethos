from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.repository.policy import docstrings
from ethos.repository.policy.docstrings import docstring_coverage_report

if TYPE_CHECKING:
    from pathlib import Path


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_docstring_coverage_reports_public_surface_gaps(tmp_path: Path) -> None:
    _write(
        tmp_path / ".config/checks/docstrings/policy.toml",
        """
paths = ["packages/sample/src"]
fail_under = 75
exclude_roots = ["packages/sample/src/sample/generated"]
""".strip(),
    )
    _write(tmp_path / "packages/sample/src/sample/__init__.py", "")
    _write(
        tmp_path / "packages/sample/src/sample/cli.py",
        '''
from __future__ import annotations

@app.command
def documented():
    """Explain the command."""

@app.command(name="missing")
def missing():
    pass
''',
    )
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '''
__all__ = ["Exported", "exported"]

class Exported:
    """Documented export."""


def exported():
    pass


def internal():
    pass
''',
    )
    _write(
        tmp_path / "packages/sample/src/sample/generated/cli.py",
        """
@app.command
def ignored():
    pass
""",
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is False
    assert report["coverage_percent"] == 40.0
    assert report["documented_count"] == 2
    assert report["public_count"] == 5
    assert report["required_gaps"][0] == "docstring_coverage_below_minimum:40.00<75.00"
    missing = {item["qualified_name"] for item in report["missing"]}
    assert missing == {"sample", "sample.cli.missing", "sample.api.exported"}
    assert all("generated" not in item["path"] for item in report["missing"])


def test_docstring_coverage_defaults_to_clean_when_no_public_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/internal.py",
        """
def helper():
    pass
""",
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is True
    assert report["coverage_percent"] == 100.0
    assert report["public_count"] == 0
    assert report["required_gaps"] == []


def test_docstring_helpers_parse_module_names_and_decorators() -> None:
    assert docstrings._module_name("packages/ethos/src/ethos/repository/__init__.py") == (
        "ethos.repository"
    )
    assert docstrings._module_name("packages/ethos/src/ethos/cli.py") == "ethos.cli"
