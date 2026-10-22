"""Verify Python quality evidence and preserve locked native execution."""

from __future__ import annotations

import shutil
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from uv import find_uv_bin

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.python_quality as python_quality
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.gates.verification import provider_reports
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize(
    ("native_layout", "outcome"),
    [("uv", "pass"), ("relocated-mise", "pass"), ("uv", "failure"), ("uv", "warning")],
)
def test_generic_provider_uses_real_locked_python_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_layout: str, outcome: str
) -> None:
    """Preserve one locked native attempt, its diagnostics and clean owned output."""
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    files = {
        **{name: (fixture / name).read_text() for name in ("pyproject.toml", "uv.lock")},
        "pytest.toml": '[pytest]\naddopts = ["--strict-config"]\ncache_dir = ".cache/pytest"\n',
        "src/sample/__init__.py": "def answer() -> int:\n    return 42\n",
        "tests/test_sample.py": "from pathlib import Path\n"
        + ("from warnings import warn\n" if outcome == "warning" else "")
        + "\nfrom sample import answer\n\n\ndef test_answer() -> None:\n"
        "    with (Path(__file__).parents[2] / 'runs').open('a') as output:\n"
        "        output.write('x')\n"
        "    print('native test diagnostic')\n"
        + (
            "    warn('native test warning', UserWarning, stacklevel=2)\n"
            if outcome == "warning"
            else ""
        )
        + f"    assert answer() == {43 if outcome == 'failure' else 42}\n",
    }
    selected_tools: list[str] = []
    if native_layout == "relocated-mise":
        files.update(
            {
                ".config/mise/config.toml": '[tools]\npython = "3.14.7"\nuv = "0.12.20"\n',
                ".config/mise/mise.lock": "",
            }
        )
        uv_executable = shutil.which("uv")
        assert uv_executable is not None

        def selected_tool(_root: Path, name: str, **_kwargs: object) -> Path:
            selected_tools.append(name)
            return Path(sys.executable if name == "python" else uv_executable)

        monkeypatch.setattr(
            python_quality,
            "locked_environment",
            lambda _root, _files: nullcontext({"UV_PROJECT_ENVIRONMENT": str(repo / ".venv")}),
        )
        monkeypatch.setattr(python_quality, "locked_tool", selected_tool)
    repo = committed_source_repo(tmp_path, files)
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", str(repo / ".venv"))
    with patch.object(python_quality, "run_command", wraps=python_quality.run_command) as run:
        report = native_quality.behavior_report(repo)
        assert run.call_count == 1
    assert report["verdict"] == ("pass" if outcome == "pass" else "block"), report
    retained = report["native"][0]
    assert native_layout != "uv" or retained["native"]["command"][0] == find_uv_bin()
    assert "VIRTUAL_ENV" not in retained["native"]["stderr"]
    assert retained["tests"]["total"] == 1
    assert retained["native"]["exit_code"] == (0 if outcome == "pass" else 1)
    assert retained["native"]["cwd"] == str(repo)
    if outcome != "pass":
        assert "native test diagnostic" in retained["native"]["stdout"]
    assert (tmp_path / "runs").read_text() == "x"
    assert native_quality.static_report(repo)["verdict"] == "pass"
    assert not any((repo / path).exists() for path in (".cache/pytest", ".venv"))
    if native_layout == "relocated-mise":
        assert set(selected_tools) == {"python", "uv"}


@pytest.mark.parametrize("admitted", [True, False], ids=["runtime-admitted", "runtime-excluded"])
def test_uv_project_runs_its_tests_on_an_interpreter_it_declares(
    tmp_path: Path, *, admitted: bool
) -> None:
    """Without mise, the runtime interpreter is pinned only when the project admits it."""
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    pyproject = (fixture / "pyproject.toml").read_text()
    if not admitted:
        pyproject = pyproject.replace(
            'requires-python = ">=3.12,<3.15"', 'requires-python = "==3.11.*"'
        )
    repo = committed_source_repo(
        tmp_path,
        {
            "pyproject.toml": pyproject,
            "uv.lock": (fixture / "uv.lock").read_text(),
            "src/sample/__init__.py": "def answer() -> int:\n    return 42\n",
            "tests/test_sample.py": "from sample import answer\n\n\ndef test_answer() -> None:\n"
            "    assert answer() == 42\n",
        },
    )
    report = native_quality.behavior_report(repo)
    command = report["native"][0]["native"]["command"]
    assert ("--python" in command) is admitted, command
    if admitted:
        assert command[command.index("--python") + 1] == sys.executable
        assert report["verdict"] == "pass", report


