"""Native CUE projection compilation over caller-selected immutable materials."""

from __future__ import annotations

import json
import subprocess
import tomllib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING

from ethos.adapters.process import run_command
from ethos.adapters.repo.content.observation import read_regular_bytes
from ethos.adapters.repo.runtime.materialization.native_supply import resolve_native_tool
from ethos.adapters.toolchain.mise import MISE_CONFIG
from ethos.adapters.toolchain.mise import MISE_LOCK
from ethos.adapters.toolchain.mise import locked_tool
from ethos.repository.policy.projections import projection_input_bindings
from ethos.repository.release.resources import canonical_resource
from ethos.repository.release.resources import packaged_resource
from ethos.repository.release.resources import require_packaged_resource

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
    bindings = projection_input_bindings(compiler["inputs"], declaration)
    inputs = {
        key: (json.loads if kind == "json" else tomllib.loads)(files[path])
        for key, (path, kind) in bindings.items()
    }
    source = files[compiler["source"]]
    common, selected, version = _compiler_supply(root, declaration, compiler, files, executable)
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
        candidate_source = source + "\n_inputs: " + json.dumps(inputs)
        if common:
            candidate_source += "\ncompiled: #Verification & {parameters: _inputs.ci}\n"
        candidate = _export(selected, isolated, candidate_source, common=common)
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


def _compiler_supply(
    root: Path, declaration: str, compiler: dict, files: Mapping[str, str], executable: Path | None
) -> tuple[str, Path, str]:
    """Bind product inputs separately from the repository's real source closure."""
    common = ""
    if resource := compiler.get("common"):
        if resource != ".config/ci/verification.cue":
            message = "projection_common_model_unknown:" + declaration
            raise ValueError(message)
        product = canonical_resource("pyproject.toml").parent
        if product == packaged_resource():
            require_packaged_resource(resource)
        common = read_regular_bytes(
            product,
            resource,
            unsafe_gap="product_model_unsafe",
            unstable_gap="product_model_changed",
            size_gap="product_model_size_exceeded",
        ).decode("utf-8")
    supply = compiler.get("supply")
    if supply:
        tool_files = {MISE_CONFIG: files[supply["config"]], MISE_LOCK: files[supply["lock"]]}
        version = tomllib.loads(tool_files[MISE_CONFIG])["tools"]["cue"]
        selected = executable or locked_tool(root, "cue", tool_files)
    elif common:
        product = canonical_resource("pyproject.toml").parent
        version = tomllib.loads((product / MISE_CONFIG).read_text(encoding="utf-8"))["tools"]["cue"]
        selected = executable or (
            resolve_native_tool("cue")
            if product == packaged_resource()
            else locked_tool(product, "cue")
        )
    else:
        message = "projection_compiler_supply_missing:" + declaration
        raise ValueError(message)
    return common, selected, version


def _export(executable: Path, root: Path, source: str, *, common: str = "") -> dict:
    sources = ("cue:", "-")
    if common:
        (root / "common.cue").write_text(common, encoding="utf-8", newline="")
        (root / "repository.cue").write_text(source, encoding="utf-8", newline="")
        sources = ("common.cue", "repository.cue")
    try:
        result = run_command(
            root,
            (str(executable), "export", *sources, "-e", "compiled", "--out", "json"),
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
