"""Native configuration quality over authored inputs and mandatory installed policy."""

from __future__ import annotations

import configparser
import json
import subprocess
import tomllib
from pathlib import Path

from yamllint import config as yamllint_config
from yamllint import linter as yamllint_linter

from ethos.adapters.gates.formatting import source_format_report
from ethos.adapters.gates.native.inputs import authored_source_files
from ethos.adapters.gates.native.inputs import native_configurations
from ethos.adapters.gates.native.inputs import quality_inventory_failure
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.adapters.repo.git import GitExecutionError
from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node_package_supply import product_node_module
from ethos.contracts.verdict import close_verdict
from ethos.normalization.coercion import string_sequence

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
    inventory = tuple(map(Path, requested)) or _configuration_inventory(root)
    candidates = []
    for raw in inventory:
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
        candidates.append(path.resolve().relative_to(root.resolve()).as_posix())
    authored = set(authored_source_files(root, paths=tuple(candidates))) if candidates else set()
    selected = []
    for relative in candidates:
        owned_elsewhere = (
            relative not in authored
            or relative.startswith(("openspec/changes/", "openspec/specs/"))
            or relative in {"openspec/config.yaml", "openspec/config.yml"}
        )
        if owned_elsewhere:
            if requested:
                message = f"config target has another owner: {relative}"
                raise ValueError(message)
            continue
        selected.append(Path(relative))
    return {
        kind: tuple(path for path in dict.fromkeys(selected) if path.suffix.lower() in suffixes)
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
        completed = run_command(
            root,
            (
                str(node),
                str(taplo),
                "lint",
                "--no-schema",
                "--config",
                config,
                *map(str, paths),
            ),
            timeout=60,
            remove_env=("NODE_OPTIONS", "NODE_PATH"),
        )
        if completed.returncode:
            failures.append((completed.stdout + completed.stderr).strip())
    return failures


def _json_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    failures = []
    for path in paths:
        try:
            json.loads((root / path).read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            failures.append(f"{path}: JSON parse failed: {error}")
    return failures


def _yaml_failures(root: Path, paths: tuple[Path, ...]) -> list[str]:
    failures = []
    configs = native_configurations(root, "yamllint", ".config/checks/yamllint/.yamllint.yaml")
    policies = [yamllint_config.YamlLintConfig(Path(config).read_text()) for config in configs]
    semantic_rules = policies[0].rules.keys()
    for path in paths:
        text = (root / path).read_text(encoding="utf-8")
        for policy in policies:
            failures.extend(
                f"{path}:{problem.line}:{problem.column}: {problem.message}"
                for problem in yamllint_linter.run(text, policy, filepath=path.as_posix())
                if problem.rule is None or problem.rule in semantic_rules
            )
    return failures


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
        format_paths = tuple(
            path.as_posix() for kind in ("toml", "json", "yaml") for path in candidates[kind]
        )
        if format_paths:
            formatted = source_format_report(root, paths=format_paths)
            failures = (*failures, *string_sequence(formatted["required_gaps"]))
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