def test_generic_provider_counts_passing_subtests_from_native_events(tmp_path: Path) -> None:
    """Passing subtests count from pytest events that the JUnit parent omits."""
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    repo = committed_source_repo(
        tmp_path,
        {
            **{name: (fixture / name).read_text() for name in ("pyproject.toml", "uv.lock")},
            "src/sample/__init__.py": "def answer() -> int:\n    return 42\n",
            "tests/test_sample.py": "import unittest\n\nfrom sample import answer\n\n\n"
            "class SampleTests(unittest.TestCase):\n"
            "    def test_answers(self) -> None:\n"
            "        for value in (1, 2):\n"
            "            with self.subTest(value=value):\n"
            "                self.assertEqual(answer(), 42)\n",
        },
    )

    report = native_quality.behavior_report(repo)

    assert report["verdict"] == "pass", report
    assert report["native"][0]["tests"] == {
        "total": 3,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }


def test_generic_provider_binds_exercised_tooling_coverage(tmp_path: Path) -> None:
    """Tooling that tests execute binds to coverage without owing product coverage."""
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    repo = committed_source_repo(
        tmp_path,
        {
            **{name: (fixture / name).read_text() for name in ("pyproject.toml", "uv.lock")},
            ".gitattributes": "tools/** ethos-role=tooling\n",
            "src/sample/__init__.py": "def answer() -> int:\n    return 42\n",
            "tools/helper.py": "def double(value: int) -> int:\n    return value * 2\n",
            "tests/test_sample.py": "import runpy\nfrom pathlib import Path\n\n"
            "from sample import answer\n\n\ndef test_tool_doubles_answer() -> None:\n"
            "    tool = runpy.run_path(str(Path(__file__).parents[1] / 'tools/helper.py'))\n"
            "    assert tool['double'](answer()) == 84\n",
        },
    )

    report = native_quality.behavior_report(repo)

    assert report["verdict"] == "pass", report
    assert report["native"][0]["tests"]["total"] == 1


@pytest.mark.parametrize(
    ("axis", "session", "provider"),
    [
        ("behavior", "tests", "behavior_report"),
        ("static-analysis", "quality", "static_report"),
    ],
)
def test_python_verified_command_does_not_replay_without_native_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    axis: str,
    session: str,
    provider: str,
) -> None:
    """Text-only success cannot justify a second test or static invocation."""
    repo = committed_source_repo(
        tmp_path,
        {
            "src/app.py": "def answer() -> int:\n    return 42\n",
            "tests/test_app.py": "def test_answer():\n    assert True\n",
        },
    )

    def replay(*_args: object, **_kwargs: object) -> None:
        pytest.fail("an unsupported aggregate execution triggered another native tool")

    monkeypatch.setattr(python_quality, "run_command", replay)
    command = ("nox", "-s", session)
    execution = NativeExecution(
        declared_identity=command,
        argv=command,
        cwd=repo.resolve(),
        exit_code=0,
        stdout="55 passed in 7.52s\n" if session == "tests" else "All checks passed!\n",
        stderr="",
    )
    reports, verdict, _ = provider_reports(
        session,
        (f"ethos.adapters.gates.code_quality:{provider}",),
        repo,
        execution=execution,
    )
    assert verdict == "block"
    report = reports[0]["report"]
    assert isinstance(report, dict)
    expected_gap = (
        "quality_behavior_python_native_evidence_unavailable"
        if axis == "behavior"
        else "quality_static_python_native_selection_invalid"
    )
    assert report["required_gaps"] == [expected_gap]
    original = report["native"][0]["native"]
    assert original["stdout"] == execution.stdout
    assert original["stderr"] == execution.stderr


