"""Hash-checked bytecode that every process of one test gate run shares."""

from __future__ import annotations

import re
import sys
import sysconfig
from contextlib import suppress
from pathlib import Path

from ethos.adapters.process import run_command

CACHE = Path("build/runtime/tool-cache/python-bytecode")
_SKIP = r"[\\/](?:idlelib|test|tests|tkinter|turtledemo)[\\/]"


def sources(root: Path) -> tuple[Path, ...]:
    """Return the interpreter, environment and repository sources test processes import."""
    paths = sysconfig.get_paths()
    environment = dict.fromkeys(Path(paths[key]) for key in ("stdlib", "purelib", "platlib"))
    return (*environment, root / "src", root / "tools")


def compile_bytecode(root: Path, python: Path, env: dict[str, str | None]) -> Path | None:
    """Compile every source once and return the prefix only when compilation completed."""
    prefix = root / CACHE
    stdlib = Path(sysconfig.get_paths()["stdlib"])
    completed = run_command(
        root,
        (
            str(python),
            "-X",
            f"pycache_prefix={prefix}",
            "-m",
            "compileall",
            "-q",
            "-j",
            "0",
            "--invalidation-mode",
            "checked-hash",
            "-x",
            rf"^{re.escape(str(stdlib / 'site-packages'))}|{_SKIP}",
            *map(str, sources(root)),
        ),
        env={key: value for key, value in env.items() if value is not None},
        remove_env=tuple(key for key, value in env.items() if value is None),
    )
    compiled = completed.returncode == 0
    output = (completed.stdout + completed.stderr).strip().splitlines()
    state = "compiled" if compiled else f"unavailable exit={completed.returncode}"
    with suppress(OSError, ValueError):
        print(f"ethos_test_bytecode state={state} prefix={prefix}", *output[-1:], file=sys.stderr)
    return prefix if compiled else None
