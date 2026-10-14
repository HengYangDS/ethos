"""Native configuration quality over authored inputs and mandatory installed policy."""

from __future__ import annotations

import configparser
import fnmatch
import json
import os
import subprocess
import tomllib
from pathlib import Path

import yaml
from yamllint import config as yamllint_config
from yamllint import linter as yamllint_linter

from ethos.adapters.gates.format_selection import audit as carrier_ownership
from ethos.adapters.gates.tool import native_configurations
from ethos.adapters.gates.tool import quality_inventory_failure
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.verdict import close_verdict

SUPPORTED_SUFFIXES = frozenset({".toml", ".yaml", ".yml", ".json", ".ini", ".cfg"})


def _configuration_inventory(root: Path) -> tuple[Path, ...]:
    output = run_command(
        root,
        (
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
            *(f"*{suffix}" for suffix in sorted(SUPPORTED_SUFFIXES)),
        ),
        timeout=30,
        check=True,
    ).stdout
    return tuple(Path(item) for item in output.split("\0") if item)


def _candidate_paths(root: Path, requested: tuple[str, ...]) -> dict[str, tuple[Path, ...]]:
    selected = []
    for raw in tuple(map(Path, requested)) or _configuration_inventory(root):
        path = root / raw
        if raw.suffix.lower() not in SUPPORTED_SUFFIXES:
            message = f"unsupported config lint targets: {raw}"
            raise ValueError(message)
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            message = f"config target outside repository: {raw}"
            raise ValueError(message)
        if not path.is_file():
            if requested:
                message = f"config target missing or not a file: {raw}"
                raise ValueError(message)
            continue
        relative = path.resolve().relative_to(root.resolve()).as_posix()
        selected.append(Path(relative))
    ownership = carrier_ownership(root, paths=tuple(map(str, dict.fromkeys(selected))))
    if ownership["failures"]:
        message = f"config ownership unresolved: {ownership['failures']}"
        raise ValueError(message)
    candidates = []
    for assignment in ownership["assignments"]:
        if assignment["mutation_policy"] not in {
            "forbidden",
            "official-owner-only",
            "package-manager-only",
            "generator-only",
        } and assignment["validation_command"].endswith("-s config_quality"):
            candidates.append(Path(assignment["path"]))
        elif requested:
            message = (
                f"config target has another owner: {assignment['path']}; "
                f"run {assignment['validation_command']}"
            )
            raise ValueError(message)
    return {
        kind: tuple(path for path in candidates if path.suffix.lower() in suffixes)
        for kind, suffixes in {
            "toml": {".toml"},
            "yaml": {".yaml", ".yml"},
            "json": {".json"},
            "ini": {".ini", ".cfg"},
        }.items()
    }


def _text_failures(path: Path, data: bytes) -> list[str]:
    failures = []
    if data and not data.endswith(b"\n"):
        failures.append(f"{path}: missing final newline")
    if data.endswith(b"\n\n"):
        failures.append(f"{path}: more than one trailing newline")
    failures.extend(
        f"{path}:{number}: trailing whitespace"
        for number, line in enumerate(data.splitlines(), start=1)
        if line.rstrip(b" \t") != line
    )
    return failures


def _toml_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    failures = []
    for relative in paths:
        data = (root / relative).read_bytes()
        failures.extend(_text_failures(relative, data))
        try:
            tomllib.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            failures.append(f"{relative}: TOML parse failed: {error}")
    if not paths or failures:
        return failures
    node = resolve_node_runtime().executable
    taplo = product_node_module("@taplo/cli") / "dist/cli.js"
    configs = native_configurations(root, "taplo", ".config/checks/taplo/taplo.toml")
    for config in configs:
        for arguments in (("format", "--check"), ("lint", "--no-schema")):
            completed = run_command(
                root,
                (str(node), str(taplo), *arguments, "--config", config, *map(str, paths)),
                timeout=60,
                remove_env=("NODE_OPTIONS", "NODE_PATH"),
            )
            if completed.returncode:
                failures.append((completed.stdout + completed.stderr).strip())
    return failures


