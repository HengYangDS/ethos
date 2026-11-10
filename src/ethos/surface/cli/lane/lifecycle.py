"""The hidden `lane` group's Cyclopts App and the options of its commands outside the catalog.

The catalog's `lane` commands join this App; `lane retire`, `lane lease` and `lane handoff` keep
their own Cyclopts commands until they are entries too.
"""

from __future__ import annotations

from typing import ClassVar

from cyclopts import App
from pydantic import BaseModel
from pydantic import ConfigDict

from ethos.contracts.operations.catalog import GROUPS
from ethos.surface.cli.application import app
from ethos.surface.cli.output import JsonFlag
from ethos.surface.cli.root_binding import RootOption

lane_app = App(name="lane", help=GROUPS["lane"].help, show=False)
app.command(lane_app)


class LaneCommandOptions(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    command: ClassVar[str]

    root: RootOption | None = None
    json_output: JsonFlag = False


class AppliedLaneCommandOptions(LaneCommandOptions):
    apply: bool = False
