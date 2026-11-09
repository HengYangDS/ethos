"""Release binding conformance: the `[release]` table declares the release mirror alone.

The branch role reader consults `[release]` for its mirror and nothing else: the version comes from
`VERSION` and the tag rule from `[protected_refs] tags`. Every other key of `[release]` is a
declaration that no reader consults, whether or not the binding protects release tags.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.branch.roles import RELEASE_KEYS
from ethos.repository.paradigm.gap import ParadigmGap

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping

    from ethos.contracts.paradigm.declaration import RepositoryParadigm


def release_binding_gaps(
    paradigm: RepositoryParadigm, declared: Mapping[str, object]
) -> Iterator[ParadigmGap]:
    """Report every `[release]` key that the branch role reader does not consult."""
    release = declared.get("release")
    if not isinstance(release, dict):
        return  # The branch role reader refuses a `[release]` that is not a table.
    carrier = paradigm.binding.path("release")
    for key in release:
        if key not in RELEASE_KEYS:
            repair = f"remove {key}; no reader consults it"
            yield ParadigmGap("release-binding", f"{carrier}:release.{key}", repair)