def test_native_quality_requires_committed_python_scope(tmp_path: Path) -> None:
    """No HEAD or selected Python file must not become an empty success."""
    untracked = tmp_path / "untracked"
    untracked.mkdir()
    assert python_quality.static_report(untracked)["required_gaps"] == [
        "quality_static_source_head_missing"
    ]

    repo = init_git_repo(tmp_path / "repo")
    assert python_quality.static_report(repo)["required_gaps"] == [
        "quality_static_python_sources_missing"
    ]


def test_native_behavior_requires_source_tests_and_a_lock(tmp_path: Path) -> None:
    """An unrecognized or unlocked scope cannot claim behavior coverage."""
    repo = init_git_repo(tmp_path / "repo")
    source = repo / "src/app.py"
    source.parent.mkdir()
    source.write_text("def answer(): return 42\n", encoding="utf-8")
    commit_fixture(repo, "add source without tests")
    assert python_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_scope_unrecognized"
    ]

    test = repo / "tests/test_app.py"
    test.parent.mkdir()
    test.write_text("def test_answer(): assert True\n", encoding="utf-8")
    commit_fixture(repo, "add tests without lock")
    assert python_quality.behavior_report(repo)["required_gaps"] == [
        "quality_behavior_locked_toolchain_missing"
    ]


