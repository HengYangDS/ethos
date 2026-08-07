"""Cross-platform configuration syntax and canonical-format owner."""

from __future__ import annotations

import fnmatch
import json
import subprocess
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING
from typing import Any

from yamllint import config as yamllint_config
from yamllint import linter as yamllint_linter

if TYPE_CHECKING:
    from collections.abc import Iterable

ROOT = Path(__file__).resolve().parents[2]
TAPLO = ROOT / "node_modules/@taplo/cli/dist/cli.js"
TAPLO_CONFIG = ROOT / ".config/checks/taplo/taplo.toml"
YAML_CONFIG = ROOT / ".config/checks/yaml/yamllint.yaml"
JSON_CONFIG = ROOT / ".config/checks/json/format.toml"
DEFAULT_YAML_PATHS = (
    Path(".pre-commit-config.yaml"),
    Path(".config/checks/markdown/.markdownlint-cli2.yaml"),
    Path(".config/checks/yaml/yamllint.yaml"),
    Path(".config/ci/templates/hosted/github-actions.yml"),
    Path(".config/ci/templates/hosted/gitlab-ci.yml"),
    Path(".github/workflows/ci.yml"),
    Path(".gitlab-ci.yml"),
)
SUPPORTED_SUFFIXES = frozenset({".toml", ".yaml", ".yml", ".json"})
EXTERNAL_YAML_ROOTS = (Path("openspec"),)


def _ethos_yaml(path: Path) -> bool:
    return not any(path.is_relative_to(root) for root in EXTERNAL_YAML_ROOTS)


def _tracked_paths(*patterns: str) -> tuple[Path, ...]:
    output = subprocess.check_output(("git", "ls-files", "-z", *patterns), cwd=ROOT)
    return tuple(Path(item.decode()) for item in output.split(b"\0") if item)


def _candidate_paths(raw_paths: Iterable[str]) -> dict[str, tuple[Path, ...]]:
    requested = tuple(Path(raw) for raw in raw_paths)
    unsupported = tuple(path for path in requested if path.suffix.lower() not in SUPPORTED_SUFFIXES)
    if unsupported:
        names = ", ".join(path.as_posix() for path in unsupported)
        message = f"unsupported config lint targets: {names}"
        raise ValueError(message)
    paths = requested or (*_tracked_paths("*.toml", "*.json"), *DEFAULT_YAML_PATHS)
    existing = tuple(
        dict.fromkeys(
            path
            for path in paths
            if (ROOT / path).is_file()
            and (path.suffix.lower() not in {".yaml", ".yml"} or _ethos_yaml(path))
        )
    )
    return {
        suffix: tuple(path for path in existing if path.suffix.lower() in suffixes)
        for suffix, suffixes in {
            "toml": {".toml"},
            "yaml": {".yaml", ".yml"},
            "json": {".json"},
        }.items()
    }


def _text_failures(path: Path, data: bytes) -> list[str]:
    failures = []
    if data and not data.endswith(b"\n"):
        failures.append(f"{path}: missing final newline")
    if data.endswith(b"\n\n"):
        failures.append(f"{path}: more than one trailing newline")
    failures.extend(
        f"{path}:{line_number}: trailing whitespace"
        for line_number, line in enumerate(data.splitlines(), start=1)
        if line.rstrip(b" \t") != line
    )
    return failures


def _toml_failures(paths: tuple[Path, ...], node: Path) -> list[str]:
    failures = []
    for relative in paths:
        data = (ROOT / relative).read_bytes()
        failures.extend(_text_failures(relative, data))
        try:
            tomllib.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            failures.append(f"{relative}: TOML parse failed: {error}")
    if not paths or failures:
        return failures
    if not node.is_file() or not TAPLO.is_file():
        return [*failures, "locked Taplo runtime is missing; run npm ci --ignore-scripts"]
    for arguments in (
        ("format", "--check", "--config", str(TAPLO_CONFIG)),
        ("lint", "--config", str(TAPLO_CONFIG), "--no-schema"),
    ):
        completed = subprocess.run(
            (str(node), str(TAPLO), *arguments, *(str(path) for path in paths)),
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode:
            failures.append((completed.stdout + completed.stderr).strip())
    return failures


def _json_rendering(policy: dict[str, Any], relative: str, parsed: Any) -> bytes:
    rules = policy.get("rule", [])
    mode = next(
        (
            str(rule["mode"])
            for rule in reversed(rules)
            if any(fnmatch.fnmatchcase(relative, glob) for glob in rule["globs"])
        ),
        str(policy["default_mode"]),
    )
    indent = None if mode == "compact" else int(policy["indent"])
    arguments: dict[str, Any] = {"ensure_ascii": False, "indent": indent}
    if indent is None:
        arguments["separators"] = (",", ":")
    return (json.dumps(parsed, **arguments) + "\n").encode()


def _json_failures(paths: tuple[Path, ...]) -> list[str]:
    policy = tomllib.loads(JSON_CONFIG.read_text(encoding="utf-8"))
    failures = []
    for path in paths:
        relative = path.as_posix()
        try:
            parsed = json.loads((ROOT / path).read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            failures.append(f"{relative}: JSON parse failed: {error}")
            continue
        if (ROOT / path).read_bytes() != _json_rendering(policy, relative, parsed):
            failures.append(f"{relative}: JSON format drift")
    return failures


def _yaml_failures(paths: tuple[Path, ...]) -> list[str]:
    policy = yamllint_config.YamlLintConfig(YAML_CONFIG.read_text(encoding="utf-8"))
    failures = []
    for path in paths:
        text = (ROOT / path).read_text(encoding="utf-8")
        failures.extend(
            f"{path}:{problem.line}:{problem.column}: {problem.message}"
            for problem in yamllint_linter.run(text, policy, filepath=path.as_posix())
        )
    return failures


def run(paths: Iterable[str], *, node: Path) -> tuple[str, ...]:
    """Return deterministic configuration-quality failures."""
    candidates = _candidate_paths(paths)
    return (
        *_toml_failures(candidates["toml"], node),
        *_json_failures(candidates["json"]),
        *_yaml_failures(candidates["yaml"]),
    )
