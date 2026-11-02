"""Check and render the hosted provider projections from their native CUE owner."""

from __future__ import annotations

import json
import sys
from importlib import import_module
from pathlib import Path
from typing import Annotated

from cyclopts import App
from cyclopts import Parameter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
_projection = import_module("tools.ci.ci_projection")

cli_app = App(name="ethos-ci", help="ETHOS CI projection helpers.")


@cli_app.command(name="check-templates")
def check_templates_command(
    *, json_output: Annotated[bool, Parameter(name="--json")] = False, render: bool = False
) -> int:
    """Check native CUE compilation against the hosted provider surfaces."""
    if render:
        rendered = _projection.compile_providers(ROOT)
        outputs = {
            entry["projection"]: rendered[entry["provider"]]
            for entry in _projection.projection_entries()
        }
        sys.stdout.write(json.dumps(outputs, indent=2) + "\n")
        return 0
    return _projection.check_templates(json_output=json_output)


def main(argv: list[str] | None = None) -> int:
    """Run the Cyclopts-backed CI helper command surface."""
    try:
        cli_app(argv)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
