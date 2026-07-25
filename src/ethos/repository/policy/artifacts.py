"""Generated artifact topology audit."""

from __future__ import annotations

import re
import subprocess
import tomllib
from os import walk
from pathlib import Path
from typing import Any

from ethos.contracts.artifacts.topology import GeneratedArtifactTopologyDeclaration
from ethos.contracts.artifacts.topology import generated_artifact_contract
from ethos.contracts.artifacts.topology import load_generated_artifact_topology_declaration
from ethos.contracts.artifacts.topology import path_policy_from_declaration

_ROOT_TEST_RESIDUE_FILENAMES = frozenset({".coverage", "coverage.xml", "junit.xml"})
_ROOT_TEST_RESIDUE_PREFIXES = (".coverage.",)


_PRUNE_DIRS = frozenset({".git", ".pixi", ".venv", "__pycache__", "node_modules"})

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
_ROOT_VENV_RUNTIME_TOKEN = ".venv/bin/python"
_PYTHON_EXECUTION_PATTERN = re.compile(r"(?:^|[;&|()]|\s)(?:python(?:[0-9.]*)?)(?:\s|$)")
_PYTHON_BOOTSTRAP_EXEMPTIONS = frozenset(
    {
        "tools/ci/scripts/bootstrap-python.sh",
        "tools/ci/scripts/configure-git-checkout.sh",
    }
)


def generated_artifact_topology_report(root: Path) -> dict[str, Any]:
    """Report generated artifact placement drift without mutating the repository."""
    declaration = load_generated_artifact_topology_declaration(
        root / "system/policies/generated-artifact-topology.toml"
    )
    allowed_paths: list[str] = []
    denied_paths: list[str] = []
    review_paths: list[str] = []
    ignored_local_paths: list[str] = []
    review_gaps: list[str] = []
    path_blockers: list[str] = []

    for path in _candidate_paths(root, declaration):
        rel = path.relative_to(root).as_posix()
        if _is_ignored_local_test_residue(root, rel):
            ignored_local_paths.append(rel)
            continue

        policy = path_policy_from_declaration(rel, declaration)
        decision = str(policy["decision"])
        if decision == "allow":
            allowed_paths.append(rel)
        elif decision == "review":
            review_paths.append(rel)
            review_gap = str(policy.get("required_gap") or "")
            if review_gap:
                review_gaps.append(review_gap)
        elif decision == "deny":
            denied_paths.append(rel)
            required_gap = str(policy.get("required_gap") or "")
            if required_gap:
                path_blockers.append(required_gap)

    entrypoint_audit = generated_artifact_entrypoint_audit(root)
    entrypoint_blockers = [str(gap) for gap in entrypoint_audit["required_gaps"]]
    required_gaps = sorted({*path_blockers, *entrypoint_blockers})

    allowed_paths.sort()
    denied_paths.sort()
    review_paths.sort()
    ignored_local_paths.sort()
    review_gaps.sort()
    path_blockers.sort()
    return {
        "ok": not required_gaps,
        "state": "clean" if not required_gaps else "blocked",
        "contract": generated_artifact_contract(declaration),
        "summary": {
            "allowed_path_count": len(allowed_paths),
            "denied_path_count": len(denied_paths),
            "review_path_count": len(review_paths),
            "ignored_local_path_count": len(ignored_local_paths),
            "review_gap_count": len(review_gaps),
            "path_blocker_count": len(path_blockers),
            "entrypoint_checked_file_count": entrypoint_audit["summary"]["checked_file_count"],
            "entrypoint_blocker_count": entrypoint_audit["summary"]["blocker_count"],
            "blocker_count": len(required_gaps),
        },
        "allowed_paths": allowed_paths,
        "denied_paths": denied_paths,
        "review_paths": review_paths,
        "ignored_local_paths": ignored_local_paths,
        "review_gaps": review_gaps,
        "path_blockers": path_blockers,
        "entrypoint_audit": entrypoint_audit,
        "required_gaps": required_gaps,
    }


