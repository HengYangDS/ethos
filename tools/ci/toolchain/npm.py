"""Run npm from the locked Node supply instead of an ambient installation.

`--seed` selects the npm bundled with the verified Node archive, which only performs
the first `npm ci`; every other invocation uses the npm that package-lock.json owns.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from ethos.adapters.repo.runtime.materialization.input_resolution import resolve_node_runtime
from ethos.adapters.repo.runtime.materialization.node.supply import NodeRuntime
from ethos.adapters.repo.runtime.materialization.node.supply import NodeSupply

# Ends a hung npm; the emulated windows-11-arm seed alone takes about two minutes.
TIMEOUT_SECONDS = 600


def main(argv: list[str] | None = None) -> int:
    """Run npm with the selected locked runtime and return its exit status."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    seed = arguments[:1] == ["--seed"]
    root = Path.cwd()
    runtime = (
        NodeRuntime.read(NodeSupply.read(root).installed_root(root), windows=os.name == "nt")
        if seed
        else resolve_node_runtime()
    )
    environment = {
        **os.environ,
        "PATH": os.pathsep.join((str(runtime.executable.parent), os.environ["PATH"])),
        "npm_config_engine_strict": "true",
        "npm_config_audit": "false",
        "npm_config_fund": "false",
        "npm_config_update_notifier": "false",
    }
    command = (str(runtime.executable), str(runtime.npm), *arguments[int(seed) :])
    completed = subprocess.run(
        command,
        cwd=root,
        env=environment,
        stdin=subprocess.DEVNULL,
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
