from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AUDIT_PATH = ROOT / "tools" / "ci" / "local_state_audit.py"


def _load_audit_module() -> object:
    spec = importlib.util.spec_from_file_location("ethos_test_local_state_audit", AUDIT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _init_repo(repo: Path) -> None:
    _git(repo, "init")
    _git(repo, "config", "user.email", "ethos@example.invalid")
    _git(repo, "config", "user.name", "ETHOS Test")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / ".gitignore").write_text(
        "build/\n.cache/\n__pycache__/\n*.pyc\n",
        encoding="utf-8",
    )
    _git(repo, "add", ".gitignore")
    _git(repo, "commit", "-m", "initialize ignored local state policy")


def test_ignored_untracked_state_lists_gitignored_local_state(tmp_path: Path) -> None:
    """Report ignored runtime state instead of hiding it behind --exclude-standard."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    for rel in (
        "build/evidence/local-state/audit.json",
        ".cache/local-state/worktree/leases.json",
        "packages/ethos/src/ethos/__pycache__/core.cpython-313.pyc",
    ):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ignored local state\n", encoding="utf-8")

    audit = _load_audit_module()

    ignored = audit.ignored_untracked_state(
        repo,
        ["build/", ".cache/", "__pycache__/"],
    )

    assert ignored == [
        ".cache/local-state/worktree/leases.json",
        "build/evidence/local-state/audit.json",
        "packages/ethos/src/ethos/__pycache__/core.cpython-313.pyc",
    ]


def test_ignored_untracked_state_excludes_dependency_environment_caches(
    tmp_path: Path,
) -> None:
    """Keep third-party installation trees out of the local-state signal."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    for rel in (
        ".venv/lib/python3.13/site-packages/__pycache__/pytest.cpython-313.pyc",
        "node_modules/pkg/__pycache__/module.cpython-313.pyc",
        "packages/ethos/src/ethos/__pycache__/core.cpython-313.pyc",
    ):
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ignored local state\n", encoding="utf-8")

    audit = _load_audit_module()

    ignored = audit.ignored_untracked_state(
        repo,
        ["build/", ".cache/", "node_modules/", "__pycache__/"],
    )

    assert ignored == ["packages/ethos/src/ethos/__pycache__/core.cpython-313.pyc"]


def test_forbidden_tracked_state_flags_nested_cache_directories() -> None:
    """A forced tracked __pycache__ artifact is never durable repository truth."""
    audit = _load_audit_module()
    tracked = [
        "packages/ethos/src/ethos/__pycache__/core.cpython-313.pyc",
        "build/evidence/local-state/audit.json",
        "src/app.py",
    ]

    forbidden = audit.forbidden_tracked_state(
        tracked,
        ["build/", ".cache/", "node_modules/", "__pycache__/"],
        allowed_placeholders=set(),
    )

    assert forbidden == [
        {
            "path": "packages/ethos/src/ethos/__pycache__/core.cpython-313.pyc",
            "reason": "generated or host-local state is tracked",
        },
        {
            "path": "build/evidence/local-state/audit.json",
            "reason": "generated or host-local state is tracked",
        },
    ]