def generated_artifact_entrypoint_audit(root: Path) -> dict[str, Any]:
    """Report whether active producer entrypoints route generated state semantically."""
    checked_files: list[str] = []
    findings: list[dict[str, str]] = []

    for rel, path in _entrypoint_files(root):
        checked_files.append(rel)
        text = path.read_text(encoding="utf-8", errors="replace")
        findings.extend(_entrypoint_findings(rel, text))

    required_gaps = sorted({finding["required_gap"] for finding in findings})
    checked_files.sort()
    findings.sort(key=lambda item: (item["path"], item["check"], item["required_gap"]))
    return {
        "ok": not required_gaps,
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
    commands: list[str] = []
    for task in tasks.values():
        commands.extend(_structured_task_commands(task))
    return "\n".join(commands)


def _structured_task_commands(task: object) -> list[str]:
    if isinstance(task, str):
        return [task]
    if isinstance(task, list):
        return [" ".join(str(token) for token in task)]
    if not isinstance(task, dict):
        return []
    for key in ("cmd", "command"):
        command = task.get(key)
        if isinstance(command, str):
            return [command]
        if isinstance(command, list):
            return [" ".join(str(token) for token in command)]
    return []


def _active_entrypoint_lines(text: str) -> list[str]:
    return [line for raw in text.splitlines() if (line := raw.strip()) and not line.startswith("#")]


def _denied_home_findings(rel: str, active_text: str) -> list[dict[str, str]]:
    return [
        _entrypoint_finding(
            rel,
            check=check,
            boundary=boundary,
            required_gap=f"{gap_prefix}:{rel}:{token}",
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
        for token in tokens
        if _contains_denied_home_token(line, token)
    ]


def _tool_route_findings(rel: str, active_text: str, full_text: str) -> list[dict[str, str]]:
    if rel != ".gitlab-ci.yml" and not rel.startswith(("tools/", ".github/", ".githooks/")):
        return _pytest_config_findings(rel, active_text)
    producer_text = "\n".join(
        line for line in active_text.splitlines() if not _is_cleanup_line(line)
    )
    return [
        *_pytest_config_findings(rel, active_text),
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
            _ROOT_VENV_RUNTIME_TOKEN in producer_text,
            "root-venv-runtime",
            "active execution must not fall back to root .venv",
            "root_venv_runtime",
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
    return [
        _entrypoint_finding(
            rel,
            check="package-artifact-routing",
            boundary="local package builds must route to build/artifacts/<kind>",
            required_gap=f"generated_artifact_entrypoint_package_artifacts_unrouted:{rel}",
        )
        for line in producer_text.splitlines()
        if ("uv build" in line or "hatch build" in line or "python -m build" in line)
        and "--out-dir build/artifacts/" not in line
    ]


def _gitlab_local_route_findings(rel: str, producer_text: str) -> list[dict[str, str]]:
    return (
        []
        if "gitlab-ci-local" not in producer_text
        or "build/runtime/work/gitlab-ci-local" in producer_text
        else [
            _entrypoint_finding(
                rel,
                check="gitlab-local-state-routing",
                boundary="gitlab-ci-local state must route to build/runtime/work/gitlab-ci-local",
                required_gap=f"generated_artifact_entrypoint_gitlab_state_unrouted:{rel}",
            )
        ]
    )


def _contains_denied_home_token(line: str, token: str) -> bool:
    if token not in line:
        return False
    if token != "dist/":
        return True
    return line.startswith("dist/") or any(
        marker in line
        for marker in (
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


def _candidate_paths(root: Path, declaration: GeneratedArtifactTopologyDeclaration) -> list[Path]:
    candidates: dict[str, Path] = {}
    prefixes = (
        *declaration.product_adopter_root_prefixes,
        *(
            item.prefix.rstrip("/")
            for group in (
                "declarative_prefix",
                "review_prefix",
                "denied_prefix",
                "denied_root_cache_prefix",
                "denied_legacy_generated_prefix",
            )
            for item in getattr(declaration, group)
        ),
        declaration.cache_flat_root_prefix,
        declaration.runtime_flat_root_prefix,
    )
    descendant_prefixes = tuple(f"{prefix}/" for prefix in prefixes)
    for rel in _explicit_denied_roots(declaration):
        path = root / rel
        if path.exists():
            candidates[rel] = path

    for parent, directories, filenames in walk(root, topdown=True):
        directory = Path(parent)
        rel_directory = directory.relative_to(root)
        directories[:] = [
            name for name in directories if not _skip_descendant(rel_directory / name, declaration)
        ]
        if directory != root:
            rel = rel_directory.as_posix()
            if rel not in candidates and (rel in prefixes or rel.startswith(descendant_prefixes)):
                policy = path_policy_from_declaration(rel_directory, declaration)
                if policy["decision"] == "deny" and not any(
                    child.is_file() for child in directory.rglob("*")
                ):
                    candidates[rel] = directory
        for name in filenames:
            path = directory / name
            rel = path.relative_to(root).as_posix()
            generated = (
                name not in declaration.source_metadata_filenames
                and not name.endswith(declaration.source_schema_suffix)
                and (
                    name in declaration.generated_filenames
                    or path.suffix in declaration.generated_suffixes
                    or name.startswith(declaration.generated_filename_prefixes)
                )
            )
            if (
                rel not in candidates
                and (generated or rel in prefixes or rel.startswith(descendant_prefixes))
                and path_policy_from_declaration(path.relative_to(root), declaration)["decision"]
                != "ignore"
            ):
                candidates[rel] = path
    return [candidates[key] for key in sorted(candidates)]


def _skip_descendant(rel: Path, declaration: GeneratedArtifactTopologyDeclaration) -> bool:
    """Skip excluded implementation trees and recursive allowed artifact homes."""
    return rel.name in _PRUNE_DIRS or any(
        rel.as_posix() == item.prefix.rstrip("/") for item in declaration.allowed_prefix
    )


def _explicit_denied_roots(declaration: GeneratedArtifactTopologyDeclaration) -> list[str]:
    contract = generated_artifact_contract(declaration)
    return [
        prefix
        for group in ("denied_root_cache_prefixes", "denied_legacy_generated_prefixes")
        for item in contract[group]
        if (prefix := str(item["prefix"]).rstrip("/"))
    ]


def _is_ignored_local_test_residue(root: Path, rel: str) -> bool:
    return (
        "/" not in rel
        and (rel in _ROOT_TEST_RESIDUE_FILENAMES or rel.startswith(_ROOT_TEST_RESIDUE_PREFIXES))
        and _git_status_check(root, "check-ignore", "--quiet", "--", rel)
        and not _git_status_check(root, "ls-files", "--error-unmatch", "--", rel)
    )


def _git_status_check(root: Path, *args: str) -> bool:
    completed = subprocess.run(
        ("git", *args),
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0
