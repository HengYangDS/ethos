"""Observe native OpenSpec configuration and schema inputs without host-global state."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from ethos.adapters.openspec.cli import OFFICIAL_VERSION
from ethos.adapters.openspec.cli import openspec_base_command
from ethos.adapters.process import ProcessExecutionError
from ethos.adapters.process import run_command
from ethos.normalization.coercion import string_sequence
from ethos.repository.openspec.audit import configuration_policy_gaps


def official_config_report(root: Path, *, initialize: bool = False) -> dict[str, object]:
    """Resolve the selected native config, schema and templates before claiming readiness."""
    target = root.resolve()
    command = openspec_base_command(execution_probe=False)
    fallback: dict[str, object] = {
        "verdict": "unknown",
        "path": str(target / "openspec/config.yaml"),
        "content": None,
        "default_content": "",
        "exists": False,
        "safe": False,
        "required_gaps": ["openspec_configuration_observation_unavailable"],
        "inputs": [],
        "input_digest": "",
    }
    if command is None:
        return fallback | {"required_gaps": ["openspec_official_cli_missing"]}
    try:
        with TemporaryDirectory(prefix="ethos-openspec-configuration-") as temporary:
            environment = {
                key: os.environ[key]
                for key in ("PATH", "SystemRoot", "WINDIR")
                if key in os.environ
            }
            environment.update(
                HOME=temporary,
                USERPROFILE=temporary,
                XDG_DATA_HOME=temporary,
                XDG_CONFIG_HOME=temporary,
                OPENSPEC_TELEMETRY="0",
                OPENSPEC_NO_UPDATE_CHECK="1",
            )
            completed = run_command(
                target,
                (
                    command[0],
                    str(Path(__file__).with_suffix(".mjs")),
                    command[1],
                    OFFICIAL_VERSION,
                    str(target),
                    "initialize" if initialize else "inspect",
                ),
                env=environment,
                inherit_environment=False,
                timeout=30,
            )
        payload = json.loads(completed.stdout)
        if (
            completed.returncode
            or completed.stderr
            or not isinstance(payload, dict)
            or payload.get("verdict") not in {"pass", "block", "unknown"}
            or not isinstance(payload.get("path"), str)
            or not isinstance(payload.get("required_gaps"), list)
            or not all(isinstance(gap, str) for gap in payload["required_gaps"])
            or not isinstance(payload.get("input_digest"), str)
            or not isinstance(payload.get("default_content"), str)
            or not isinstance(payload.get("content"), (str, type(None)))
            or not isinstance(payload.get("exists"), bool)
            or not isinstance(payload.get("safe"), bool)
            or not isinstance(payload.get("inputs"), list)
            or not Path(payload["path"]).is_relative_to(target)
        ):
            return fallback | {"detail": completed.stderr or completed.stdout}
    except (OSError, ProcessExecutionError, subprocess.TimeoutExpired, ValueError) as error:
        return fallback | {"detail": f"{type(error).__name__}: {error}"}
    payload["required_gaps"].extend(configuration_policy_gaps(string_sequence(payload.get("keys"))))
    if payload["required_gaps"] and payload["verdict"] == "pass":
        payload["verdict"] = "block"
    return payload
