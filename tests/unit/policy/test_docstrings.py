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
        '\npaths = ["packages/sample/src"]\nfail_under = 75\nexclude_roots = ["packages/sample/src/sample/generated"]\n'.strip(),
    )
    _write(tmp_path / "packages/sample/src/sample/__init__.py", "")
    _write(
        tmp_path / "packages/sample/src/sample/cli.py",
        '\nfrom __future__ import annotations\n\n@app.command\ndef documented():\n    """Explain the command."""\n\n@app.command(name="missing")\ndef missing():\n    pass\n',
    )
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '\nclass Exported:\n    """Documented export."""\n\n\ndef exported():\n    pass\n\n\ndef internal():\n    pass\n',
    )
    _write(
        tmp_path / "packages/sample/src/sample/generated/cli.py",
        "\n@app.command\ndef ignored():\n    pass\n",
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
        "\ndef _helper():\n    pass\n",
    )
    _write(
        tmp_path / "packages/ethos/src/ethos/decorated.py",
        "\n@1\ndef ignored():\n    pass\n",
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
        '\npaths = ["packages/sample/src/sample/api.py", "packages/sample/src/missing"]\nfail_under = 100\nexclude_roots = []\n'.strip(),
    )
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '\ndef exported():\n    """Documented export."""\n',
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
        '\npaths = ["packages/sample/src"]\nfail_under = 100\nstyle = "google"\ncheck_structured_signature = true\nexclude_roots = []\n'.strip(),
    )
    _write(tmp_path / "packages/sample/src/sample/__init__.py", '"""Sample package."""\n')
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '\n\ndef bad(value, *, mode):\n    """Do something structured.\n\n    Args:\n        value: Input value.\n        extra: Unknown argument.\n    """\n    return value\n\n\ndef legacy(value):\n    """Legacy function.\n\n    Parameters\n    ----------\n    value\n        Input value.\n    """\n    return value\n',
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
        '\npaths = ["packages/sample/src"]\nfail_under = 100\nstyle = "google"\ncheck_structured_signature = true\nexclude_roots = []\n'.strip(),
    )
    _write(tmp_path / "packages/sample/src/sample/__init__.py", '"""Sample package."""\n')
    _write(
        tmp_path / "packages/sample/src/sample/api.py",
        '\n\ndef concise(value):\n    """Return the governed value."""\n    return value\n',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["ok"] is True
    assert report["style_issue_count"] == 0
