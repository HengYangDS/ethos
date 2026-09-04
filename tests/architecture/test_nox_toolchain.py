from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from tools.ci import sessions

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[2]


def _declared_nox_sessions() -> set[str]:
    declaration = tomllib.loads((ROOT / "system/gates.toml").read_text(encoding="utf-8"))
    return {
        str(command[-1])
        for item in declaration["gates"]
        if (command := item.get("command", [])) and "nox" in command and "-s" in command
    }


def test_noxfile_is_only_a_projection_of_repository_sessions() -> None:
    source = (ROOT / "noxfile.py").read_text(encoding="utf-8")
    assert "sessions.PUBLIC_SESSIONS" in source
    assert "system/gates.toml" not in source
    assert "timeout" not in source
    assert not (ROOT / "tools/ci/registry.py").exists()
    assert not (ROOT / "tools/ci/runner.py").exists()


def test_machine_declared_nox_gates_are_implemented_by_sessions() -> None:
    public = set(sessions.PUBLIC_SESSIONS)
    assert _declared_nox_sessions() <= public
    assert all(callable(getattr(sessions, name)) for name in public)


def test_session_projection_names_are_unique() -> None:
    assert len(sessions.PUBLIC_SESSIONS) == len(set(sessions.PUBLIC_SESSIONS))


def test_project_runtime_is_the_only_executable_resolution_owner() -> None:
    consumers = (
        "tools/ci/sessions.py",
        "tools/ci/dependency_hygiene.py",
        "tools/ci/delivery/acceptance/effect.py",
        "tools/ci/delivery/pipeline.py",
    )
    for relative in consumers:
        assert "tools.ci.toolchain.environment" in (ROOT / relative).read_text(encoding="utf-8")


def test_pytest_git_environment_is_hermetic() -> None:
    count = int(os.environ["GIT_CONFIG_COUNT"])
    entries = tuple(
        (os.environ[f"GIT_CONFIG_KEY_{index}"], os.environ[f"GIT_CONFIG_VALUE_{index}"])
        for index in range(count)
    )

    assert ("core.fsmonitor", "false") in entries
    assert len([key for key, _value in entries if key == "init.templateDir"]) == 1
    assert not {"user.name", "user.email"} & {key for key, _value in entries}
    assert all(value for _key, value in entries)
    assert os.environ["GIT_AUTHOR_NAME"] == "ETHOS Test"
    assert os.environ["GIT_AUTHOR_EMAIL"] == "test@example.invalid"
    assert os.environ["GIT_COMMITTER_NAME"] == "ETHOS Test"
    assert os.environ["GIT_COMMITTER_EMAIL"] == "test@example.invalid"
    assert os.environ["GIT_CONFIG_GLOBAL"] == os.devnull
    assert os.environ["GIT_CONFIG_NOSYSTEM"] == "1"
    assert os.environ["GIT_TERMINAL_PROMPT"] == "0"


def test_lint_inventory_excludes_deleted_worktree_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alive = tmp_path / "alive.py"
    alive.write_text("value = 1\n", encoding="utf-8")
    calls: list[tuple[object, ...]] = []

    class Session:
        def run(self, *args, **_kwargs):
            calls.append(args)
            return "alive.py\0deleted.py\0" if args[:2] == ("git", "ls-files") else ""

    monkeypatch.setattr(sessions, "ROOT", tmp_path)
    monkeypatch.setattr(sessions, "RUFF_CACHE", tmp_path / ".ruff-cache")
    sessions.lint(Session())

    assert all("alive.py" in call for call in calls[1:])
    assert all("deleted.py" not in call for call in calls[1:])


def test_prose_executor_consumes_only_declared_policy_paths() -> None:
    calls = []
    sessions.prose(type("Session", (), {"run": lambda _, *args: calls.append(args)})())
    expected = [sessions.RUNTIME.script("codespell"), "--toml"]
    expected += [str(ROOT / ".config/checks/prose/codespell.toml"), "--count"]
    expected += ["--quiet-level=2", "README.md", "CONTRIBUTING.md", "AGENTS.md"]
    assert calls[0] == (*expected, "docs", "rules", "openspec/specs")
