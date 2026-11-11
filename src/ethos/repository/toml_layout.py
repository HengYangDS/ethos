"""The layout of the TOML that ETHOS writes into a governed repository.

The shipped Taplo policy owns that layout. It keeps every array open, one element per line with a
trailing comma, as `tomli_w` writes it, so the policy's indent is the one setting read here.
"""

from __future__ import annotations

import tomllib
from typing import TYPE_CHECKING

import tomli_w

from ethos.repository.release.resources import canonical_resource

if TYPE_CHECKING:
    from collections.abc import Mapping

_SHIPPED_POLICY = ".config/checks/taplo/taplo.toml"


def render_toml(document: Mapping[str, object]) -> str:
    """Render a document with the `indent_string` that the shipped Taplo policy declares.

    `tomli_w` indents by a number of spaces, so an indent that is not spaces alone refuses.
    """
    policy = tomllib.loads(canonical_resource(_SHIPPED_POLICY).read_text(encoding="utf-8"))
    indent = policy.get("formatting", {}).get("indent_string")
    if not isinstance(indent, str) or not indent or indent.strip(" "):
        message = "taplo_indent_not_spaces"
        raise ValueError(message)
    return tomli_w.dumps(document, indent=len(indent))
