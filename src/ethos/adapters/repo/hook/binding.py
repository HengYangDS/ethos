"""One package-owned declaration of native Git hook launcher bytes."""

from __future__ import annotations

import hashlib
import os
import re
import tomllib
from pathlib import Path
from pathlib import PurePosixPath
from typing import TypedDict


class HookContract(TypedDict):
    """Exact launcher bytes and identity compiled from one selected package."""

    scripts: tuple[str, ...]
    launchers: dict[str, str]
    generation_digest: str


def load_hook_contract(
    path: Path | None = None, *, platform_name: str | None = None
) -> HookContract:
    """Read the package declaration without executing its interpreter or source."""
    declaration = path or Path(__file__).with_suffix(".toml")
    if declaration.is_symlink():
        message = "hook_launcher_declaration_invalid"
        raise ValueError(message)
    data = tomllib.loads(declaration.read_text(encoding="utf-8"))
    scripts, platforms, template = (data.get(key) for key in ("scripts", "python", "launcher"))
    valid = (
        set(data) == {"scripts", "python", "launcher"}
        and isinstance(scripts, list)
        and bool(scripts)
        and all(
            isinstance(name, str) and re.fullmatch(r"[a-z][a-z0-9-]*", name) for name in scripts
        )
        and len(scripts) == len(set(scripts))
        and isinstance(platforms, dict)
        and set(platforms) == {"posix", "nt"}
        and all(
            isinstance(value, str)
            and bool(re.fullmatch(r"[A-Za-z0-9_./-]+", value))
            and not PurePosixPath(value).is_absolute()
            and ".." not in PurePosixPath(value).parts
            for value in platforms.values()
        )
        and isinstance(template, str)
        and template.startswith("#!/bin/sh\n")
        and template.endswith("\n")
        and template.count("@PYTHON@") == template.count("@HOOK@") == 1
    )
    if not valid:
        message = "hook_launcher_declaration_invalid"
        raise ValueError(message)
    platform = platform_name or os.name
    if platform not in platforms:
        message = "hook_launcher_platform_invalid"
        raise ValueError(message)
    names = tuple(scripts)
    launchers = {
        name: template.replace("@PYTHON@", platforms[platform]).replace("@HOOK@", name)
        for name in names
    }
    return HookContract(
        scripts=names,
        launchers=launchers,
        generation_digest=hook_generation_digest(launchers, scripts=names),
    )


def hook_generation_digest(
    launchers: dict[str, str], *, scripts: tuple[str, ...] | None = None
) -> str:
    """Return the identity of one complete ordered native launcher contract."""
    if tuple(launchers) != (HOOK_NAMES if scripts is None else scripts):
        message = "hook_launcher_projection_invalid"
        raise ValueError(message)
    return hashlib.sha256(
        b"".join(
            name.encode() + b"\0" + content.encode() + b"\0" for name, content in launchers.items()
        )
    ).hexdigest()


HOOK_NAMES = load_hook_contract()["scripts"]


def hook_launcher(name: str) -> str:
    """Render one native launcher from the invoking package declaration."""
    if name not in HOOK_NAMES:
        message = "hook_name_invalid"
        raise ValueError(message)
    return load_hook_contract()["launchers"][name]
