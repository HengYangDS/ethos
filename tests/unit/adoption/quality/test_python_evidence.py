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
            lambda _root, _files: nullcontext({}),
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
    if native_layout == "relocated-mise":
        assert set(selected_tools) == {"python", "uv"}
        assert not (repo / ".venv").exists()


@pytest.mark.parametrize(
    ("axis", "session", "provider", "replay_name", "selected_paths"),
    [
        ("behavior", "tests", "behavior_report", "python_behavior_report", ["src/app.py"]),
        (
            "static-analysis",
            "quality",
            "static_report",
            "python_static_report",
            ["src/app.py", "tests/test_app.py"],
        ),
    ],
)
def test_python_verified_command_does_not_replay_without_native_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    axis: str,
    session: str,
    provider: str,
    replay_name: str,
    selected_paths: list[str],
) -> None:
    """Text-only success cannot justify a second test or static invocation."""
    repo = committed_source_repo(
        tmp_path,
        {
            "src/app.py": "def answer() -> int:\n    return 42\n",
            "tests/test_app.py": "def test_answer():\n    assert True\n",
        },
    )
    tree = subprocess.check_output(("git", "rev-parse", "HEAD^{tree}"), cwd=repo, text=True).strip()
    replays: list[Path] = []

    def replay(root: Path) -> dict[str, object]:
        replays.append(root)
        return {
            "verdict": "pass",
            "quality_evidence": {
                "axis": axis,
                "source_tree": tree,
                "selected_paths": selected_paths,
            },
        }

    monkeypatch.setattr(native_quality, replay_name, replay)
    command = ("nox", "-s", session)
    execution = NativeExecution(
        declared_identity=command,
        argv=command,
        cwd=repo,
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
    assert report["required_gaps"] == [f"quality_{axis}_python_native_evidence_unavailable"]
    assert replays == []


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
    monkeypatch.setattr(python_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        python_quality,
        "run_command",
        lambda *_args, **_kwargs: SimpleNamespace(stdout=stdout, returncode=returncode),
    )
    assert python_quality.static_report(tmp_path)["required_gaps"] == [gap]


@pytest.mark.parametrize("toolchain", ["product", "mise"])
def test_python_behavior_preserves_selected_locked_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, toolchain: str
) -> None:
    """Either locked entrypoint installs into one owned disposable environment."""
    native_mise = toolchain == "mise"
    if native_mise:
        (tmp_path / "mise.toml").write_text('[tools]\nuv = "0.12.18"\n', encoding="utf-8")
        (tmp_path / "mise.lock").write_text("[tools]\n", encoding="utf-8")
        monkeypatch.setattr(
            python_quality,
            "locked_environment",
            lambda _root, _files: nullcontext({"UV_PROJECT_ENVIRONMENT": str(tmp_path / ".venv")}),
        )
        monkeypatch.setattr(
            python_quality,
            "locked_tool",
            lambda _root, name, **_kwargs: Path(f"/native/{name}"),
        )

    def observe(_root: Path, command: tuple[str, ...], **options: object) -> None:
        removed = options["remove_env"]
        assert isinstance(removed, tuple)
        assert "UV_PROJECT_ENVIRONMENT" in removed
        environment = options["env"]
        assert isinstance(environment, dict)
        selected = environment["UV_PROJECT_ENVIRONMENT"]
        assert isinstance(selected, str)
        assert not Path(selected).is_relative_to(tmp_path)
        if native_mise:
            assert command[:6] == (
                "/native/uv",
                "run",
                "--locked",
                "--offline",
                "--python",
                "/native/python",
            )
            assert "--no-sync" not in command
        message = "observed"
        raise ValueError(message)

    monkeypatch.setattr(python_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        python_quality,
        "_behavior_scope",
        lambda _root, _paths: (("src/app.py",), ("tests/test_app.py",)),
    )
    monkeypatch.setattr(python_quality, "run_command", observe)
    assert python_quality.behavior_report(tmp_path)["required_gaps"] == [
        "quality_behavior_observed"
    ]


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
    monkeypatch.setattr(python_quality, "_source", lambda _root: ("a" * 40, ("src/app.py",)))
    monkeypatch.setattr(
        python_quality,
        "_behavior_scope",
        lambda _root, _paths: (("src/app.py",), ("tests/test_app.py",)),
    )
    assert python_quality.behavior_report(tmp_path)["required_gaps"] == [
        f"quality_behavior_{reason}"
    ]
