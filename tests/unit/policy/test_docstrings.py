from __future__ import annotations

from typing import TYPE_CHECKING

import ethos.repository.policy.docstrings.core as docstrings_core
from ethos.repository.policy.docstrings.core import docstring_coverage_report
from tests.support import write_text as _write

if TYPE_CHECKING:
    from pathlib import Path


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
    assert report["coverage_percent"] == 33.33
    assert report["documented_count"] == 1
    assert report["public_count"] == 3
    assert report["required_gaps"][0] == "docstring_coverage_below_minimum:33.33<75.00"
    missing = {item["qualified_name"] for item in report["missing"]}
    assert missing == {"sample", "sample.cli.missing"}
    assert all("generated" not in item["path"] for item in report["missing"])


def test_docstring_coverage_defaults_to_clean_when_no_public_surface(tmp_path: Path) -> None:
    _write(
        tmp_path / "packages/ethos/src/ethos/internal.py",
        """
def _helper():
    pass
""",
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is True
    assert report["coverage_percent"] == 100.0
    assert report["public_count"] == 0
    assert report["required_gaps"] == []


def test_docstring_helpers_parse_module_names_and_decorators() -> None:
    assert docstrings_core._module_name("packages/ethos/src/ethos/repository/__init__.py") == (
        "ethos.repository"
    )
    assert docstrings_core._module_name("packages/ethos/src/ethos/cli.py") == "ethos.cli"


def test_docstring_coverage_handles_file_paths_and_missing_roots(tmp_path: Path) -> None:
    _write(
        tmp_path / ".config/checks/docstrings/policy.toml",
        """
paths = ["packages/sample/src/sample/api.py", "packages/sample/src/missing"]
fail_under = 100
exclude_roots = []
""".strip(),
    )
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '''
def exported():
    """Documented export."""
''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is True
    assert report["public_count"] == 0
    assert report["documented_count"] == 0
    assert report["paths"] == [
        "packages/sample/src/sample/api.py",
        "packages/sample/src/missing",
    ]


def test_docstring_gate_rejects_legacy_and_mismatched_structured_docstrings(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / ".config/checks/docstrings/policy.toml",
        """
paths = ["packages/sample/src"]
fail_under = 100
style = "google"
check_structured_signature = true
exclude_roots = []
""".strip(),
    )
    _write(tmp_path / "packages/sample/src/sample/__init__.py", '"""Sample package."""\n')
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '''

def bad(value, *, mode):
    """Do something structured.

    Args:
        value: Input value.
        extra: Unknown argument.
    """
    return value


def legacy(value):
    """Legacy function.

    Parameters
    ----------
    value
        Input value.
    """
    return value
''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is False
    assert report["coverage_percent"] == 100.0
    assert report["style_issue_count"] == 3
    codes = {item["code"] for item in report["style_issues"]}
    assert {"args_missing", "args_extra", "legacy_style"} <= codes
    assert any("sample.api.bad:args_missing" in gap for gap in report["required_gaps"])


def test_docstring_gate_accepts_short_google_summary_without_structured_sections(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / ".config/checks/docstrings/policy.toml",
        """
paths = ["packages/sample/src"]
fail_under = 100
style = "google"
check_structured_signature = true
exclude_roots = []
""".strip(),
    )
    _write(tmp_path / "packages/sample/src/sample/__init__.py", '"""Sample package."""\n')
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '''

def concise(value):
    """Return the governed value."""
    return value
''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is True
    assert report["style_issue_count"] == 0
