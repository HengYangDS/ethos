"""Verify Python quality evidence and preserve locked native execution."""

from __future__ import annotations

import shutil
import subprocess
import sys
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

import ethos.adapters.gates.code_quality as native_quality
import ethos.adapters.gates.python_quality as python_quality
from ethos.adapters.gates.verification import NativeExecution
from ethos.adapters.gates.verification import provider_reports
from ethos.repository.policy.code_subjects import CodeSubject
from tests.support.governed_repository import commit_fixture
from tests.support.governed_repository import committed_source_repo
from tests.support.governed_repository import init_git_repo


@pytest.mark.parametrize("native_layout", ["uv", "relocated-mise"])
def test_generic_provider_uses_real_locked_python_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, native_layout: str
) -> None:
    """The generalized provider preserves Python's existing native success path."""
    repo = init_git_repo(tmp_path / "repo")
    fixture = Path(__file__).resolve().parents[3] / "fixtures/quality-sample"
    for name in ("pyproject.toml", "uv.lock"):
        (repo / name).write_bytes((fixture / name).read_bytes())
    selected_tools: list[str] = []
    monkeypatch.setenv("UV_PROJECT_ENVIRONMENT", str(repo / ".venv"))
    if native_layout == "relocated-mise":
        config = repo / ".config/mise/config.toml"
        config.parent.mkdir(parents=True)
        config.write_text('[tools]\npython = "3.14.7"\nuv = "0.12.20"\n')
        (config.parent / "mise.lock").write_text("")
        uv_executable = shutil.which("uv")
        assert uv_executable is not None

        def selected_tool(_root: Path, name: str, **_kwargs: object) -> Path:
            selected_tools.append(name)
            return Path(sys.executable if name == "python" else uv_executable)

        monkeypatch.setattr(
            python_quality,
            "locked_environment",
            lambda _root, _files: nullcontext({"UV_PROJECT_ENVIRONMENT": str(repo / ".venv")}),
            raising=False,
        )
        monkeypatch.setattr(python_quality, "locked_tool", selected_tool, raising=False)
    (repo / "pytest.toml").write_text(
        '[pytest]\naddopts = ["--strict-config"]\ncache_dir = ".cache/pytest"\n'
    )
    source = repo / "src/sample/__init__.py"
    source.parent.mkdir(parents=True)
    source.write_text("def answer() -> int:\n    return 42\n")
    test = repo / "tests/test_sample.py"
    test.parent.mkdir()
    test.write_text(
        "from sample import answer\n\n\ndef test_answer() -> None:\n    assert answer() == 42\n"
    )
    commit_fixture(repo, "lock native Python quality")

    for report in (native_quality.behavior_report(repo), native_quality.static_report(repo)):
        assert report["verdict"] == "pass", report["required_gaps"]
    assert not (repo / ".cache/pytest").exists()
    assert not (repo / ".venv").exists()
    if native_layout == "relocated-mise":
        assert set(selected_tools) == {"python", "uv"}


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
    ("stdout", "returncode", "gap"),
    [
        ("{", 0, "quality_static_report_invalid"),
        ("{}", 0, "quality_static_report_invalid"),
        ("[]", 1, "quality_static_diagnostics"),
        ('[{"code":"E999"}]', 1, "quality_static_diagnostics"),
    ],
)
def test_native_static_adapter_distinguishes_report_from_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    stdout: str,
    returncode: int,
    gap: str,
) -> None:
    """A malformed tool report differs from a valid report containing findings."""
    monkeypatch.setattr(
        python_quality,
        "observe_quality_subjects",
        lambda _root, **_kwargs: ("a" * 40, (CodeSubject("src/app.py", "python", is_test=False),)),
    )
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=stdout, stderr="", returncode=returncode),
    )
    assert python_quality.static_report(tmp_path)["required_gaps"] == [gap]


@pytest.mark.parametrize(
    ("exit_code", "reason"), [(0, "test_report_missing"), (1, "test_command_failed")]
)
def test_python_behavior_distinguishes_command_failure_from_missing_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exit_code: int, reason: str
) -> None:
    """A failed locked tool must not masquerade as a filesystem-only failure."""
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=exit_code, stdout="", stderr=""),
    )
    monkeypatch.setattr(
        python_quality,
        "observe_quality_subjects",
        lambda _root, **_kwargs: ("a" * 40, (CodeSubject("src/app.py", "python", is_test=False),)),
    )
    monkeypatch.setattr(
        python_quality,
        "_behavior_scope",
        lambda _root, _paths: (("src/app.py",), ("tests/test_app.py",)),
    )
    assert python_quality.behavior_report(tmp_path)["required_gaps"] == [
        f"quality_behavior_{reason}"
    ]


@pytest.mark.parametrize("identity", ["exact", "base-binary"])
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
        assert report["required_gaps"] == ["quality_static_python_native_toolchain_unbound"]


def test_python_static_cannot_waive_product_rules_with_inline_noqa(tmp_path: Path) -> None:
    """Repository-authored suppression cannot remove the product's prior obligation."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = missing_name  # noqa: F821\n"})
    report = python_quality.static_report(repo)
    assert report["verdict"] == "block"
    assert report["required_gaps"] == ["quality_static_diagnostics"]
    assert "F821" in report["native"]["stdout"]


@pytest.mark.parametrize("stdout", ["[]", "{"])
def test_python_static_preserves_native_warning_and_invalid_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stdout: str
) -> None:
    """A zero native exit cannot hide stderr or discard an invalid diagnostic stream."""
    repo = committed_source_repo(tmp_path, {"src/app.py": "answer = 42\n"})
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(
            stdout=stdout,
            stderr="native warning\n",
            returncode=0,
        ),
    )
    report = python_quality.static_report(repo)
    assert report["verdict"] == "block"
    assert report["native"]["stdout"] == stdout
    assert report["native"]["stderr"] == "native warning\n"


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
