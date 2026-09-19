"""Native CUE projection compilation over caller-selected immutable materials."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.toolchain.mise import locked_tool

if TYPE_CHECKING:
    from collections.abc import Mapping


def compile_projections(
    root: Path,
    declaration: str,
    files: Mapping[str, str],
    *,
    executable: Path | None = None,
    observations: Mapping[str, str] | None = None,
    check_format: bool = False,
) -> dict[str, str]:
    """Compile exact materials; candidate code cannot supply the observation verdict."""
    configuration = tomllib.loads(files[declaration])
    compiler = configuration["compiler"]
    inputs = {key: tomllib.loads(files[path]) for key, path in compiler["inputs"].items()}
    source = files[compiler["source"]]
    supply = compiler["supply"]
    tool_files = {"mise.toml": files[supply["config"]], "mise.lock": files[supply["lock"]]}
    version = tomllib.loads(tool_files["mise.toml"])["tools"]["cue"]
    selected = executable or locked_tool(root, "cue", tool_files)
    observed = run_command(root, (str(selected), "version"), timeout=10, check=True)
    if not observed.stdout.startswith(f"cue version v{version}\n"):
        message = "cue_version_mismatch"
        raise ValueError(message)
    # Explicit files in an owned empty directory exclude ambient modules and worktree inputs.
    with TemporaryDirectory(prefix="ethos-cue-") as directory:
        isolated = Path(directory)
        if check_format:
            formatted = run_command(
                isolated,
                (str(selected), "fmt", "-"),
                stdin=source,
                timeout=30,
                env={"CUE_REGISTRY": "none", "CUE_EXPERIMENT": "", "CUE_DEBUG": ""},
            )
            if formatted.returncode or formatted.stdout != source:
                message = f"cue_format_required:{compiler['source']}"
                raise ValueError(message)
        candidate = _export(selected, isolated, source + "\n_inputs: " + json.dumps(inputs))
        providers = candidate["providers"]
        expected = {entry["provider"] for entry in configuration["projection"]}
        if not isinstance(providers, dict) or set(providers) != expected:
            message = "cue_projection_providers_mismatch"
            raise ValueError(message)
        # Decode external bytes only after candidate evaluation has ended. Never pass
        # observations to candidate CUE or trust its own rendered/observations fields.
        transport = (
            'import nativeyaml "encoding/yaml"\n'
            f"providers: {json.dumps(providers)}\n"
            f"observations: {json.dumps(dict(observations or {}))}\n"
            "compiled: {\n"
            "rendered: {for name, value in providers {(name): nativeyaml.Marshal(value)}}\n"
            "observed: {for name, value in observations {(name): nativeyaml.Unmarshal(value)}}\n"
            "}\n"
        )
        result = _export(selected, isolated, transport)
    if observations is not None and result["observed"] != providers:
        message = "cue_projection_drift"
        raise ValueError(message)
    return result["rendered"]


def _export(executable: Path, root: Path, source: str) -> dict:
    try:
        result = run_command(
            root,
            (str(executable), "export", "cue:", "-", "-e", "compiled", "--out", "json"),
            stdin=source,
            timeout=30,
            env={"CUE_REGISTRY": "none", "CUE_EXPERIMENT": "", "CUE_DEBUG": ""},
        )
    except (OSError, subprocess.SubprocessError) as error:
        message = f"cue_execution_unavailable:{error}"
        raise ValueError(message) from error
    if result.returncode:
        message = "cue_compilation_failed: " + result.stderr.strip()
        raise ValueError(message)
    return json.loads(result.stdout)
