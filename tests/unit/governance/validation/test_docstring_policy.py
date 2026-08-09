"""Public behavior coverage for the native docstring policy report."""

from __future__ import annotations

import textwrap
import tomllib
from typing import TYPE_CHECKING

import pytest

from ethos.repository.policy.docstrings.coverage import docstring_coverage_report

if TYPE_CHECKING:
    from pathlib import Path


def write_policy(
    root: Path, *, paths: tuple[str, ...] = ("src/sample",), style: str = "google"
) -> None:
    path = root / ".config" / "checks" / "docstrings" / "policy.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        f"paths = {list(paths)!r}\nfail_under = 100\nstyle = {style!r}\n"
        "check_structured_signature = true\n",
        encoding="utf-8",
    )


def write_python(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(source), encoding="utf-8")
    return path


def test_docstring_report_defaults_to_clean_when_public_surface_is_absent(tmp_path: Path) -> None:
    report = docstring_coverage_report(tmp_path)

    assert report == {
        "verdict": "pass",
        "state": "clean",
        "policy": ".config/checks/docstrings/policy.toml",
        "style": "google",
        "paths": ["src/ethos"],
        "fail_under": 95.0,
        "coverage_percent": 100.0,
        "documented_count": 0,
        "public_count": 0,
        "missing": [],
        "style_issue_count": 0,
        "style_issues": [],
        "required_gaps": [],
    }


def test_docstring_report_blocks_missing_package_and_command_docstrings(tmp_path: Path) -> None:
    write_policy(tmp_path)
    write_python(tmp_path, "src/sample/__init__.py", "value = 1\n")
    write_python(
        tmp_path,
        "src/sample/cli.py",
        """
        @app.command
        def status():
            return None
        """,
    )

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "block"
    assert report["coverage_percent"] == 0.0
    assert report["public_count"] == 2
    assert [item["kind"] for item in report["missing"]] == ["package_boundary", "function"]
    assert report["required_gaps"] == [
        "docstring_coverage_below_minimum:0.00<100.00",
        "public_docstring_missing:src/sample/__init__.py:sample",
        "public_docstring_missing:src/sample/cli.py:sample.cli.status",
    ]


def test_docstring_report_preserves_duplicate_configured_surface_observations(
    tmp_path: Path,
) -> None:
    write_policy(tmp_path, paths=("src/sample/__init__.py", "src/sample"))
    write_python(tmp_path, "src/sample/__init__.py", '"""Public package."""\n')

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["public_count"] == 2
    assert report["documented_count"] == 2


def test_docstring_report_exposes_native_google_style_failures(tmp_path: Path) -> None:
    write_policy(tmp_path)
    write_python(tmp_path, "src/sample/__init__.py", '"""Public package."""\n')
    write_python(
        tmp_path,
        "src/sample/cli.py",
        '''
        """Helper.

        Parameters:
            unused: Legacy module input.
        """

        @command()
        def publish(alpha, /, beta, *items, gamma, **options):
            """Publish artifacts:

            Args:
                alpha: First value.
                extra: Unknown value.
            """
        ''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["coverage_percent"] == 100.0
    assert report["verdict"] == "block"
    issues = {(item["qualified_name"], item["code"]) for item in report["style_issues"]}
    assert issues == {
        ("sample.cli", "weak_summary"),
        ("sample.cli", "unknown_section"),
        ("sample.cli.publish", "summary_colon"),
        ("sample.cli.publish", "args_missing"),
        ("sample.cli.publish", "args_extra"),
    }


def test_docstring_report_accepts_arguments_and_async_native_commands(tmp_path: Path) -> None:
    write_policy(tmp_path)
    write_python(tmp_path, "src/sample/__init__.py", '"""Public package."""\n')
    write_python(
        tmp_path,
        "src/sample/cli.py",
        '''
        """Public commands."""

        @app.command()
        async def inspect(value):
            """Inspect one value.

            Arguments:
                value: Value to inspect.
            """
        ''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["documented_count"] == report["public_count"] == 2


def test_docstring_report_does_not_apply_google_checks_to_native_other_style(
    tmp_path: Path,
) -> None:
    write_policy(tmp_path, style="numpy")
    write_python(tmp_path, "src/sample/__init__.py", '"""Helper."""\n')

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["style_issue_count"] == 0


def test_docstring_report_handles_root_module_and_non_command_decorators(tmp_path: Path) -> None:
    write_policy(tmp_path, paths=("commands.py",))
    write_python(
        tmp_path,
        "commands.py",
        '''
        """Root commands."""

        @route
        def ignored(value):
            """Ignore non-command decorators."""

        @status_command
        def status(value):
            """Report status without a structured argument section."""
        ''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "pass"
    assert report["public_count"] == 1
    assert report["documented_count"] == 1


def test_docstring_report_recognizes_legacy_fields_and_section_underlines(tmp_path: Path) -> None:
    write_policy(tmp_path)
    write_python(tmp_path, "src/sample/__init__.py", '"""Public package."""\n')
    write_python(
        tmp_path,
        "src/sample/cli.py",
        '''
        """Public commands."""

        @command
        def status(value):
            """Report status.

            :param value: Legacy value.

            Returns
            -------
            object
            """
        ''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "block"
    legacy = [item for item in report["style_issues"] if item["code"] == "legacy_style"]
    assert [item["message"] for item in legacy] == [
        "legacy docstring marker: :param",
        "legacy docstring marker: Returns",
    ]


def test_docstring_report_handles_blank_argument_lines_and_section_boundary(tmp_path: Path) -> None:
    write_policy(tmp_path)
    write_python(tmp_path, "src/sample/__init__.py", '"""Public package."""\n')
    write_python(
        tmp_path,
        "src/sample/cli.py",
        '''
        """Public commands."""

        @command
        def status(value):
            """Report status.

            Args:

                - value (str): Value to report.
            Boundary:
            """
        ''',
    )

    report = docstring_coverage_report(tmp_path)

    assert report["verdict"] == "block"
    assert not any(item["code"] == "args_missing" for item in report["style_issues"])
    assert any(item["code"] == "unknown_section" for item in report["style_issues"])


@pytest.mark.parametrize(
    ("relative", "contents", "error"),
    [
        (".config/checks/docstrings/policy.toml", "paths = [", tomllib.TOMLDecodeError),
        ("src/sample/__init__.py", '"""unterminated', SyntaxError),
    ],
)
def test_docstring_report_never_passes_malformed_native_inputs(
    tmp_path: Path, relative: str, contents: str, error: type[Exception]
) -> None:
    if not relative.endswith("policy.toml"):
        write_policy(tmp_path)
    write_python(tmp_path, relative, contents)

    with pytest.raises(error):
        docstring_coverage_report(tmp_path)
