"""Typed native package fields consumed by reference observation and declarations."""

from __future__ import annotations

import json
import re
import tomllib
from collections import defaultdict
from typing import Literal

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import ValidationError

from ethos.repository.policy.references.carriers import reference_carrier
from ethos.repository.policy.references.commands import shell_executables


class ProjectFields(BaseModel):
    """Only consumed Python project fields; unrelated native fields remain native."""

    model_config = ConfigDict(strict=True, extra="ignore")
    name: str | None = None
    requires_python: str | None = Field(default=None, alias="requires-python")
    dependencies: list[str] = Field(default_factory=list)
    optional_dependencies: dict[str, list[str]] = Field(
        default_factory=dict, alias="optional-dependencies"
    )
    scripts: dict[str, str] = Field(default_factory=dict)
    gui_scripts: dict[str, str] = Field(default_factory=dict, alias="gui-scripts")


class BuildFields(BaseModel):
    """A build requirement list cannot be a character-wise string iteration."""

    model_config = ConfigDict(strict=True, extra="ignore")
    requires: list[str] = Field(default_factory=list)


class GroupInclude(BaseModel):
    """Native PEP 735 group inclusion is not a distribution name."""

    model_config = ConfigDict(strict=True, extra="forbid")
    include_group: str = Field(alias="include-group")


class PythonManifest(BaseModel):
    """Shape validation for the exact fields this observation actually consumes."""

    model_config = ConfigDict(strict=True, extra="ignore")
    project: ProjectFields = Field(default_factory=ProjectFields)
    build_system: BuildFields = Field(default_factory=BuildFields, alias="build-system")
    dependency_groups: dict[str, list[str | GroupInclude]] = Field(
        default_factory=dict, alias="dependency-groups"
    )

    @classmethod
    def read(cls, text: str) -> PythonManifest | None:
        """Parse once and reject malformed consumed fields without coercion."""
        try:
            return cls.model_validate(tomllib.loads(text))
        except (tomllib.TOMLDecodeError, ValidationError):
            return None

    def declarations(self, observed: dict[str, set[str]]) -> None:
        """Project native package and executable identities from valid values."""
        requirements = list(self.project.dependencies) + self.build_system.requires
        if self.project.name is not None:
            requirements.append(self.project.name)
        for values in self.project.optional_dependencies.values():
            requirements.extend(values)
        for values in self.dependency_groups.values():
            requirements.extend(value for value in values if isinstance(value, str))
        for requirement in requirements:
            if match := re.match(r"[A-Za-z0-9][A-Za-z0-9._-]*", requirement):
                observed["distribution"].add(normalized_distribution(match.group()))
        observed["executable"].update(self.project.scripts)
        observed["executable"].update(self.project.gui_scripts)
        # As devEngines declares npm, requires-python declares the interpreter the project runs.
        if self.project.requires_python is not None:
            observed["executable"].add("python")


class NativePackageManager(BaseModel):
    """One native devEngines alternative declares an executable, not its effects."""

    model_config = ConfigDict(strict=True, extra="forbid")
    name: str = Field(min_length=1)
    version: str = ""
    on_fail: Literal["ignore", "warn", "error", "download"] = Field(default="error", alias="onFail")


class NodeDevEngines(BaseModel):
    """Validate consumed package-manager fields; other native engines stay native."""

    model_config = ConfigDict(strict=True, extra="ignore")
    package_manager: NativePackageManager | list[NativePackageManager] = Field(
        default_factory=list, alias="packageManager"
    )


class NodeManifest(BaseModel):
    """Typed Node metadata, without interpreting arbitrary fields as commands."""

    model_config = ConfigDict(strict=True, extra="ignore")
    name: str | None = None
    private: bool = False
    scripts: dict[str, str] = Field(default_factory=dict)
    dependencies: dict[str, str] = Field(default_factory=dict)
    dev_dependencies: dict[str, str] = Field(default_factory=dict, alias="devDependencies")
    optional_dependencies: dict[str, str] = Field(
        default_factory=dict, alias="optionalDependencies"
    )
    peer_dependencies: dict[str, str] = Field(default_factory=dict, alias="peerDependencies")
    package_manager: str | None = Field(default=None, alias="packageManager")
    dev_engines: NodeDevEngines = Field(default_factory=NodeDevEngines, alias="devEngines")
    bin: str | dict[str, str] | None = None

    @classmethod
    def read(cls, text: str) -> NodeManifest | None:
        """Validate scripts and declarations before any consumer iterates them."""
        try:
            return cls.model_validate(json.loads(text))
        except (json.JSONDecodeError, ValidationError):
            return None

    def declarations(self, observed: dict[str, set[str]]) -> None:
        """Native authored identities remain distinct from consumed script effects."""
        if not self.private and self.name is not None:
            observed["distribution"].add(self.name.lower())
        for dependencies in (
            self.dependencies,
            self.dev_dependencies,
            self.optional_dependencies,
            self.peer_dependencies,
        ):
            observed["distribution"].update(name.lower() for name in dependencies)
        if self.package_manager is not None:
            observed["executable"].add(self.package_manager.partition("@")[0])
        managers = self.dev_engines.package_manager
        for manager in managers if isinstance(managers, list) else [managers]:
            observed["executable"].add(manager.name)
        if isinstance(self.bin, dict):
            observed["executable"].update(self.bin)
        elif isinstance(self.bin, str) and self.name is not None:
            observed["executable"].add(self.name.rsplit("/", 1)[-1])


def pyproject_references(
    text: str, observed: dict[str, set[str]], *, declarations: bool = True
) -> bool:
    """Project valid Python fields; report malformed consumed shapes explicitly."""
    manifest = PythonManifest.read(text)
    if manifest is None:
        return False
    if declarations:
        manifest.declarations(observed)
    return True


def package_json_references(
    text: str,
    npm_scripts: dict[str, set[str]],
    observed: dict[str, set[str]],
    *,
    declarations: bool,
) -> bool:
    """Consume only validated script strings and retain declaration ownership."""
    manifest = NodeManifest.read(text)
    if manifest is None:
        return False
    if declarations:
        manifest.declarations(observed)
    for command in manifest.scripts.values():
        observed["executable"].update(
            shell_executables(command, npm_scripts, module_imports=observed["import"])
        )
    return True


def npm_script_commands(files: dict[str, str]) -> dict[str, set[str]]:
    """Compile declared script alternatives without silently coercing their values."""
    scripts: dict[str, set[str]] = defaultdict(set)
    for path, text in files.items():
        if reference_carrier(path).name != "package-json":
            continue
        manifest = NodeManifest.read(text)
        if manifest is not None:
            for name, command in manifest.scripts.items():
                scripts[name].add(command)
    return dict(scripts)


def normalized_distribution(value: str) -> str:
    """Normalize a native package identity with the PEP 503 name relation."""
    return re.sub(r"[-_.]+", "-", value).lower()