@pytest.mark.parametrize(
    ("stdout", "returncode", "stderr", "gap"),
    [
        ("{", 0, "", "quality_static_report_invalid"),
        ("{}", 0, "", "quality_static_report_invalid"),
        ("[]", 1, "", "quality_static_diagnostics"),
        ('[{"code":"E999"}]', 1, "", "quality_static_diagnostics"),
        ("[]", 0, "native warning\n", "quality_static_diagnostics"),
        ("{", 0, "native warning\n", "quality_static_report_invalid"),
    ],
)
def test_native_static_adapter_distinguishes_report_from_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    returncode: int,
    stderr: str,
    gap: str,
) -> None:
    """A malformed tool report differs from a valid report containing findings."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = 42\n"})
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout=stdout, stderr=stderr, returncode=returncode
        ),
    )
    report = python_quality.static_report(repo)
    assert report["required_gaps"] == [gap]
    assert report["native"]["stdout"] == stdout
    assert report["native"]["stderr"] == stderr


@pytest.mark.parametrize(
    ("exit_code", "written", "reason"),
    [
        (0, (), "test_report_missing"),
        (1, (), "test_command_failed"),
        (0, ("--junitxml=",), "test_event_report_missing"),
        (1, ("--junitxml=",), "test_command_failed"),
    ],
)
def test_python_behavior_distinguishes_command_failure_from_missing_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exit_code: int,
    written: tuple[str, ...],
    reason: str,
) -> None:
    """A failed locked tool must not masquerade as a filesystem-only failure."""

    def run_command(_root: Path, command: tuple[str, ...], **_kwargs: object) -> SimpleNamespace:
        for argument in command:
            if argument.startswith(written):
                Path(argument.partition("=")[2]).write_text("<testsuites/>", encoding="utf-8")
        return SimpleNamespace(
            returncode=exit_code, stdout="native result\n", stderr="native diagnostic\n"
        )

    monkeypatch.setattr(python_quality, "run_command", run_command)
    repo = committed_source_repo(
        tmp_path,
        {
            "src/app.py": "answer = 42\n",
            "tests/test_app.py": "def test_answer(): assert True\n",
            "pyproject.toml": "[project]\nname = 'sample'\nversion = '0.1.0'\n",
            "uv.lock": "version = 1\n",
        },
    )
    report = python_quality.behavior_report(repo)
    assert report["required_gaps"] == [f"quality_behavior_{reason}"]
    assert report["native"]["stdout"] == "native result\n"
    assert report["native"]["stderr"] == "native diagnostic\n"
    assert report["native"]["exit_code"] == exit_code


@pytest.mark.parametrize("identity", ["exact", "base-binary", "bytecode-enabled"])
def test_python_static_reuses_exact_native_ruff_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    identity: str,
) -> None:
    """Reuse the native attempt once, distinguishing invocation from its base file."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = 42\n"})
    original = python_quality.static_report(repo)
    assert original["verdict"] == "pass", original
    native = original["native"]
    command = tuple(native["command"])
    executable = native["executable"]
    if identity == "bytecode-enabled":
        command = tuple(argument for argument in command if argument != "-B")
    if identity == "base-binary":
        executable = str(Path(executable).resolve())
        facts = subprocess.run(
            [executable, "-I", "-c", "import sys; print(sys.prefix)"],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        if Path(facts.stdout.strip()).resolve() == Path(sys.prefix).resolve():
            pytest.skip("the selected interpreter is not a distinct virtual environment")
    execution = NativeExecution(
        declared_identity=command,
        argv=command,
        cwd=repo.resolve(),
        exit_code=native["exit_code"],
        stdout=native["stdout"],
        stderr=native["stderr"],
        executable=executable,
    )

    def replay(*_args: object, **_kwargs: object) -> None:
        pytest.fail("verification replayed a completed native Ruff attempt")

    monkeypatch.setattr(python_quality, "run_command", replay)
    reports, verdict, _ = provider_reports(
        "static",
        ("ethos.adapters.gates.code_quality:static_report",),
        repo,
        execution=execution,
    )
    expected = "pass" if identity == "exact" else "block"
    assert verdict == expected, reports
    report = reports[0]["report"]
    retained = report["native"][0]["native"]
    assert retained["stdout"] == native["stdout"]
    assert retained["stderr"] == native["stderr"]
    if identity != "exact":
        gap = (
            "quality_static_python_native_selection_invalid"
            if identity == "bytecode-enabled"
            else "quality_static_python_native_toolchain_unbound"
        )
        assert report["required_gaps"] == [gap]


def test_python_static_cannot_waive_product_rules_with_inline_noqa(tmp_path: Path) -> None:
    """Repository-authored suppression cannot remove the product's prior obligation."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = missing_name  # noqa: F821\n"})
    report = python_quality.static_report(repo)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["quality_static_diagnostics"]
    assert "F821" in report["native"]["stdout"]


@pytest.mark.parametrize(("width", "verdict"), [(100, "pass"), (101, "block")])
def test_python_static_measures_lines_at_the_fleet_width(
    tmp_path: Path, width: int, verdict: str
) -> None:
    """Isolated product rules use the shared width, not Ruff's 88-column default."""
    line = "answer = " + "1" * (width - len("answer = "))
    repo = committed_source_repo(tmp_path, {"src/app.py": f"{line}\n"})

    report = python_quality.static_report(repo)

    assert report["verdict"] == verdict, report
    assert ("E501" in report["native"]["stdout"]) is (verdict == "block")


@pytest.mark.parametrize("changed_at", ["before", "after"])
def test_python_static_requires_exact_committed_bytes_before_and_after(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed_at: str
) -> None:
    """Native clean output cannot qualify a mutable substitute for selected source."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = 42\n"})
    source = repo / "src/app.py"
    if changed_at == "before":
        source.write_text("answer = 43\n")

    def observe(*_args: object, **_kwargs: object) -> SimpleNamespace:
        if changed_at == "after":
            source.write_text("answer = 43\n")
        return SimpleNamespace(stdout="[]", stderr="", returncode=0)

    monkeypatch.setattr(python_quality, "run_command", observe)
    report = python_quality.static_report(repo)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["quality_static_code_source_changed"]


@pytest.mark.parametrize("staged", [False, True])
def test_python_static_retains_deleted_committed_subjects(
    tmp_path: Path,
    *,
    staged: bool,
) -> None:
    """Removing an index entry cannot silently narrow the committed source obligation."""
    repo = committed_source_repo(
        tmp_path,
        {
            "src/app.py": "answer = 42\n",
            "src/other.py": "answer = 43\n",
        },
    )
    (repo / "src/app.py").unlink()
    if staged:
        subprocess.run(["git", "add", "src/app.py"], cwd=repo, check=True, timeout=15)
    report = python_quality.static_report(repo)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["quality_static_code_source_unavailable"]
