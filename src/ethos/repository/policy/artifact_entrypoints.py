"""Generated-artifact producer entrypoint policy."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING
from typing import Any

from ethos.contracts.verdict import close_verdict

if TYPE_CHECKING:
    from pathlib import Path

_ENTRYPOINT_EXPLICIT_FILES = (
    ".gitlab-ci.yml",
    "package.json",
    "pyproject.toml",
    "system/tools.toml",
    ".config/checks/pytest/pytest.ini",
    "tools/ci/ci_templates.py",
    "tools/ci/architecture_projection.py",
)
_ENTRYPOINT_GLOB_PATTERNS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    ".config/ci/**/*.yml",
    ".config/ci/**/*.yaml",
    ".config/ci/**/*.toml",
    "tools/ci/scripts/*",
    ".githooks/*",
)
_DENIED_ENTRYPOINT_CACHE_TOKENS = (
    ".import_linter_cache",
    ".import-linter-cache",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".tox",
    ".nox",
    ".uv-cache",
)
_DENIED_ENTRYPOINT_HOME_TOKENS = (
    "build/cache/",
    "build/runtime/gitlab-ci-local",
    "dist/",
)
_RUNTIME_BOOTSTRAP_PATH = "tools/ci/scripts/with-python-runtime.sh"
_RETIRED_VENV_RUNTIME_MARKER = "build/runtime/venv"
_PYTHON_EXECUTION_PATTERN = re.compile(r"(?:^|[;&|()]|\s)(?:python(?:[0-9.]*)?)(?:\s|$)")
_PYTHON_BOOTSTRAP_EXEMPTIONS = frozenset(
    {
        "tools/ci/scripts/bootstrap-python.sh",
        "tools/ci/scripts/configure-git-checkout.sh",
    }
)
_SHELL_ASSIGNMENT_PATTERN = re.compile(
    r"^\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\"[^\"]*\"|'[^']*'|\S+)\s*$"
)
_OUT_DIR_PATTERN = re.compile(r"--out-dir\s+(?P<value>\"[^\"]*\"|'[^']*'|\S+)")
_SHELL_VARIABLE_PATTERN = re.compile(
    r"^(?:\"|')?\$(?:\{(?P<braced>[A-Za-z_][A-Za-z0-9_]*)\}|(?P<bare>[A-Za-z_][A-Za-z0-9_]*))(?:\"|')?$"
)
_PACKAGE_ARTIFACT_DIRECTORY_PATTERN = re.compile(r"(?:^|/)build/artifacts/[^/\s]+(?:/|$)")


def generated_artifact_entrypoint_audit(root: Path) -> dict[str, Any]:
    """Report whether active producer entrypoints route generated state semantically."""
    audits = [
        (rel, _entrypoint_findings(rel, path.read_text(encoding="utf-8", errors="replace")))
        for rel, path in _entrypoint_files(root)
    ]
    checked_files = [rel for rel, _ in audits]
    findings = sorted(
        (finding for _, audit_findings in audits for finding in audit_findings),
        key=lambda item: (item["path"], item["check"], item["required_gap"]),
    )
    required_gaps = sorted({finding["required_gap"] for finding in findings})
    return {
        "verdict": close_verdict("pass", required_gaps=tuple(required_gaps)),
        "state": "clean" if not required_gaps else "blocked",
        "summary": {
            "checked_file_count": len(checked_files),
            "finding_count": len(findings),
            "blocker_count": len(required_gaps),
        },
        "checked_files": checked_files,
        "findings": findings,
        "required_gaps": required_gaps,
    }


def _entrypoint_files(root: Path) -> list[tuple[str, Path]]:
    candidates = {rel: path for rel in _ENTRYPOINT_EXPLICIT_FILES if (path := root / rel).is_file()}
    candidates.update(
        (path.relative_to(root).as_posix(), path)
        for pattern in _ENTRYPOINT_GLOB_PATTERNS
        for path in root.glob(pattern)
        if path.is_file()
    )
    return sorted(candidates.items())


def _entrypoint_findings(rel: str, text: str) -> list[dict[str, str]]:
    active_text = "\n".join(_active_entrypoint_lines(text))
    producer_text = _entrypoint_producer_text(rel, text, active_text)
    return [
        *_denied_home_findings(rel, producer_text),
        *_tool_route_findings(rel, active_text, text),
    ]


def _entrypoint_producer_text(rel: str, text: str, active_text: str) -> str:
    if rel != "pyproject.toml":
        return active_text
    try:
        document = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return active_text
    tool = document.get("tool")
    pixi = tool.get("pixi") if isinstance(tool, dict) else None
    tasks = pixi.get("tasks") if isinstance(pixi, dict) else None
    if not isinstance(tasks, dict):
        return ""
    commands = (_structured_task_commands(task) for task in tasks.values())
    return "\n".join(command for group in commands for command in group)


def _structured_task_commands(task: object) -> list[str]:
    if isinstance(task, str):
        return [task]
    if isinstance(task, list):
        return [" ".join(str(argument) for argument in task)]
    if not isinstance(task, dict):
        return []
    for key in ("cmd", "command"):
        command = task.get(key)
        if isinstance(command, str):
            return [command]
        if isinstance(command, list):
            return [" ".join(str(argument) for argument in command)]
    return []


def _active_entrypoint_lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if (line := raw.strip()) and line[0] != "#"]


def _denied_home_findings(rel: str, active_text: str) -> list[dict[str, str]]:
    return [
        _entrypoint_finding(
            rel,
            check=check,
            boundary=boundary,
            required_gap=f"{gap_prefix}:{rel}:{marker}",
        )
        for line in active_text.splitlines()
        if not _is_cleanup_line(line)
        for check, boundary, gap_prefix, tokens in (
            (
                "denied-root-cache-home",
                "active entrypoints may not produce root tool cache homes",
                "generated_artifact_entrypoint_denied_root_cache",
                _DENIED_ENTRYPOINT_CACHE_TOKENS,
            ),
            (
                "denied-flat-generated-home",
                "active entrypoints may not produce flat or retired generated homes",
                "generated_artifact_entrypoint_denied_generated_home",
                _DENIED_ENTRYPOINT_HOME_TOKENS,
            ),
        )
        for marker in tokens
        if _contains_denied_home_token(line, marker)
    ]


def _tool_route_findings(rel: str, active: str, full_text: str) -> list[dict[str, str]]:
    if rel != ".gitlab-ci.yml" and not rel.startswith(("tools/", ".github/", ".githooks/")):
        return _pytest_config_findings(rel, active)
    producer_text = "\n".join(line for line in active.splitlines() if not _is_cleanup_line(line))
    return [
        *_pytest_config_findings(rel, active),
        *_runtime_bootstrap_findings(rel, producer_text),
        *_ruff_route_findings(rel, producer_text, full_text),
        *_import_linter_route_findings(rel, producer_text, full_text),
        *_pytest_runner_findings(rel, producer_text, full_text),
        *_package_build_route_findings(rel, producer_text),
        *_gitlab_local_route_findings(rel, producer_text),
    ]


def _runtime_bootstrap_findings(rel: str, producer_text: str) -> list[dict[str, str]]:
    """Reject executable Python/uv paths that evade the semantic bootstrap."""
    if rel == _RUNTIME_BOOTSTRAP_PATH:
        return []
    bootstrap_bound = "with-python-runtime.sh" in producer_text
    checks = (
        (
            _RETIRED_VENV_RUNTIME_MARKER in producer_text,
            "retired-venv-runtime",
            "active execution must use the checkout's single root .venv",
            "retired_venv_runtime",
        ),
        (
            "uv run" in producer_text and not bootstrap_bound,
            "uv-runtime-bootstrap",
            "active uv execution must route through the semantic runtime bootstrap",
            "uv_runtime_unbound",
        ),
        (
            rel not in _PYTHON_BOOTSTRAP_EXEMPTIONS
            and bool(_PYTHON_EXECUTION_PATTERN.search(producer_text))
            and not bootstrap_bound,
            "python-runtime-bootstrap",
            "active Python execution must route through the semantic runtime bootstrap",
            "python_runtime_unbound",
        ),
    )
    return [
        _entrypoint_finding(
            rel,
            check=check,
            boundary=boundary,
            required_gap=f"generated_artifact_entrypoint_{gap}:{rel}",
        )
        for applies, check, boundary, gap in checks
        if applies
    ]


def _pytest_config_findings(rel: str, active_text: str) -> list[dict[str, str]]:
    if (
        rel != ".config/checks/pytest/pytest.ini"
        or "cache_dir" not in active_text
        or "cache_dir = build/runtime/tool-cache/pytest" in active_text
    ):
        return []
    return [
        _entrypoint_finding(
            rel,
            check="pytest-cache-routing",
            boundary="pytest cache_dir must route to build/runtime/tool-cache/pytest",
            required_gap=f"generated_artifact_entrypoint_pytest_cache_unrouted:{rel}",
        )
    ]


def _ruff_route_findings(rel: str, producer_text: str, full_text: str) -> list[dict[str, str]]:
    if not (
        "ruff check" in producer_text or "ruff format" in producer_text or '"ruff"' in producer_text
    ) or ("--cache-dir" in producer_text or "RUFF_CACHE_DIR" in full_text):
        return []
    return [
        _entrypoint_finding(
            rel,
            check="ruff-cache-routing",
            boundary="Ruff runtime cache must route to build/runtime/tool-cache/ruff",
            required_gap=f"generated_artifact_entrypoint_ruff_cache_unrouted:{rel}",
        )
    ]


def _import_linter_route_findings(
    rel: str, producer_text: str, full_text: str
) -> list[dict[str, str]]:
    if "lint-imports" not in producer_text or (
        "--cache-dir" in producer_text
        or "IMPORT_LINTER_CACHE_DIR" in full_text
        or "build/runtime/tool-cache/import-linter" in producer_text
    ):
        return []
    return [
        _entrypoint_finding(
            rel,
            check="import-linter-cache-routing",
            boundary=(
                "import-linter runtime cache must route to build/runtime/tool-cache/import-linter"
            ),
            required_gap=(f"generated_artifact_entrypoint_import_linter_cache_unrouted:{rel}"),
        )
    ]


def _pytest_runner_findings(rel: str, producer_text: str, full_text: str) -> list[dict[str, str]]:
    if rel != "tools/ci/scripts/run-python-tests.sh" or "pytest" not in producer_text:
        return []
    required_routes = {
        "pytest-config": (
            'pytest_config_path=".config/checks/pytest/pytest.ini"',
            f"generated_artifact_entrypoint_pytest_config_unrouted:{rel}",
            "pytest must use the explicit .config/checks/pytest/pytest.ini owner",
        ),
        "pytest-config-argument": (
            '-c "${pytest_config_path}"',
            f"generated_artifact_entrypoint_pytest_config_argument_missing:{rel}",
            "pytest command must pass its explicit config owner",
        ),
        "coverage-evidence": (
            'COVERAGE_FILE="${coverage_evidence_dir}/.coverage"',
            f"generated_artifact_entrypoint_coverage_evidence_unrouted:{rel}",
            "coverage runtime data must route under build/evidence quality evidence",
        ),
        "pytest-basetemp": (
            '--basetemp="${pytest_tmp_dir}"',
            f"generated_artifact_entrypoint_pytest_basetemp_unrouted:{rel}",
            "pytest scratch work must route to an explicit temporary work directory",
        ),
    }
    return [
        _entrypoint_finding(rel, check=check, boundary=boundary, required_gap=gap)
        for check, (needle, gap, boundary) in required_routes.items()
        if needle not in full_text
    ]


def _package_build_route_findings(rel: str, producer_text: str) -> list[dict[str, str]]:
    assignments: dict[str, str] = {}
    findings: list[dict[str, str]] = []
    for line in producer_text.splitlines():
        if assignment := _SHELL_ASSIGNMENT_PATTERN.fullmatch(line):
            assignments[assignment["name"]] = assignment["value"]
            continue
        if (
            "uv build" in line or "hatch build" in line or "python -m build" in line
        ) and not _package_build_output_is_routed(line, assignments):
            findings.append(
                _entrypoint_finding(
                    rel,
                    check="package-artifact-routing",
                    boundary="local package builds must route to build/artifacts/<kind>",
                    required_gap=(
                        f"generated_artifact_entrypoint_package_artifacts_unrouted:{rel}"
                    ),
                )
            )
    return findings


def _package_build_output_is_routed(command: str, assignments: dict[str, str]) -> bool:
    match = _OUT_DIR_PATTERN.search(command)
    if match is None:
        return False
    output = match["value"]
    if reference := _SHELL_VARIABLE_PATTERN.fullmatch(output):
        name = reference["braced"] or reference["bare"]
        output = assignments.get(name, "")
    return bool(_PACKAGE_ARTIFACT_DIRECTORY_PATTERN.search(output.strip("\"'")))


def _gitlab_local_route_findings(rel: str, producer_text: str) -> list[dict[str, str]]:
    routed = "build/runtime/work/gitlab-ci-local" in producer_text
    if "gitlab-ci-local" not in producer_text or routed:
        return []
    return [
        _entrypoint_finding(
            rel,
            check="gitlab-local-state-routing",
            boundary="gitlab-ci-local state must route to build/runtime/work/gitlab-ci-local",
            required_gap=f"generated_artifact_entrypoint_gitlab_state_unrouted:{rel}",
        )
    ]


def _contains_denied_home_token(line: str, marker: str) -> bool:
    if marker not in line:
        return False
    if marker != "dist/":
        return True
    return line.startswith("dist/") or any(
        token in line
        for token in (
            " dist/",
            '"dist/',
            "'dist/",
            "=dist/",
            ":dist/",
            "(dist/",
            "[dist/",
            "./dist/",
            "${repo_root}/dist/",
            "$(pwd)/dist/",
            "${CI_PROJECT_DIR:-$(pwd)}/dist/",
        )
    )


def _is_cleanup_line(line: str) -> bool:
    return line.startswith(("rm -rf ", "rm -f ")) or "cleanup" in line.lower()


def _entrypoint_finding(
    path: str,
    *,
    check: str,
    boundary: str,
    required_gap: str,
) -> dict[str, str]:
    return {
        "path": path,
        "check": check,
        "boundary": boundary,
        "required_gap": required_gap,
    }