def _native_format_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    """Use the original Prettier check on the same exact authored configuration."""
    if not paths:
        return []
    failures = []
    configs = native_configurations(root, "prettier", ".config/checks/prettier/prettier.toml")
    node = str(resolve_node_runtime().executable)
    prettier = str(product_node_module("prettier") / "bin/prettier.cjs")
    for config in configs:
        completed = run_command(
            root,
            (
                node,
                prettier,
                "--config",
                config,
                "--no-editorconfig",
                "--ignore-path",
                os.devnull,
                "--check",
                "--",
                *map(str, paths),
            ),
            timeout=60,
            remove_env=("NODE_OPTIONS", "NODE_PATH"),
        )
        if completed.returncode or completed.stderr:
            failures.append((completed.stdout + completed.stderr).strip())
    return failures


def _json_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    """Preserve the native serializer's authored JSON policy and exact bytes."""
    failures = []
    policies = tuple(
        tomllib.loads(Path(config).read_text(encoding="utf-8"))
        for config in native_configurations(
            root, "python-stdlib-json", ".config/checks/config-quality/policy.toml"
        )
    )
    for path in paths:
        try:
            data = (root / path).read_bytes()
            parsed = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            failures.append(f"{path}: JSON parse failed: {error}")
            continue
        for policy in policies:
            mode = next(
                (
                    rule["mode"]
                    for rule in reversed(policy.get("rule", []))
                    if any(fnmatch.fnmatchcase(str(path), pattern) for pattern in rule["globs"])
                ),
                policy["default_mode"],
            )
            rendered = (
                json.dumps(parsed, ensure_ascii=False, separators=(",", ":"))
                if mode == "compact"
                else json.dumps(parsed, ensure_ascii=False, indent=policy["indent"])
            ) + "\n"
            if data != rendered.encode("utf-8"):
                failures.append(f"{path}: JSON format drift")
    return failures


def _yaml_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    failures = []
    configs = native_configurations(root, "yamllint", ".config/checks/yamllint/.yamllint.yaml")
    policies = [yamllint_config.YamlLintConfig(Path(config).read_text()) for config in configs]
    semantic_rules = policies[0].rules.keys()
    for path in paths:
        text = (root / path).read_text(encoding="utf-8")
        for policy in policies:
            problems = tuple(yamllint_linter.run(text, policy, filepath=path.as_posix()))
            scalar_lines: set[int] = set()
            if any(problem.rule == "empty-lines" for problem in problems):
                try:
                    scalar_lines = {
                        line
                        for token in yaml.scan(text)
                        if isinstance(token, yaml.ScalarToken)
                        for line in range(token.start_mark.line + 2, token.end_mark.line + 1)
                    }
                except yaml.YAMLError:
                    scalar_lines = set()
            failures.extend(
                f"{path}:{problem.line}:{problem.column}: {problem.message}"
                for problem in problems
                if (problem.rule is None or problem.rule in semantic_rules)
                and (problem.rule != "empty-lines" or problem.line not in scalar_lines)
            )
    return [*failures, *_native_format_failures(root, paths)]


def _ini_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    failures = []
    for path in paths:
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        try:
            with (root / path).open(encoding="utf-8") as stream:
                parser.read_file(stream)
        except (UnicodeDecodeError, configparser.Error) as error:
            failures.append(f"{path}: INI parse failed: {error}")
    return failures


def configuration_report(root: Path, *, paths: tuple[str, ...] = ()) -> dict[str, object]:
    """Check native configuration without source tooling, writes or ambient policy."""
    candidates: dict[str, tuple[Path, ...]] = {}
    try:
        candidates = _candidate_paths(root, paths)
        failures = (
            *_toml_failures(root, candidates["toml"]),
            *_json_failures(root, candidates["json"]),
            *_yaml_failures(root, candidates["yaml"]),
            *_ini_failures(root, candidates["ini"]),
        )
    except (GitExecutionError, subprocess.CalledProcessError) as error:
        return quality_inventory_failure(root, "config-quality", error)
    except (
        OSError,
        ValueError,
        yamllint_config.YamlLintConfigError,
        ProcessExecutionError,
        subprocess.TimeoutExpired,
    ) as error:
        failures = (str(error),)
    return {
        "id": "config-quality",
        "verdict": close_verdict("pass", required_gaps=failures),
        "state": "unproven" if failures else "verified",
        "file_count": sum(map(len, candidates.values())),
        "required_gaps": list(failures),
    }
