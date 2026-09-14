"""Native budget-policy fixtures and controlled external counter observations."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import ethos.domain.source_budget.measurement as source_budget
from tests.support.governed_repository import git
from tests.support.subprocesses import completed as cp

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


def write_budget_selection(
    root: Path,
    *,
    terminal: tuple[int, int, int, int, int] = (1_000, 1_000, 1_000, 1_000, 2_000),
    tolerance: tuple[int, int] = (100, 200),
) -> Path:
    path = root / ".config/checks/format/selection.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "[source_budget]\n"
        "terminal = { "
        f"python_product = {terminal[0]}, python_tests = {terminal[1]}, "
        f"python_tools = {terminal[2]}, python_other = {terminal[3]}, "
        f"global_total = {terminal[4]} }}\n"
        f"""immutable_record_roots = ["openspec/changes/archive/"]
line_width = 100

[source_budget.cross_check]
command = "fake-scc"
args = ["--format", "json2", "--exclude-file=__never__"]
timeout_seconds = 5
tolerance = {{ python_total = {tolerance[0]}, global_total = {tolerance[1]} }}

[source_budget.aggregates]
python_total = ["python_product", "python_tests", "python_tools", "python_other"]
global_total = [
  "python_product", "python_tests", "python_tools", "python_other",
  "toml", "json", "yaml", "ini", "shell",
]

[[format]]
extensions = [".lock", ".json", ".yaml", ".yml"]
[[format.budget]]
category = "dependency_resolution"
paths = [
  "*.lock", "**/*.lock", "*-lock.json", "**/*-lock.json",
  "*-lock.yaml", "**/*-lock.yaml", "*-lock.yml", "**/*-lock.yml",
  "npm-shrinkwrap.json", "**/npm-shrinkwrap.json",
]
accounting = "generated_evidence"

[[format]]
extensions = [".py"]
budget = [
  {{ category = "python_product", paths = ["src/*"], measure = "python_ast" }},
  {{ category = "python_tests", paths = ["tests/*"], measure = "python_ast" }},
  {{ category = "python_tools", paths = ["tools/*"], measure = "python_ast" }},
  {{ category = "python_other", measure = "python_ast" }},
]

[[format]]
extensions = [".toml"]
budget = [{{ category = "toml", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".json"]
budget = [{{ category = "json", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".yaml", ".yml"]
budget = [{{ category = "yaml", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".ini", ".cfg"]
budget = [{{ category = "ini", measure = "structured", baseline_measure = "lines" }}]

[[format]]
extensions = [".sh"]
shebangs = ["sh", "bash", "zsh"]
budget = [
  {{ category = "shell", comment_prefixes = ["#"] }},
]
""",
        encoding="utf-8",
    )
    return path


def budget_repository(
    root: Path,
    *,
    terminal: tuple[int, int, int, int, int] = (1_000, 1_000, 1_000, 1_000, 2_000),
    tolerance: tuple[int, int] = (100, 200),
) -> tuple[Path, Path]:
    selection = write_budget_selection(root, terminal=terminal, tolerance=tolerance)
    source = root / "src/ethos/demo.py"
    source.parent.mkdir(parents=True)
    source.write_text('''"""Not executable."""\nFIRST = 1\nSECOND = 2\n''', encoding="utf-8")
    rules = root / ".ethos/rules.toml"
    rules.parent.mkdir(parents=True)
    rules.write_text(
        "[quality.source_budget.terminal]\n"
        f"python_product = {terminal[0]}\n"
        f"python_tests = {terminal[1]}\n"
        f"python_tools = {terminal[2]}\n"
        f"python_other = {terminal[3]}\n"
        f"global_total = {terminal[4]}\n",
        encoding="utf-8",
    )
    git(root, "init", "-q", "-b", "dev")
    git(root, "add", ".")
    git(
        root,
        "commit",
        "-qm",
        "baseline",
    )
    return selection, source


def fake_scc(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    counts: dict[str, int] | None = None,
    *,
    include_all: bool = True,
) -> None:
    """Expose an external cross-check fixture through the report boundary."""
    expected = counts or {}
    run = source_budget.subprocess.run
    which = source_budget.shutil.which

    def payload() -> str:
        completed = run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            text=True,
            capture_output=True,
            check=True,
        )
        paths = completed.stdout.splitlines()
        if not include_all:
            paths = [path for path in paths if path in expected]
        return json.dumps(
            {
                "languageSummary": [
                    {
                        "Name": "fixture",
                        "Files": [
                            {
                                "Location": (root / path).as_posix(),
                                "Code": expected.get(path, 0),
                            }
                            for path in paths
                        ],
                    }
                ]
            }
        )

    def dispatch(command, **kwargs):
        if command[0] == "/fake-scc":
            assert "--exclude-file=__never__" in command
            return cp(stdout=payload(), command="scc")
        return run(command, **kwargs)

    monkeypatch.setattr(
        source_budget.shutil,
        "which",
        lambda command, **kwargs: (
            "/fake-scc" if command == "fake-scc" else which(command, **kwargs)
        ),
    )
    monkeypatch.setattr(source_budget.subprocess, "run", dispatch)


def measure_budget(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    counts: dict[str, int] | None = None,
    *,
    include_all: bool = True,
) -> source_budget.SourceBudgetReport:
    fake_scc(monkeypatch, root, counts, include_all=include_all)
    return source_budget.source_budget_report(root)


def tracked_budget_file(
    root: Path,
    relative: str,
    content: str,
    *,
    executable: bool = False,
) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    git(root, "add", path.as_posix())
    return path
