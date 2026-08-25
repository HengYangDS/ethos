"""Hatch hook for the lock-bound, production-only OpenSpec runtime."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

_SOURCE_IDENTITY_PATH = Path("src/ethos/data/build/source-identity.json")


class OpenSpecRuntimeHook(BuildHookInterface):
    """Compile the npm production closure into wheel build data."""

    PLUGIN_NAME = "openspec-runtime"

    def _cleanup_supply(self) -> None:
        owned = self.__dict__.pop("_owned_supply", None)
        if owned is not None:
            owned.cleanup()

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        if version == "editable":
            return
        self._cleanup_supply()
        root = Path(self.root)
        owned = tempfile.TemporaryDirectory(prefix="ethos-openspec-supply-")
        supply = Path(owned.name)
        self._owned_supply = owned
        try:
            identity = _source_identity(root)
            identity_file = supply / "source-identity.json"
            identity_file.write_text(
                json.dumps(identity, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            if self.target_name == "sdist":
                build_data["force_include"][str(identity_file)] = _SOURCE_IDENTITY_PATH.as_posix()
                return
            build_data["force_include"][str(identity_file)] = (
                "ethos/data/build/source-identity.json"
            )
            for relative in ("package.json", "package-lock.json"):
                shutil.copy2(root / relative, supply / relative)
            node = os.environ.get("ETHOS_BUILD_NODE", "")
            npm_cli = os.environ.get("ETHOS_BUILD_NPM_CLI", "")
            if not node or not npm_cli:
                _runtime_unavailable()
            subprocess.run(
                (
                    node,
                    npm_cli,
                    "ci",
                    "--omit=dev",
                    "--ignore-scripts",
                    "--offline",
                    "--workspaces=false",
                    "--no-audit",
                    "--no-fund",
                ),
                cwd=supply,
                check=True,
            )
            build_data["force_include"][str(supply / "node_modules")] = (
                "ethos/data/openspec-runtime/node_modules"
            )
        except BaseException as error:
            try:
                self._cleanup_supply()
            except OSError as cleanup_error:
                error.add_note(f"OpenSpec supply cleanup failed: {cleanup_error}")
            raise

    def finalize(self, version: str, build_data: dict[str, Any], artifact_path: str) -> None:
        del version, build_data, artifact_path
        self._cleanup_supply()


def get_build_hook() -> type[OpenSpecRuntimeHook]:
    """Expose the single custom hook class to Hatchling."""
    return OpenSpecRuntimeHook


def _runtime_unavailable() -> None:
    message = "Nox must bind the package-local Node/npm runtime"
    raise RuntimeError(message)


def _source_identity(root: Path) -> dict[str, object]:
    observed = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if observed.returncode:
        return _carried_source_identity(root)
    commit = observed.stdout.strip()
    with tempfile.TemporaryDirectory(prefix="ethos-source-index-") as directory:
        environment = {**os.environ, "GIT_INDEX_FILE": str(Path(directory) / "index")}
        subprocess.run(("git", "read-tree", "HEAD"), cwd=root, env=environment, check=True)
        subprocess.run(("git", "add", "-A"), cwd=root, env=environment, check=True)
        tree = subprocess.run(
            ("git", "write-tree"),
            cwd=root,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    identity: dict[str, object] = {
        "schema_version": 1,
        "source_commit": commit,
        "source_tree": tree,
    }
    if not _valid_source_identity(identity):
        message = "hook_runtime_build_source_identity_invalid"
        raise RuntimeError(message)
    return identity


def _carried_source_identity(root: Path) -> dict[str, object]:
    try:
        identity = json.loads((root / _SOURCE_IDENTITY_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as error:
        message = "hook_runtime_build_source_identity_missing"
        raise RuntimeError(message) from error
    if _valid_source_identity(identity):
        return identity
    message = "hook_runtime_build_source_identity_invalid"
    raise RuntimeError(message)


def _valid_source_identity(identity: object) -> bool:
    if not isinstance(identity, dict) or identity.get("schema_version") != 1:
        return False
    values = (identity.get("source_commit"), identity.get("source_tree"))
    return all(
        isinstance(value, str)
        and len(value) in {40, 64}
        and not set(value) - set("0123456789abcdef")
        for value in values
    )
