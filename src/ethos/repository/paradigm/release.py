"""Release binding conformance: the `[release]` table declares only what its readers consult.

The branch role reader consults `[release]` for its mirror, and the release owner for
`upgrade_from`, the releases that a release upgrades from. The version comes from `VERSION` and
the tag rule from `[protected_refs] tags`. Every other key of `[release]` is a declaration that no
reader consults, whether or not the binding protects release tags. A record of predecessors that
its reader refuses is reported under the same obligation, as the key was before it had a reader.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ethos.contracts.branch.roles import RELEASE_KEYS
from ethos.contracts.branch.roles import RELEASE_UPGRADE_FROM_KEY
from ethos.repository.paradigm.gap import ParadigmGap
from ethos.repository.release.predecessors import recorded

if TYPE_CHECKING:
    from collections.abc import Iterator
    from collections.abc import Mapping

    from ethos.contracts.paradigm.declaration import RepositoryParadigm


def release_binding_gaps(
    paradigm: RepositoryParadigm, declared: Mapping[str, object]
) -> Iterator[ParadigmGap]:
    """Report every `[release]` key that no reader consults, and a record its reader refuses."""
    release = declared.get("release")
    if not isinstance(release, dict):
        return  # The branch role reader refuses a `[release]` that is not a table.
    carrier = paradigm.binding.path("release")
    for key in release:
        if key not in RELEASE_KEYS:
            repair = f"remove {key}; no reader consults it"
            yield ParadigmGap("release-binding", f"{carrier}:release.{key}", repair)
    try:
        recorded(declared)
    except ValueError:
        repair = (
            f"record each release under [release.{RELEASE_UPGRADE_FROM_KEY}] as "
            '"<version>" = "<class>", with the class that ethos lane upgrade-from --json names'
        )
        key = f"{carrier}:release.{RELEASE_UPGRADE_FROM_KEY}"
        yield ParadigmGap("release-binding", key, repair)
