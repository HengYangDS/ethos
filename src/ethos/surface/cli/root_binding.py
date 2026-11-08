"""The repository-root option of CLI commands; the console resolves the root itself."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

RootOption = Annotated[Path, Parameter(name="--root")]
